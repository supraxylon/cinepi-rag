from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .db import Database
from .llm_gateway import LLMError, LLMGateway
from .utils import append_jsonl, read_jsonl, short, stable_id, write_text

EXTRACTION_PROMPT = """Extract one troubleshooting knowledge item from the source text.
Return only valid JSON with these keys:
- id
- type
- project
- topic
- symptoms
- environment
- likely_causes
- recommended_fix
- commands
- warnings
- confidence
- source_refs
- status

Use status "needs_review". Keep fields concise. Do not invent commands.
"""


def extract_knowledge(db: Database, llm: LLMGateway, query: str, output_path: str | Path, top_k: int = 6) -> list[dict]:
    chunks = db.search(query, top_k)
    items: list[dict] = []
    for chunk in chunks:
        source_ref = chunk.get("path_or_url") or chunk.get("source_title")
        fallback = {
            "id": stable_id(query, chunk["id"]),
            "type": "troubleshooting_case",
            "project": chunk.get("project") or "cinepi",
            "topic": chunk["title"],
            "symptoms": [query],
            "environment": {},
            "likely_causes": [],
            "recommended_fix": [short(chunk["content"], 500)],
            "commands": [],
            "warnings": ["Needs human review before publication."],
            "confidence": "low",
            "source_refs": [source_ref],
            "status": "needs_review",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            text = llm.chat([
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Query: {query}\nSource: {source_ref}\n\n{chunk['content']}"},
            ], task="extract", temperature=0.0, max_tokens=1200)
            item = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
            item.setdefault("id", fallback["id"])
            item.setdefault("status", "needs_review")
            item.setdefault("source_refs", [source_ref])
        except (LLMError, json.JSONDecodeError):
            item = fallback
        items.append(item)

    append_jsonl(Path(output_path), items)
    return items


def generate_docs(items_folder: str | Path, output_folder: str | Path) -> int:
    items: list[dict] = []
    for path in Path(items_folder).glob("*.jsonl"):
        items.extend(read_jsonl(path))

    count = 0
    for item in items:
        if item.get("status") not in {"approved", "published"}:
            continue
        slug = item.get("topic", "untitled").lower().replace("/", "-").replace(" ", "-")[:80]
        markdown = knowledge_item_to_markdown(item)
        write_text(Path(output_folder) / f"{slug}.md", markdown)
        count += 1
    return count


def knowledge_item_to_markdown(item: dict) -> str:
    def bullet(values: list | str | dict) -> str:
        if isinstance(values, dict):
            values = [f"{k}: {v}" for k, v in values.items()]
        if isinstance(values, str):
            values = [values]
        return "\n".join(f"- {value}" for value in values) if values else "- Not documented yet."

    title = item.get("topic", "Untitled troubleshooting note")
    return f"""# {title}

Status: `{item.get('status', 'unknown')}`  
Project: `{item.get('project', 'unknown')}`  
Confidence: `{item.get('confidence', 'unknown')}`

## Symptoms

{bullet(item.get('symptoms', []))}

## Environment

{bullet(item.get('environment', {}))}

## Likely causes

{bullet(item.get('likely_causes', []))}

## Recommended fix

{bullet(item.get('recommended_fix', []))}

## Commands

{bullet(item.get('commands', []))}

## Warnings

{bullet(item.get('warnings', []))}

## Sources

{bullet(item.get('source_refs', []))}
"""
