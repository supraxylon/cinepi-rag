from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG = {
    "database": {"path": "data/cinepi_rag.sqlite"},
    "retrieval": {
        "top_k": 6,
        "candidate_multiplier": 4,
        "enable_authority_rerank": True,
        "authority_boost_weight": 0.15,
        "pinned_boost_weight": 0.05,
        "reaction_boost_weight": 0.02,
    },
    "discord": {
        "preserve_author_names": False,
        "trusted_authors": [],
        "trusted_roles": {"Admin": 1.5, "Moderator": 1.3},
    },
    "discord_exports": {
        "default_project": "cinepi",
        "preserve_author_names": False,
        "include_bots": False,
        "max_chars": 5000,
        "max_messages": 40,
    },
    "llm": {"default_provider": "offline", "providers": {"offline": {"type": "offline"}}},
}


def load_config(path: str = "config.yaml") -> dict[str, Any]:
    load_dotenv()
    config_path = Path(path)
    if not config_path.exists():
        return DEFAULT_CONFIG
    loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config = DEFAULT_CONFIG | loaded
    config["database"] = DEFAULT_CONFIG["database"] | config.get("database", {})
    config["retrieval"] = DEFAULT_CONFIG["retrieval"] | config.get("retrieval", {})
    config["discord"] = DEFAULT_CONFIG["discord"] | config.get("discord", {})
    config["discord_exports"] = DEFAULT_CONFIG["discord_exports"] | config.get("discord_exports", {})
    config["llm"] = DEFAULT_CONFIG["llm"] | config.get("llm", {})
    return config
