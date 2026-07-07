from __future__ import annotations

import asyncio
import os
from typing import Any

from .config import load_config
from .db import Database
from .llm_gateway import LLMGateway
from .rag import answer_question
from .utils import short

DISCORD_LIMIT = 2000
SAFE_LIMIT = 1900


def split_discord_message(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    """Split text into Discord-sized messages without breaking lines when possible."""
    text = text.strip() or "No response generated."
    parts: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    parts.append(text)
    return parts


def allowed_channel(channel_id: int | None, allowed_ids: list[int]) -> bool:
    return not allowed_ids or channel_id in allowed_ids


def run_bot(config_path: str = "config.yaml") -> None:
    """Run the Discord slash-command bot.

    The discord.py import lives here so the rest of the package works even when
    the optional Discord dependency is not installed.
    """
    try:
        import discord
        from discord import app_commands
    except ImportError as exc:  # pragma: no cover - exercised manually
        raise SystemExit("discord.py is not installed. Run: pip install -r requirements.txt") from exc

    config = load_config(config_path)
    bot_cfg: dict[str, Any] = config.get("discord_bot", {})
    token_env = bot_cfg.get("token_env", "DISCORD_BOT_TOKEN")
    token = os.getenv(token_env)
    if not token:
        raise SystemExit(f"Missing Discord bot token. Set {token_env} in your environment or .env file.")

    db = Database(config["database"]["path"])
    llm = LLMGateway(config)
    retrieval_config = config.get("retrieval", {})
    top_k = int(bot_cfg.get("top_k", retrieval_config.get("top_k", 6)))
    allowed_ids = [int(x) for x in bot_cfg.get("allowed_channel_ids", []) if str(x).strip()]
    guild_id = bot_cfg.get("guild_id") or os.getenv(bot_cfg.get("guild_id_env", "DISCORD_GUILD_ID"), "")
    public_by_default = bool(bot_cfg.get("public_by_default", True))

    intents = discord.Intents.default()

    class CinePiRagBot(discord.Client):
        def __init__(self) -> None:
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)

        async def setup_hook(self) -> None:
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
            else:
                await self.tree.sync()

    client = CinePiRagBot()

    @client.event
    async def on_ready() -> None:  # pragma: no cover - exercised manually
        print(f"Logged in as {client.user} | chunks indexed: {db.count_chunks()}")

    @client.tree.command(name="ask", description="Ask the CinePi/Cinemate troubleshooting knowledge base")
    @app_commands.describe(question="What do you want to troubleshoot?", private="Only show the answer to you")
    async def ask(interaction: discord.Interaction, question: str, private: bool = False) -> None:
        if not allowed_channel(interaction.channel_id, allowed_ids):
            await interaction.response.send_message("This bot is not enabled in this channel.", ephemeral=True)
            return

        ephemeral = private or not public_by_default
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        response = await asyncio.to_thread(answer_question, db, llm, question, top_k, retrieval_config)
        for part in split_discord_message(response):
            await interaction.followup.send(part, ephemeral=ephemeral)

    @client.tree.command(name="search", description="Search indexed CinePi/Cinemate chunks")
    @app_commands.describe(query="Search terms")
    async def search(interaction: discord.Interaction, query: str) -> None:
        if not allowed_channel(interaction.channel_id, allowed_ids):
            await interaction.response.send_message("This bot is not enabled in this channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        results = await asyncio.to_thread(db.search, query, min(top_k, 5), retrieval_config)
        if not results:
            await interaction.followup.send("No matching indexed chunks found.", ephemeral=True)
            return

        lines = []
        for i, result in enumerate(results, start=1):
            source = result.get("path_or_url") or result.get("source_title")
            lines.append(f"**[{i}] {result['title']}**\nSource: `{source}`\n{short(result['content'], 350)}")
        for part in split_discord_message("\n\n".join(lines)):
            await interaction.followup.send(part, ephemeral=True)

    @client.tree.command(name="health", description="Check the CinePi/Cinemate RAG bot status")
    async def health(interaction: discord.Interaction) -> None:
        provider = config.get("llm", {}).get("default_provider", "offline")
        await interaction.response.send_message(
            f"CinePi RAG bot is running. Indexed chunks: `{db.count_chunks()}`. LLM provider: `{provider}`.",
            ephemeral=True,
        )

    client.run(token)


if __name__ == "__main__":
    run_bot()
