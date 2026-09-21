"""Single-file SQLite store: documents, chunks, FTS5 (BM25) index and embedding vectors.

Why one file instead of SQLite + a vector database: replacing a document (delete old chunks,
insert new chunks, vectors and text index) is ONE transaction, so a crash can never leave
the two stores out of sync, and a backup is one file copy. Dense search is an exact numpy
dot product over the collection's vectors, which is instant at study-material scale
(tens of thousands of chunks). Swap in an ANN index only if the corpus outgrows that.
"""
import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from app.ingest.types import Chunk, LoadedDocument

SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    warnings TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (collection_id, source)
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    header TEXT NOT NULL,
    text TEXT NOT NULL,
    meta TEXT NOT NULL,
    embedding BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(content, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
INSERT OR IGNORE INTO kv (key, value) VALUES ('version', 0);
"""

_STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from how i if in into is it its me my of on or "
    "our so than that the their them then there these they this to us was we what when where "
    "which who why will with you your about between explain describe difference".split()
)


@dataclass(frozen=True)
class ChunkRecord:
    id: int
    document_id: int
    doc_title: str
    source_type: str
    source: str
    ordinal: int
    header: str
    text: str
    meta: dict


@dataclass(frozen=True)
class DocumentRecord:
    id: int
    collection: str
    title: str
    source_type: str
    source: str
    sha256: str
    chunk_count: int
    warnings: list[str]


def fts_query(text: str) -> str | None:
    """Turn free text into a safe FTS5 OR-query of quoted content words (None if nothing left)."""
    words = [w for w in re.findall(r"[A-Za-z0-9]+", text.lower()) if w not in _STOPWORDS and len(w) > 1]
    return " OR ".join(f'"{w}"' for w in dict.fromkeys(words)) or None


class Store:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[tuple, tuple[int, np.ndarray, np.ndarray]] = {}
        with self._connect() as con:
            con.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def _transaction(self):
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
            except BaseException:
                con.execute("ROLLBACK")
                raise
            con.execute("UPDATE kv SET value = value + 1 WHERE key = 'version'")
            con.execute("COMMIT")

    # ---- collections -------------------------------------------------------------------

    def get_or_create_collection(self, name: str) -> int:
        with self._transaction() as con:
            con.execute("INSERT OR IGNORE INTO collections (name) VALUES (?)", (name,))
            return con.execute("SELECT id FROM collections WHERE name = ?", (name,)).fetchone()["id"]

    def collection_ids(self, names: Iterable[str] | None) -> list[int] | None:
        """Names -> ids. None means 'all collections'. Unknown names raise KeyError."""
        if names is None:
            return None
        with self._connect() as con:
            ids = []
            for name in names:
                row = con.execute("SELECT id FROM collections WHERE name = ?", (name,)).fetchone()
                if row is None:
                    raise KeyError(name)
                ids.append(row["id"])
            return ids

    def list_collections(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT c.id, c.name, COUNT(DISTINCT d.id) AS documents, COUNT(ch.id) AS chunks "
                "FROM collections c LEFT JOIN documents d ON d.collection_id = c.id "
                "LEFT JOIN chunks ch ON ch.document_id = d.id GROUP BY c.id ORDER BY c.name").fetchall()
            return [dict(r) for r in rows]

    # ---- documents ---------------------------------------------------------------------

    def find_document(self, collection_id: int, source: str) -> DocumentRecord | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT d.*, c.name AS collection FROM documents d JOIN collections c ON c.id = d.collection_id "
                "WHERE d.collection_id = ? AND d.source = ?", (collection_id, source)).fetchone()
            return self._document(row) if row else None

    def list_documents(self, collection_id: int | None = None) -> list[DocumentRecord]:
        with self._connect() as con:
            sql = ("SELECT d.*, c.name AS collection FROM documents d "
                   "JOIN collections c ON c.id = d.collection_id")
            params: tuple = ()
            if collection_id is not None:
                sql += " WHERE d.collection_id = ?"
                params = (collection_id,)
            return [self._document(r) for r in con.execute(sql + " ORDER BY c.name, d.title", params)]

    @staticmethod
    def _document(row) -> DocumentRecord:
        return DocumentRecord(row["id"], row["collection"], row["title"], row["source_type"], row["source"],
                              row["sha256"], row["chunk_count"], json.loads(row["warnings"]))

    @staticmethod
    def _delete_document(con, document_id: int) -> None:
        con.execute("DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE document_id = ?)",
                    (document_id,))
        con.execute("DELETE FROM documents WHERE id = ?", (document_id,))  # chunks cascade

    def delete_document(self, document_id: int) -> bool:
        with self._transaction() as con:
            exists = con.execute("SELECT 1 FROM documents WHERE id = ?", (document_id,)).fetchone()
            if exists:
                self._delete_document(con, document_id)
            return bool(exists)

    def add_document(self, collection_id: int, doc: LoadedDocument, chunks: Sequence[Chunk],
                     vectors: np.ndarray) -> int:
        """Insert a document, replacing any earlier copy from the same source, atomically."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        with self._transaction() as con:
            old = con.execute("SELECT id FROM documents WHERE collection_id = ? AND source = ?",
                              (collection_id, doc.source)).fetchone()
            if old:
                self._delete_document(con, old["id"])
            document_id = con.execute(
                "INSERT INTO documents (collection_id, title, source_type, source, sha256, chunk_count, warnings) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (collection_id, doc.title, doc.source_type, doc.source, doc.content_hash, len(chunks),
                 json.dumps(doc.warnings))).lastrowid
            for chunk, vector in zip(chunks, vectors):
                chunk_id = con.execute(
                    "INSERT INTO chunks (document_id, ordinal, header, text, meta, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                    (document_id, chunk.ordinal, chunk.header, chunk.text, json.dumps(chunk.meta),
                     vector.tobytes())).lastrowid
                con.execute("INSERT INTO chunks_fts (rowid, content) VALUES (?, ?)",
                            (chunk_id, chunk.header + "\n" + chunk.text))
            return document_id

    # ---- search ------------------------------------------------------------------------

    @staticmethod
    def _scope(collection_ids: Sequence[int] | None) -> tuple[str, list]:
        if collection_ids is None:
            return "", []
        marks = ",".join("?" for _ in collection_ids) or "NULL"
        return f" AND d.collection_id IN ({marks})", list(collection_ids)

    def _version(self, con) -> int:
        return con.execute("SELECT value FROM kv WHERE key = 'version'").fetchone()["value"]

    def _matrix(self, collection_ids: Sequence[int] | None) -> tuple[np.ndarray, np.ndarray]:
        key = None if collection_ids is None else tuple(sorted(collection_ids))
        with self._connect() as con:
            version = self._version(con)
            with self._lock:
                cached = self._cache.get(key)
            if cached and cached[0] == version:
                return cached[1], cached[2]
            scope_sql, params = self._scope(collection_ids)
            rows = con.execute(
                "SELECT c.id, c.embedding FROM chunks c JOIN documents d ON d.id = c.document_id "
                f"WHERE 1 = 1{scope_sql} ORDER BY c.id", params).fetchall()
        ids = np.array([r["id"] for r in rows], dtype=np.int64)
        matrix = (np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
                  if rows else np.zeros((0, 0), dtype=np.float32))
        with self._lock:
            self._cache[key] = (version, ids, matrix)
        return ids, matrix

    def dense_search(self, query_vector: np.ndarray, collection_ids: Sequence[int] | None,
                     k: int) -> list[tuple[int, float]]:
        """Exact cosine search (vectors are unit length). Returns [(chunk_id, similarity)], best first."""
        ids, matrix = self._matrix(collection_ids)
        if len(ids) == 0:
            return []
        scores = matrix @ np.asarray(query_vector, dtype=np.float32)
        k = min(k, len(ids))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]
        return [(int(ids[i]), float(scores[i])) for i in top]

    def bm25_search(self, query: str, collection_ids: Sequence[int] | None, k: int) -> list[tuple[int, float]]:
        match = fts_query(query)
        if match is None:
            return []
        scope_sql, params = self._scope(collection_ids)
        with self._connect() as con:
            rows = con.execute(
                "SELECT chunks_fts.rowid AS id, bm25(chunks_fts) AS score FROM chunks_fts "
                "JOIN chunks c ON c.id = chunks_fts.rowid JOIN documents d ON d.id = c.document_id "
                f"WHERE chunks_fts MATCH ?{scope_sql} ORDER BY score LIMIT ?", [match, *params, k]).fetchall()
        return [(r["id"], -r["score"]) for r in rows]  # FTS5 bm25 is lower-is-better

    def cosine(self, chunk_ids: Sequence[int], query_vector: np.ndarray) -> dict[int, float]:
        if not chunk_ids:
            return {}
        marks = ",".join("?" for _ in chunk_ids)
        with self._connect() as con:
            rows = con.execute(f"SELECT id, embedding FROM chunks WHERE id IN ({marks})", list(chunk_ids)).fetchall()
        q = np.asarray(query_vector, dtype=np.float32)
        return {r["id"]: float(np.frombuffer(r["embedding"], dtype=np.float32) @ q) for r in rows}

    def get_chunks(self, chunk_ids: Sequence[int]) -> dict[int, ChunkRecord]:
        if not chunk_ids:
            return {}
        marks = ",".join("?" for _ in chunk_ids)
        with self._connect() as con:
            rows = con.execute(
                "SELECT c.id, c.document_id, c.ordinal, c.header, c.text, c.meta, d.title, d.source_type, d.source "
                f"FROM chunks c JOIN documents d ON d.id = c.document_id WHERE c.id IN ({marks})",
                list(chunk_ids)).fetchall()
        return {r["id"]: ChunkRecord(r["id"], r["document_id"], r["title"], r["source_type"], r["source"],
                                     r["ordinal"], r["header"], r["text"], json.loads(r["meta"])) for r in rows}
