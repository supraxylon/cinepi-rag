from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    title: str
    text: str
    heading_path: str


def chunk_markdown(title: str, text: str, max_chars: int = 2800) -> list[Chunk]:
    sections: list[tuple[str, str]] = []
    current_heading = title
    current_lines: list[str] = []

    for line in text.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line.lstrip("#").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    chunks: list[Chunk] = []
    for heading, body in sections:
        if len(body) <= max_chars:
            chunks.append(Chunk(title=heading, text=body, heading_path=heading))
            continue
        paragraphs = re.split(r"\n\s*\n", body)
        buffer = ""
        part = 1
        for paragraph in paragraphs:
            if len(buffer) + len(paragraph) + 2 > max_chars and buffer:
                chunks.append(Chunk(title=f"{heading} — part {part}", text=buffer.strip(), heading_path=heading))
                buffer, part = paragraph, part + 1
            else:
                buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if buffer.strip():
            chunks.append(Chunk(title=f"{heading} — part {part}" if part > 1 else heading, text=buffer.strip(), heading_path=heading))

    return [c for c in chunks if c.text]


def chunk_plain_text(title: str, text: str, max_chars: int = 2800) -> list[Chunk]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    buffer = ""
    part = 1
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 2 > max_chars and buffer:
            chunks.append(Chunk(title=f"{title} — part {part}", text=buffer.strip(), heading_path=title))
            buffer, part = paragraph, part + 1
        else:
            buffer = f"{buffer}\n\n{paragraph}" if buffer else paragraph
    if buffer.strip():
        chunks.append(Chunk(title=f"{title} — part {part}" if part > 1 else title, text=buffer.strip(), heading_path=title))
    return chunks
