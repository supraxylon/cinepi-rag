from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .db import Database
from .extraction import extract_knowledge, generate_docs
from .ingestion import ingest_discord_jsonl, ingest_docs
from .llm_gateway import LLMGateway
from .rag import answer_question
from .utils import short


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CinePi/Cinemate local-first RAG starter")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    sub = parser.add_subparsers(dest="command", required=True)

    init_db = sub.add_parser("init-db", help="Initialize the SQLite database")
    init_db.add_argument("--reset", action="store_true", help="Drop and recreate tables")

    docs = sub.add_parser("ingest-docs", help="Ingest Markdown/TXT docs from a folder")
    docs.add_argument("folder")
    docs.add_argument("--project", default="cinepi")

    discord = sub.add_parser("ingest-discord", help="Ingest opt-in Discord JSONL threads")
    discord.add_argument("path")
    discord.add_argument("--project", default="cinemate")

    search = sub.add_parser("search", help="Search indexed chunks")
    search.add_argument("query")
    search.add_argument("--top-k", type=int, default=None)

    ask = sub.add_parser("ask", help="Ask a RAG question")
    ask.add_argument("question")
    ask.add_argument("--top-k", type=int, default=None)

    extract = sub.add_parser("extract", help="Extract draft knowledge items from retrieved chunks")
    extract.add_argument("query")
    extract.add_argument("--output", default="data/knowledge_items/extracted.jsonl")
    extract.add_argument("--top-k", type=int, default=None)

    gen = sub.add_parser("generate-docs", help="Generate Markdown docs from approved JSONL knowledge items")
    gen.add_argument("items_folder")
    gen.add_argument("output_folder")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    db = Database(config["database"]["path"])

    if args.command == "init-db":
        db.init(reset=args.reset)
        print(f"Initialized database at {db.path}")
        return

    db.init(reset=False)
    top_k = getattr(args, "top_k", None) or int(config.get("retrieval", {}).get("top_k", 6))

    if args.command == "ingest-docs":
        count = ingest_docs(db, args.folder, project=args.project)
        print(f"Ingested {count} chunks from {Path(args.folder)}")
    elif args.command == "ingest-discord":
        count = ingest_discord_jsonl(db, args.path, default_project=args.project)
        print(f"Ingested {count} approved Discord chunks from {Path(args.path)}")
    elif args.command == "search":
        for i, result in enumerate(db.search(args.query, top_k), start=1):
            print(f"\n[{i}] {result['title']}")
            print(f"Source: {result.get('path_or_url') or result.get('source_title')}")
            print(short(result["content"], 900))
    elif args.command == "ask":
        print(answer_question(db, LLMGateway(config), args.question, top_k=top_k))
    elif args.command == "extract":
        items = extract_knowledge(db, LLMGateway(config), args.query, args.output, top_k=top_k)
        print(f"Wrote {len(items)} draft knowledge items to {args.output}")
    elif args.command == "generate-docs":
        count = generate_docs(args.items_folder, args.output_folder)
        print(f"Generated {count} approved docs in {args.output_folder}")


if __name__ == "__main__":
    main()
