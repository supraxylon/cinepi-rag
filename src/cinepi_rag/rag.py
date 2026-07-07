from __future__ import annotations

from .db import Database
from .llm_gateway import LLMError, LLMGateway
from .utils import short

SYSTEM_PROMPT = """You are a CinePi/Cinemate troubleshooting assistant.
Use only the provided sources. If the sources are weak or conflicting, say what is uncertain.
Prefer practical steps, commands, and verification checks. Cite sources as [1], [2], etc.
"""


def format_sources(chunks: list[dict]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        source = chunk.get("path_or_url") or chunk.get("source_title")
        blocks.append(f"[{i}] {chunk['title']}\nSource: {source}\n{chunk['content']}")
    return "\n\n---\n\n".join(blocks)


def offline_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I could not find matching indexed documentation yet. Add sources with `ingest-docs` or approved Discord intake, then try again."
    lines = ["No LLM provider is configured, so here are the most relevant retrieved sources instead.\n"]
    for i, chunk in enumerate(chunks, start=1):
        lines.append(f"[{i}] **{chunk['title']}**")
        lines.append(f"Source: `{chunk.get('path_or_url') or chunk.get('source_title')}`")
        lines.append(short(chunk["content"], 700))
        lines.append("")
    return "\n".join(lines).strip()


def answer_question(db: Database, llm: LLMGateway, question: str, top_k: int = 6, retrieval_config: dict | None = None) -> str:
    chunks = db.search(question, top_k, retrieval_config)
    if not chunks:
        return "I could not find relevant indexed sources for that question."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question:\n{question}\n\nSources:\n{format_sources(chunks)}"},
    ]
    try:
        answer = llm.chat(messages, task="answer", temperature=0.0, max_tokens=1400)
    except LLMError:
        return offline_answer(question, chunks)

    citation_lines = ["", "Sources:"]
    for i, chunk in enumerate(chunks, start=1):
        citation_lines.append(f"[{i}] {chunk['title']} — {chunk.get('path_or_url') or chunk.get('source_title')}")
    return answer.strip() + "\n" + "\n".join(citation_lines)
