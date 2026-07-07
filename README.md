# CinePi / Cinemate RAG Starter

A local-first starter project for turning reviewed CinePi/Cinemate docs and opt-in Discord knowledge into a searchable troubleshooting Q&A system.

This repo is intentionally small and readable. The first working version uses:

- **SQLite + FTS5** for searchable chunks
- **Markdown/TXT ingestion** for official docs and notes
- **Opt-in Discord JSONL ingestion** for solved/support threads
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
ollama pull qwen2.5:14b-instruct
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
      model: qwen2.5:14b-instruct
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
      model: Qwen/Qwen2.5-32B-Instruct
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
  ingestion.py        # docs + opt-in Discord ingestion
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
