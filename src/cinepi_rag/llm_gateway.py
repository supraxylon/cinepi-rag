from __future__ import annotations

import json
from typing import Any

import requests

from .utils import env_value


class LLMError(RuntimeError):
    pass


class BaseProvider:
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config

    def is_available(self) -> bool:
        return self.config.get("type") == "offline"

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0, max_tokens: int = 1200) -> str:
        raise LLMError(f"Provider '{self.name}' does not implement chat().")


class OfflineProvider(BaseProvider):
    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0, max_tokens: int = 1200) -> str:
        raise LLMError("No LLM provider is configured. Using offline fallback instead.")


class OpenAICompatibleProvider(BaseProvider):
    def is_available(self) -> bool:
        base_url = self.config.get("base_url", "").rstrip("/")
        return bool(base_url and self.config.get("model"))

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0, max_tokens: int = 1200) -> str:
        base_url = self.config["base_url"].rstrip("/")
        api_key = env_value(self.config.get("api_key"), self.config.get("api_key_env")) or "local-dev-key"
        payload = {"model": self.config["model"], "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=int(self.config.get("timeout_seconds", 120)),
        )
        if response.status_code >= 400:
            raise LLMError(f"{self.name} returned HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        return data["choices"][0]["message"]["content"]


class LLMGateway:
    def __init__(self, config: dict[str, Any]):
        llm_config = config.get("llm", {})
        self.default_provider = llm_config.get("default_provider", "offline")
        self.providers = {name: self._make_provider(name, cfg) for name, cfg in llm_config.get("providers", {}).items()}
        self.providers.setdefault("offline", OfflineProvider("offline", {"type": "offline"}))

    def _make_provider(self, name: str, config: dict[str, Any]) -> BaseProvider:
        if config.get("type") == "openai_compatible":
            return OpenAICompatibleProvider(name, config)
        return OfflineProvider(name, config)

    def chat(self, messages: list[dict[str, str]], task: str = "answer", temperature: float = 0.0, max_tokens: int = 1200) -> str:
        provider = self.providers.get(self.default_provider, self.providers["offline"])
        if not provider.is_available() or isinstance(provider, OfflineProvider):
            raise LLMError("No available online/local provider configured.")
        return provider.chat(messages, temperature=temperature, max_tokens=max_tokens)
