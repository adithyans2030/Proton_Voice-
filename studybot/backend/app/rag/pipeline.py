"""Glue: ingest a source, and answer a question from the indexed materials."""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from app.config import Settings
from app.core.ollama import chat_stream
from app.ingest.chunker import ChunkingConfig, chunk_document
from app.ingest.loader import load_source
from app.ingest.types import IngestError
from app.rag import prompt
from app.rag.embed import Embedder, EmbedderLike
from app.rag.rerank import Reranker, RerankerLike
from app.rag.retrieve import Hit, Mode, Retrieval, Retriever
from app.rag.store import Store


@dataclass
class IngestResult:
    document_id: int | None
    title: str
    source_type: str
    chunks: int
    skipped: bool
    warnings: list[str]
    seconds: float


@dataclass
class Answer:
    text: str
    refused: bool  # the answer is "not in your materials"
    gated: bool  # refused by the retrieval-score gate, without calling the LLM
    hits: list[Hit]
    cited: list[int] = field(default_factory=list)  # 1-based source numbers the answer cites
    invalid_citations: int = 0
    first_token_seconds: float = 0.0
    total_seconds: float = 0.0
    tokens: int = 0
    tokens_per_second: float = 0.0
    prompt_tokens: int = 0
    prompt_seconds: float = 0.0
    best_dense: float = 0.0
    empty: bool = False  # the model produced no real content (e.g. only citation markers)


class StudyBot:
    def __init__(self, settings: Settings, *, embedder: EmbedderLike | None = None,
                 reranker: RerankerLike | None = None, store: Store | None = None):
        self.settings = settings
        settings.ensure_dirs()
        self.store = store or Store(settings.db_path)
        self.embedder = embedder or Embedder(settings.embed_model, settings.models_dir)
        if reranker is None and settings.use_reranker:
            reranker = Reranker(settings.rerank_model, settings.models_dir)
        self.retriever = Retriever(self.store, self.embedder, reranker, settings.candidates)
        self.chunking = ChunkingConfig(settings.chunk_target_tokens, settings.chunk_max_tokens,
                                       settings.chunk_min_tokens, settings.chunk_overlap_tokens)

    def ingest(self, source: str, collection: str = "default", force: bool = False) -> IngestResult:
        started = time.perf_counter()
        doc = load_source(source, cache_dir=self.settings.cache_dir)
        collection_id = self.store.get_or_create_collection(collection)

        existing = self.store.find_document(collection_id, doc.source)
        if existing and existing.sha256 == doc.content_hash and not force:
            return IngestResult(existing.id, doc.title, doc.source_type, existing.chunk_count, True,
                                doc.warnings, time.perf_counter() - started)

        chunks = chunk_document(doc, self.chunking)
        if not chunks:
            raise IngestError(f"No usable text found in '{doc.title}'.")
        vectors = self.embedder.embed_passages([c.header + "\n" + c.text for c in chunks])
        document_id = self.store.add_document(collection_id, doc, chunks, vectors)
        return IngestResult(document_id, doc.title, doc.source_type, len(chunks), False, doc.warnings,
                            time.perf_counter() - started)

    def search(self, question: str, collections: Sequence[str] | None = None, k: int | None = None,
               mode: Mode = "hybrid", rerank: bool | None = None) -> Retrieval:
        ids = self.store.collection_ids(collections)
        return self.retriever.search(question, ids, k or self.settings.retrieve_k, mode, rerank)

    async def ask(self, question: str, collections: Sequence[str] | None = None, *, model: str | None = None,
                  use_gate: bool = True, on_token: Callable[[str], None] | None = None) -> Answer:
        started = time.perf_counter()
        retrieval = self.search(question, collections)
        hits = retrieval.hits

        if not hits or (use_gate and retrieval.best_dense < self.settings.min_dense_score):
            return Answer(prompt.REFUSAL, True, True, hits, best_dense=retrieval.best_dense,
                          total_seconds=time.perf_counter() - started)

        pieces: list[str] = []
        first_token = 0.0
        tokens, gen_seconds, prompt_tokens, prompt_seconds = 0, 0.0, 0, 0.0
        async for chunk in chat_stream(self.settings.ollama_url, model or self.settings.llm_model,
                                       prompt.build_messages(question, hits), num_ctx=self.settings.num_ctx):
            if chunk.text:
                if not pieces:
                    first_token = time.perf_counter() - started
                pieces.append(chunk.text)
                if on_token:
                    on_token(chunk.text)
            if chunk.done:
                tokens, gen_seconds = chunk.eval_count, chunk.eval_seconds
                prompt_tokens, prompt_seconds = chunk.prompt_tokens, chunk.prompt_seconds

        raw = "".join(pieces).strip()
        text, cited, invalid = prompt.extract_citations(raw, len(hits))
        return Answer(text, prompt.is_refusal(raw), False, hits, cited, invalid, first_token,
                      time.perf_counter() - started, tokens, tokens / gen_seconds if gen_seconds else 0.0,
                      prompt_tokens, prompt_seconds, retrieval.best_dense, prompt.is_empty_answer(text))
