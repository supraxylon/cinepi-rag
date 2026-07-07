from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG = {
    "database": {"path": "data/cinepi_rag.sqlite"},
    "retrieval": {"top_k": 6},
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
    config["llm"] = DEFAULT_CONFIG["llm"] | config.get("llm", {})
    return config
