from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .chunking import Chunk
from .utils import clean_url, redacted, stable_id

RELEVANT_AUTHOR_ROLES = {"Admin", "Moderator"}


def discord_export_files(path: str | Path) -> list[Path]:
    root = Path(path)
    if root.is_file() and root.suffix.lower() == ".json":
        return [root]
    return sorted(p for p in root.rglob("*.json") if p.is_file())


def load_discord_export(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise ValueError(f"Not a Discord channel export with a messages array: {path}")
    return data


def author_names(author: dict[str, Any]) -> tuple[str, str]:
    return str(author.get("name") or ""), str(author.get("nickname") or "")


def author_roles(author: dict[str, Any]) -> list[str]:
    return [str(role.get("name")) for role in author.get("roles", []) if isinstance(role, dict) and role.get("name")]


def authority_for_author(author: dict[str, Any], discord_config: dict[str, Any] | None = None) -> tuple[float, str]:
    discord_config = discord_config or {}
    name, nickname = author_names(author)
    names = {name.lower(), nickname.lower()} - {""}

    for trusted in discord_config.get("trusted_authors", []) or []:
        aliases = {str(alias).lower() for alias in trusted.get("aliases", [])}
        if names.intersection(aliases):
            return float(trusted.get("score", 1.0)), str(trusted.get("reason") or f"trusted author: {name or nickname}")

    role_scores = discord_config.get("trusted_roles", {}) or {}
    matched_roles = [role for role in author_roles(author) if role in role_scores]
    if matched_roles:
        best_role = max(matched_roles, key=lambda role: float(role_scores[role]))
        return float(role_scores[best_role]), f"trusted role: {best_role}"

    return 1.0, "normal author"


def author_label(author: dict[str, Any], preserve_names: bool = False, discord_config: dict[str, Any] | None = None) -> str:
    name, nickname = author_names(author)
    display = nickname or name or "unknown"
    score, _reason = authority_for_author(author, discord_config)
    if preserve_names or score > 1.0 or set(author_roles(author)).intersection(RELEVANT_AUTHOR_ROLES):
        return redacted(display)
    return f"user_{stable_id(str(author.get('id') or display))[:8]}"


def export_title(data: dict[str, Any]) -> str:
    guild = data.get("guild", {}).get("name") or "Discord"
    channel = data.get("channel", {}).get("name") or "unknown-channel"
    return f"{guild} #{channel}"


def export_metadata(data: dict[str, Any], path: str | Path) -> dict[str, Any]:
    channel = data.get("channel", {})
    guild = data.get("guild", {})
    return {
        "review_status": "raw",
        "source_format": "discord-channel-export",
        "source_file": str(path),
        "guild_id": guild.get("id"),
        "guild_name": guild.get("name"),
        "channel_id": channel.get("id"),
        "channel_name": channel.get("name"),
        "channel_category": channel.get("category"),
        "channel_topic": channel.get("topic"),
        "exported_at": data.get("exportedAt"),
        "message_count": data.get("messageCount"),
    }


def attachment_lines(attachments: list[dict[str, Any]]) -> list[str]:
    lines = []
    for item in attachments:
        name = redacted(str(item.get("fileName") or "attachment"))
        url = clean_url(str(item.get("url") or "")).strip()
        size = item.get("fileSizeBytes")
        lines.append(f"  attachment: {name}" + (f" ({size} bytes)" if size else "") + (f" {url}" if url else ""))
    return lines


def embed_lines(embeds: list[dict[str, Any]]) -> list[str]:
    lines = []
    for embed in embeds:
        title = redacted(str(embed.get("title") or "")).strip()
        description = redacted(str(embed.get("description") or "")).strip()
        url = clean_url(str(embed.get("url") or "")).strip()
        if title or url:
            lines.append(f"  embed: {title}" + (f" {url}" if url else ""))
        if description:
            lines.append(f"  embed description: {description[:800]}")
        for field in embed.get("fields", []) or []:
            if isinstance(field, dict):
                lines.append(f"  embed field: {field.get('name', '')}: {field.get('value', '')}")
    return lines


def forwarded_lines(message: dict[str, Any]) -> list[str]:
    forwarded = message.get("forwardedMessage")
    if not isinstance(forwarded, dict):
        return []
    content = redacted(str(forwarded.get("content") or "")).strip()
    lines = ["  forwarded message:" + (f" {content}" if content else "")]
    lines.extend(attachment_lines(forwarded.get("attachments", []) or []))
    lines.extend(embed_lines(forwarded.get("embeds", []) or []))
    return lines


def message_text(
    message: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    preserve_names: bool = False,
    discord_config: dict[str, Any] | None = None,
) -> str:
    author = author_label(message.get("author", {}) or {}, preserve_names, discord_config)
    timestamp = message.get("timestamp") or "unknown-time"
    tags = []
    if message.get("type") not in {None, "Default", "Reply"}:
        tags.append(str(message.get("type")))
    if message.get("isPinned"):
        tags.append("PINNED")

    content = redacted(str(message.get("content") or "")).strip()
    lines = [f"[{timestamp}] {author}" + (f" ({', '.join(tags)})" if tags else "") + f": {content}"]

    ref = message.get("reference") or {}
    parent = by_id.get(str(ref.get("messageId"))) if isinstance(ref, dict) else None
    if parent and parent.get("content"):
        parent_author = author_label(parent.get("author", {}) or {}, preserve_names, discord_config)
        parent_text = redacted(str(parent.get("content", ""))).strip().replace("\n", " ")[:500]
        lines.append(f"  replies to {parent_author}: {parent_text}")

    lines.extend(attachment_lines(message.get("attachments", []) or []))
    lines.extend(embed_lines(message.get("embeds", []) or []))
    lines.extend(forwarded_lines(message))
    return "\n".join(line for line in lines if line.strip())


def reaction_count(message: dict[str, Any]) -> int:
    return sum(int(item.get("count") or 0) for item in message.get("reactions", []) or [] if isinstance(item, dict))


def message_authority_metadata(message: dict[str, Any], discord_config: dict[str, Any] | None = None) -> dict[str, Any]:
    author = message.get("author", {}) or {}
    name, nickname = author_names(author)
    score, reason = authority_for_author(author, discord_config)
    return {
        "authority_score": score,
        "authority_reason": reason,
        "author_name": name,
        "author_nickname": nickname,
        "author_roles": author_roles(author),
        "is_pinned": bool(message.get("isPinned")),
        "reaction_count": reaction_count(message),
    }


def chunk_discord_export(
    data: dict[str, Any],
    preserve_author_names: bool = False,
    include_bots: bool = False,
    max_chars: int = 5000,
    max_messages: int = 40,
    discord_config: dict[str, Any] | None = None,
) -> list[Chunk]:
    messages = [msg for msg in data.get("messages", []) if isinstance(msg, dict)]
    by_id = {str(msg.get("id")): msg for msg in messages if msg.get("id")}
    title = export_title(data)
    chunks: list[Chunk] = []
    buffer: list[str] = []
    stats: list[dict[str, Any]] = []
    start_ts = end_ts = ""
    start_id = end_id = ""
    part = 1

    def flush() -> None:
        nonlocal buffer, stats, start_ts, end_ts, start_id, end_id, part
        if not buffer:
            return
        best = max(stats, key=lambda item: float(item["authority_score"]), default={"authority_score": 1.0, "authority_reason": "normal author"})
        trusted = [s for s in stats if float(s["authority_score"]) > 1.0]
        trusted_names = sorted({s.get("author_nickname") or s.get("author_name") for s in trusted if s.get("author_nickname") or s.get("author_name")})
        chunk_title = f"{title} — messages {part}"
        chunk_text = "\n\n".join(buffer).strip()
        chunks.append(Chunk(title=chunk_title, text=chunk_text, heading_path=f"{title} / {start_ts} to {end_ts}"))
        chunks[-1].metadata = {
            "message_id_start": start_id,
            "message_id_end": end_id,
            "timestamp_start": start_ts,
            "timestamp_end": end_ts,
            "chunk_message_count": len(stats),
            "authority_score": float(best["authority_score"]),
            "authority_reason": best["authority_reason"],
            "trusted_author_count": len(trusted),
            "trusted_authors": trusted_names,
            "is_pinned": any(bool(s.get("is_pinned")) for s in stats),
            "pinned_count": sum(1 for s in stats if s.get("is_pinned")),
            "reaction_count": sum(int(s.get("reaction_count") or 0) for s in stats),
        }
        buffer, stats, start_ts, end_ts, start_id, end_id, part = [], [], "", "", "", "", part + 1

    for message in messages:
        if message.get("author", {}).get("isBot") and not include_bots:
            continue
        text = message_text(message, by_id, preserve_author_names, discord_config)
        if not text.strip() or text.strip().endswith(":"):
            continue
        if buffer and (sum(len(item) for item in buffer) + len(text) > max_chars or len(buffer) >= max_messages):
            flush()
        buffer.append(text)
        stats.append(message_authority_metadata(message, discord_config))
        start_ts = start_ts or str(message.get("timestamp") or "")
        start_id = start_id or str(message.get("id") or "")
        end_ts = str(message.get("timestamp") or "")
        end_id = str(message.get("id") or "")
    flush()
    return chunks
