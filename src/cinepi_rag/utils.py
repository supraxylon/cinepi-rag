from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Any

SENSITIVE_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[redacted-email]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[redacted-ip]"),
    (re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"), r"\1=[redacted-secret]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"), r"\1[redacted-token]"),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in read_text(path).splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def redacted(text: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def clean_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.netloc.endswith("discordapp.com") or parsed.netloc.endswith("discordapp.net"):
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return redacted(url)


def stable_id(*parts: str) -> str:
    joined = "|".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def env_value(value: str | None, env_name: str | None) -> str | None:
    return value if value else os.getenv(env_name or "")


def short(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
