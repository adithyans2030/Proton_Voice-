"""Command line for ingesting materials and asking questions.

    python -m app.cli ingest <file-or-youtube-url> [-c COLLECTION] [--force]
    python -m app.cli search "question" [-c COLLECTION ...] [--mode hybrid|dense|bm25] [--rerank]
    python -m app.cli ask "question" [-c COLLECTION ...] [--model NAME] [--no-gate]
    python -m app.cli list
    python -m app.cli delete <document-id>
"""
import argparse
import asyncio
import sys

from app.config import Settings
from app.core.ollama import OllamaError
from app.ingest.types import IngestError
from app.rag import prompt
from app.rag.pipeline import StudyBot


def _print_hits(hits) -> None:
    for number, hit in enumerate(hits, start=1):
        preview = hit.chunk.text.replace("\n", " ")
        print(f"[{number}] {prompt.label(hit)} | score={hit.score:.4f} cosine={hit.dense:.3f}")
        print(f"    {hit.chunk.header}")
        print(f"    {preview[:160]}{'…' if len(preview) > 160 else ''}")


def _cmd_ingest(bot: StudyBot, args) -> int:
    result = bot.ingest(args.source, args.collection, force=args.force)
    status = "already up to date (skipped)" if result.skipped else "indexed"
    print(f"{status}: {result.title} [{result.source_type}] -> {result.chunks} chunks in {result.seconds:.1f}s")
    for warning in result.warnings:
        print(f"  warning: {warning}")
    return 0


def _cmd_search(bot: StudyBot, args) -> int:
    retrieval = bot.search(args.question, args.collection, args.k, args.mode, args.rerank or None)
    print(f"best cosine: {retrieval.best_dense:.3f}")
    _print_hits(retrieval.hits)
    return 0


def _cmd_ask(bot: StudyBot, args) -> int:
    answer = asyncio.run(bot.ask(args.question, args.collection, model=args.model, use_gate=not args.no_gate,
                                 on_token=lambda t: print(t, end="", flush=True)))
    if answer.gated:
        print(answer.text + f"  (best cosine {answer.best_dense:.3f} is below the gate {bot.settings.min_dense_score})")
    print()
    if answer.invalid_citations:  # the text above was streamed raw, so it may show markers that do not exist
        print(f"\n(note: the model cited {answer.invalid_citations} source number(s) that do not exist; "
              "ignore any [n] not listed under Sources)")
    if answer.empty and not answer.gated:
        print("\n(note: the model returned no answer text. Try rephrasing the question.)")
    if answer.cited:
        print("\nSources:")
        for number in answer.cited:
            hit = answer.hits[number - 1]
            url = prompt.source_url(hit)
            print(f"  [{number}] {prompt.label(hit)}" + (f"  {url}" if url else ""))
    print(f"\n(first token {answer.first_token_seconds:.1f}s, total {answer.total_seconds:.1f}s, "
          f"{answer.tokens_per_second:.0f} tok/s, best cosine {answer.best_dense:.3f})")
    return 0


def _cmd_list(bot: StudyBot, args) -> int:
    collections = bot.store.list_collections()
    if not collections:
        print("Nothing indexed yet. Try: python -m app.cli ingest <file-or-youtube-url> -c my-subject")
    for collection in collections:
        print(f"{collection['name']}: {collection['documents']} document(s), {collection['chunks']} chunks")
        for doc in bot.store.list_documents(collection["id"]):
            print(f"  #{doc.id} [{doc.source_type}] {doc.title} ({doc.chunk_count} chunks)")
    return 0


def _cmd_delete(bot: StudyBot, args) -> int:
    deleted = bot.store.delete_document(args.document_id)
    print("deleted" if deleted else f"no document with id {args.document_id}")
    return 0 if deleted else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="studybot", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="index a PDF/PPTX/DOCX file or YouTube link")
    p.add_argument("source")
    p.add_argument("-c", "--collection", default="default")
    p.add_argument("--force", action="store_true", help="re-index even if unchanged")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("search", help="show retrieved passages without calling the LLM")
    p.add_argument("question")
    p.add_argument("-c", "--collection", action="append")
    p.add_argument("-k", type=int, default=None)
    p.add_argument("--mode", choices=["hybrid", "dense", "bm25"], default="hybrid")
    p.add_argument("--rerank", action="store_true")
    p.set_defaults(func=_cmd_search)

    p = sub.add_parser("ask", help="answer a question from the indexed materials")
    p.add_argument("question")
    p.add_argument("-c", "--collection", action="append")
    p.add_argument("--model", default=None)
    p.add_argument("--no-gate", action="store_true", help="always call the LLM, skipping the score gate")
    p.set_defaults(func=_cmd_ask)

    p = sub.add_parser("list", help="list collections and documents")
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("delete", help="remove a document")
    p.add_argument("document_id", type=int)
    p.set_defaults(func=_cmd_delete)

    args = parser.parse_args(argv)
    bot = StudyBot(Settings())
    try:
        return args.func(bot, args)
    except (IngestError, OllamaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyError as exc:
        print(f"error: no collection named {exc}. Run 'list' to see collections.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
