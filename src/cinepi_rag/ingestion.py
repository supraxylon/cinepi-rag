from __future__ import annotations

from pathlib import Path
from typing import Any

from .chunking import chunk_markdown, chunk_plain_text
from .db import Database
from .discord_export import chunk_discord_export, discord_export_files, export_metadata, export_title, load_discord_export
from .utils import read_jsonl, read_text, redacted

TEXT_EXTENSIONS = {".md", ".markdown", ".txt", ".rst"}


def ingest_docs(db: Database, folder: str | Path, project: str = "cinepi") -> int:
    root = Path(folder)
    added = 0
    for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in TEXT_EXTENSIONS):
        title = path.stem.replace("-", " ").replace("_", " ").strip().title()
        text = redacted(read_text(path))
        source_id = db.add_source("file", project, title, str(path), {"extension": path.suffix})
        chunks = chunk_markdown(title, text) if path.suffix.lower() in {".md", ".markdown"} else chunk_plain_text(title, text)
        for chunk in chunks:
            db.add_chunk(source_id, chunk.title, chunk.text, chunk.heading_path, {"relative_path": str(path)})
            added += 1
    return added


def discord_thread_to_text(thread: dict[str, Any]) -> str:
    if "content" in thread:
        return redacted(str(thread["content"]))
    messages = thread.get("messages", [])
    lines = []
    for msg in messages:
        author = msg.get("author", "unknown")
        content = redacted(str(msg.get("content", ""))).strip()
        if content:
            lines.append(f"{author}: {content}")
    return "\n".join(lines)


def ingest_discord_jsonl(db: Database, path: str | Path, default_project: str = "cinemate") -> int:
    added = 0
    for index, thread in enumerate(read_jsonl(Path(path)), start=1):
        if thread.get("approved_for_kb") is not True:
            continue
        title = thread.get("title") or thread.get("thread_title") or f"Discord thread {index}"
        project = thread.get("project", default_project)
        text = discord_thread_to_text(thread)
        source_id = db.add_source("discord_intake", project, title, str(path), {"row": index, "thread_id": thread.get("thread_id")})
        for chunk in chunk_plain_text(title, text, max_chars=3200):
            db.add_chunk(source_id, chunk.title, chunk.text, chunk.heading_path, {"thread_title": title})
            added += 1
    return added


def ingest_discord_export(
    db: Database,
    path: str | Path,
    default_project: str = "cinepi",
    preserve_author_names: bool = False,
    include_bots: bool = False,
    max_chars: int = 5000,
    max_messages: int = 40,
) -> int:
    added = 0
    for export_path in discord_export_files(path):
        data = load_discord_export(export_path)
        title = export_title(data)
        metadata = export_metadata(data, export_path)
        source_id = db.add_source("discord_export_raw", default_project, title, str(export_path), metadata)
        for chunk in chunk_discord_export(data, preserve_author_names, include_bots, max_chars, max_messages):
            chunk_metadata = metadata | (chunk.metadata or {})
            db.add_chunk(source_id, chunk.title, chunk.text, chunk.heading_path, chunk_metadata)
            added += 1
    return added
