# CinePi / Cinemate RAG Roadmap

## Project goal

Build a local-first, maintainable troubleshooting and documentation assistant for CinePi/Cinemate that can:

1. Ingest official docs and maintainer-approved knowledge.
2. Convert opt-in Discord troubleshooting threads into structured knowledge.
3. Generate clean Markdown documentation from reviewed knowledge.
4. Answer user questions with citations through a RAG API, CLI, Discord bot, or web UI.
5. Switch between local LLMs and hosted LLMs through configuration.

The core principle is: **community chat should inform reviewed docs; reviewed docs should power the bot.**

## Decisions made so far

### 1. RAG over fine-tuning

We chose RAG instead of model fine-tuning because troubleshooting knowledge changes over time and needs citations. Fine-tuning would make it harder to inspect sources, update stale information, or separate advice by hardware/software version.

### 2. Local-first, hosted-optional LLM routing

The user has a 5090 32 GB GPU, so the system should be able to run local models through Ollama, vLLM, or llama.cpp-style services. Hosted models remain useful as optional fallbacks for difficult extraction, answer verification, or polished documentation generation.

### 3. Opt-in Discord knowledge intake

The system should not depend on broad historical scraping. The safer workflow is to use official docs first and then ingest Discord threads/messages that are intentionally submitted, marked as solved, or otherwise approved for documentation use.

### 4. Structured knowledge before generated docs

Instead of generating one giant summary document, the pipeline extracts structured troubleshooting records first. Those records can then be reviewed, merged, and turned into canonical docs.

## What this starter repo includes

### Implemented

- SQLite database schema for sources and chunks.
- SQLite FTS5 search for fast local retrieval.
- Markdown/TXT source ingestion.
- Opt-in Discord JSONL thread ingestion.
- Basic redaction for sensitive-looking values.
- Source-aware chunking for Markdown headings and long text.
- LLM gateway for local or hosted OpenAI-compatible providers.
- Offline fallback answering when no model is configured.
- RAG prompt that asks for citations and uncertainty handling.
- Knowledge extraction command that writes JSONL draft items.
- Documentation generation command for approved knowledge items.
- Example configuration and example Discord intake file.
- Unit tests for redaction, chunking, and retrieval.

### Not yet implemented

- Vector embeddings and semantic retrieval.
- Reranking.
- Admin/review web UI.
- Discord slash-command bot with live RAG answers.
- GitHub ingestor that pulls directly from repos.
- Docs-site crawler for the Cinemate CLI guide.
- Automated duplicate detection and merge workflow.
- Eval harness for comparing local vs hosted models.
- Source citation links back to Discord message URLs.
- Version-aware answer filtering.
- Scheduled re-indexing.
- Maintainer approval workflow.

## Proposed architecture

```text
Official docs / GitHub repos
        +
Opt-in solved Discord threads
        +
Maintainer notes
        ↓
Ingestion and redaction
        ↓
Chunks with metadata
        ↓
Structured knowledge extraction
        ↓
Human review and merge
        ↓
Canonical Markdown docs
        ↓
Search index / vector DB
        ↓
RAG API and Discord bot
        ↓
Cited troubleshooting answers
```

## LLM architecture

All model calls go through the LLM gateway.

```text
RAG / extraction / doc generation
        ↓
LLM Gateway
        ↓
Ollama / vLLM / hosted OpenAI-compatible API
```

Initial local model serving targets:

- Ollama for easiest local development.
- vLLM for higher-throughput local serving.
- Hosted OpenAI-compatible APIs as optional fallback.

Recommended task routing:

```text
Chunk tagging: local small/balanced model
Knowledge extraction: strong local model
Doc generation: strong local or hosted model
Normal Q&A: local model
Difficult/conflicting Q&A: hosted fallback or strongest local model
Evaluation/judging: hosted or strongest local model
```

## Milestones

### Milestone 1 — Local docs-only RAG

Status: **Started in this repo**

Goals:

- Ingest local Markdown/TXT docs.
- Search with SQLite FTS5.
- Ask questions from CLI.
- Return source-backed answers.
- Configure local or hosted LLM.

Remaining work:

- Add real Cinemate and cinepi-raw docs into `data/sources/`.
- Confirm the citation format is useful.
- Add a few hand-written troubleshooting examples.

### Milestone 2 — Opt-in Discord knowledge intake

Status: **Partially started**

Goals:

- Accept JSONL exports of approved Discord threads.
- Redact sensitive data.
- Chunk thread conversations in a useful way.
- Extract troubleshooting records.

Remaining work:

- Decide the exact opt-in workflow in Discord.
- Build a small exporter or bot command for marked threads.
- Add maintainer/source metadata.
- Add duplicate detection.

### Milestone 3 — Review and canonical docs

Status: **Scaffolded**

Goals:

- Extract structured knowledge items.
- Review items before publishing.
- Generate Markdown troubleshooting docs.
- Re-index generated docs.

Remaining work:

- Add an admin review UI.
- Add statuses: extracted, needs_review, approved, rejected, superseded, published.
- Add merge/dedup flow.
- Create a docs folder structure by topic.

### Milestone 4 — Discord Q&A bot

Status: **Not implemented**

Goals:

- Add slash commands such as `/ask`, `/troubleshoot`, and `/suggest-doc-fix`.
- Query the local RAG server.
- Return concise answers with citations.
- Avoid answering when retrieved context is weak.

Remaining work:

- Choose Discord library.
- Add token/env config.
- Add permission checks.
- Add rate limiting and logging.

### Milestone 5 — Semantic retrieval and evaluation

Status: **Not implemented**

Goals:

- Add embeddings and vector search.
- Add reranking.
- Add evaluation questions.
- Compare local and hosted models.

Remaining work:

- Decide between Qdrant and pgvector.
- Add local embedding provider.
- Build eval YAML format.
- Score citation accuracy, command accuracy, and hallucination rate.

## Near-term next steps

1. Add official Cinemate and cinepi-raw docs to `data/sources/`.
2. Run the docs-only RAG prototype locally.
3. Configure Ollama or vLLM in `config.yaml`.
4. Add 5–10 approved troubleshooting examples as JSONL.
5. Test retrieval and answer quality.
6. Add an extraction/review pass.
7. Generate the first draft troubleshooting docs.

## Risks and mitigations

### Risk: raw Discord content creates privacy or policy problems

Mitigation: ingest only opt-in or approved threads. Redact sensitive data. Treat Discord as source material for reviewed docs, not as training data.

### Risk: local model hallucinates commands

Mitigation: require citations, retrieve source chunks, and add an answer verifier before Discord bot deployment.

### Risk: stale advice from old CinePi versions

Mitigation: attach version, hardware, software, and source metadata to chunks and knowledge items.

### Risk: too much abstraction too early

Mitigation: keep this starter repo small. Use simple modules and add abstractions only when they are reused.

## Definition of done for v1

A useful v1 should be able to:

- Ingest current Cinemate/cinepi-raw docs.
- Ingest a small set of approved Discord troubleshooting cases.
- Answer common questions from the CLI with citations.
- Run locally with Ollama or vLLM.
- Fall back to hosted models by config.
- Generate draft Markdown troubleshooting docs from reviewed knowledge items.
