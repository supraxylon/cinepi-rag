from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .utils import stable_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    project TEXT,
    title TEXT NOT NULL,
    path_or_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    heading_path TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES sources(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    title,
    content,
    source_id UNINDEXED,
    chunk_id UNINDEXED
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self, reset: bool = False) -> None:
        with self.connect() as conn:
            if reset:
                conn.executescript("DROP TABLE IF EXISTS sources; DROP TABLE IF EXISTS chunks; DROP TABLE IF EXISTS chunks_fts;")
            conn.executescript(SCHEMA)

    def add_source(self, source_type: str, project: str, title: str, path_or_url: str, metadata: dict[str, Any] | None = None) -> str:
        source_id = stable_id(source_type, project, title, path_or_url)
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (source_id, source_type, project, title, path_or_url, json.dumps(metadata or {})),
            )
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            conn.execute("DELETE FROM chunks_fts WHERE source_id = ?", (source_id,))
        return source_id

    def add_chunk(self, source_id: str, title: str, content: str, heading_path: str, metadata: dict[str, Any] | None = None) -> str:
        chunk_id = stable_id(source_id, title, content[:200])
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (chunk_id, source_id, title, content, heading_path, json.dumps(metadata or {})),
            )
            conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))
            conn.execute(
                "INSERT INTO chunks_fts(title, content, source_id, chunk_id) VALUES (?, ?, ?, ?)",
                (title, content, source_id, chunk_id),
            )
        return chunk_id

    def search(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = [t for t in re.findall(r"[A-Za-z0-9_]+", query) if len(t) > 1]
        match_query = " OR ".join(terms[:12]) or query
        sql = """
            SELECT c.id, c.title, c.content, c.heading_path, c.metadata_json,
                   s.source_type, s.project, s.path_or_url, s.title AS source_title,
                   bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.chunk_id
            JOIN sources s ON s.id = c.source_id
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """
        try:
            with self.connect() as conn:
                rows = conn.execute(sql, (match_query, limit)).fetchall()
        except sqlite3.OperationalError:
            like_query = f"%{query}%"
            with self.connect() as conn:
                rows = conn.execute(
                    """
                    SELECT c.id, c.title, c.content, c.heading_path, c.metadata_json,
                           s.source_type, s.project, s.path_or_url, s.title AS source_title,
                           0 AS score
                    FROM chunks c JOIN sources s ON s.id = c.source_id
                    WHERE c.content LIKE ? OR c.title LIKE ?
                    LIMIT ?
                    """,
                    (like_query, like_query, limit),
                ).fetchall()
        return [dict(row) | {"metadata": json.loads(row["metadata_json"] or "{}")} for row in rows]

    def count_chunks(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
