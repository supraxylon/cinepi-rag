# CinePi / Cinemate RAG Starter

A local-first starter project for turning reviewed CinePi/Cinemate docs and opt-in Discord knowledge into a searchable troubleshooting Q&A system.

This repo is intentionally small and readable. The first working version uses:

- **SQLite + FTS5** for searchable chunks
- **Markdown/TXT ingestion** for official docs and notes
- **Opt-in Discord JSONL ingestion** for solved/support threads
- **DiscordChatExporter-style channel JSON ingestion** for raw exports staged for extraction/review
- **Trusted-author authority metadata and retrieval boosts** for maintainers like `cinepi`, `schoolpost`, and `Tiramisioux`
- **Provider-agnostic LLM gateway** for local or hosted models
- **Offline extractive fallback** so the project works before an LLM is configured
- **Roadmap-first structure** so vector search, review UI, and Discord bot features can be added incrementally

## Why this shape?

The goal is not to silently scrape Discord into a chatbot or train a model on raw chat history. The safer, more maintainable path is:

```text
Official docs + opt-in solved threads
  -> normalized chunks
  -> reviewed knowledge items
  -> generated markdown docs
  -> RAG Q&A with citations
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
cp config.example.yaml config.yaml
cinepi-rag init-db
cinepi-rag ingest-docs data/sources
cinepi-rag ingest-discord data/discord_intake/example_threads.jsonl
# Or ingest DiscordChatExporter-style channel JSON files
cinepi-rag ingest-discord-export /path/to/discord_exports --project cinepi
cinepi-rag search "cinepi.local not resolving"
cinepi-rag ask "Why does cinepi.local work on some devices but not others?"
```

The `ask` command works even without an LLM configured. It will return the most relevant retrieved snippets and citations.

## Add your first docs

Put Markdown or text files in `data/sources/`, for example:

```text
data/sources/cinemate-readme.md
data/sources/cinepi-raw-readme.md
data/sources/cli-user-guide.md
```

Then run:

```bash
cinepi-rag ingest-docs data/sources
```

## Configure a local LLM

The LLM gateway supports OpenAI-compatible APIs, which means the same provider code can call Ollama, vLLM, or hosted APIs.

### Ollama example

Start Ollama and pull a model:

```bash
ollama pull qwen3:30b-a3b-instruct-2507-q4_K_M
```

Edit `config.yaml`:

```yaml
llm:
  default_provider: ollama
  providers:
    ollama:
      type: openai_compatible
      base_url: http://localhost:11434/v1
      api_key: ollama
      model: qwen3:30b-a3b-instruct-2507-q4_K_M
```

Then run:

```bash
python -m cinepi_rag.cli ask "How do I troubleshoot Redis connection errors?"
```

### vLLM example

Start a vLLM OpenAI-compatible server separately, then configure:

```yaml
llm:
  default_provider: vllm
  providers:
    vllm:
      type: openai_compatible
      base_url: http://localhost:8000/v1
      api_key: local-dev-key
      model: Qwen/Qwen3-30B-A3B-Instruct-2507
```

### Hosted OpenAI-compatible example

```yaml
llm:
  default_provider: hosted_openai
  providers:
    hosted_openai:
      type: openai_compatible
      base_url: https://api.openai.com/v1
      api_key_env: OPENAI_API_KEY
      model: gpt-4.1-mini
```

## Discord channel exports

The initial starter repo expected approved JSONL threads. Your actual export shape is different: each `.json` file is a full Discord channel export with top-level `guild`, `channel`, `exportedAt`, `messageCount`, and a `messages` array. The repo now supports that format directly.

```bash
cinepi-rag ingest-discord-export /path/to/discord_exports --project cinepi
```

Useful options:

```bash
# Keep all author names instead of pseudonymizing normal users.
cinepi-rag ingest-discord-export /path/to/discord_exports --preserve-author-names

# Include bot messages.
cinepi-rag ingest-discord-export /path/to/discord_exports --include-bots

# Tune chunk size.
cinepi-rag ingest-discord-export /path/to/discord_exports --max-chars 5000 --max-messages 40
```

The ingestor:

- reads one JSON file at a time;
- stores channel/guild/export metadata on each source and chunk;
- marks these chunks as `review_status: raw` in metadata;
- pseudonymizes normal users by default while preserving Admin/Moderator names;
- keeps reply context when `reference.messageId` points to another message in the same export;
- includes attachment filenames, embed titles, embed descriptions, and forwarded message content;
- strips query strings from Discord CDN URLs so expiring signed URL parameters are not indexed.

The older `ingest-discord` command still exists for intentionally curated JSONL threads.

## Trusted authors and retrieval boosts

Discord exports can contain a lot of casual conversation, so the repo now stores lightweight authority metadata on raw Discord chunks. By default, trusted maintainers keep their names in indexed text while normal users are pseudonymized.

Configure trusted accounts in `config.yaml`:

```yaml
discord:
  trusted_authors:
    - aliases: ["cinepi", "CinePI"]
      score: 2.0
      reason: "project/account"
    - aliases: ["schoolpost", "Schoolpost"]
      score: 2.0
      reason: "creator of CinePI"
    - aliases: ["tiramisioux", "Tiramisioux"]
      score: 2.0
      reason: "creator of Cinemate"

  trusted_roles:
    Admin: 1.5
    Moderator: 1.3

retrieval:
  enable_authority_rerank: true
  authority_boost_weight: 0.15
  pinned_boost_weight: 0.05
  reaction_boost_weight: 0.02
```

The boost is intentionally modest. It helps maintainer, pinned, and highly reacted messages rank higher, but it should not replace review, newer official docs, or citations. Raw Discord chunks still have `review_status: raw` and should be promoted into approved knowledge items before becoming canonical docs.

## Opt-in Discord intake format

This project expects exported or bot-submitted JSONL where each line is a reviewed or opt-in thread. Example:

```json
{"project":"cinemate","title":"cinepi.local does not resolve on Windows","approved_for_kb":true,"messages":[{"author":"user","content":"cinepi.local works on my phone but not my Windows laptop."},{"author":"maintainer","content":"This is usually mDNS/Bonjour. Try the Pi IP address and verify Avahi is running."}]}
```

Records with `approved_for_kb: false` are skipped.

## Common commands

```bash
# Create/reset the local database
cinepi-rag init-db --reset

# Ingest docs
cinepi-rag ingest-docs data/sources

# Ingest opt-in Discord JSONL threads
cinepi-rag ingest-discord data/discord_intake/example_threads.jsonl

# Ingest DiscordChatExporter-style channel JSON files
cinepi-rag ingest-discord-export /path/to/discord_exports --project cinepi

# Search chunks
cinepi-rag search "ssd not mounted"

# Ask a question
cinepi-rag ask "Why are my recordings dropping frames?"

# Extract structured knowledge items from retrieved chunks
cinepi-rag extract "camera not detected"

# Generate draft docs from approved knowledge items
cinepi-rag generate-docs data/knowledge_items docs_generated
```

## Project layout

```text
src/cinepi_rag/
  cli.py              # command-line entrypoint
  config.py           # YAML/env config loading
  db.py               # SQLite schema and persistence
  chunking.py         # readable markdown/text chunking
  ingestion.py        # docs + Discord ingestion
  discord_export.py   # Discord channel export normalization
  llm_gateway.py      # local/hosted provider abstraction
  rag.py              # retrieval + answer generation
  extraction.py       # knowledge-item extraction and doc generation
  utils.py            # small shared helpers
```

## Development notes

Run tests:

```bash
pip install -r requirements-dev.txt
pytest
```

The code favors readability over heavy abstractions. Small logic stays inline unless it is reused across several places.
