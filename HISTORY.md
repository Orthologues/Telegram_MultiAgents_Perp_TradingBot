# HISTORY.md

Maintenance rule: **APPEND-ONLY**. Never edit or delete past entries. Append
new sessions at the bottom, newest last.

This file summarizes the committed development history. Current state is
maintained in `STATUS.md`; active work is maintained in `TODO.md`.

## Committed History

2026-06-25 — `75e43bc`: initial scaffold

Created the first Telegram-based multi-agent perpetual-futures scaffold, with
repository guidance, a BitMart MCP server, dependency files, and lock data.

2026-07-02 — `d1c97e5`: Figma-based application scaffold

Added the Figma-derived project structure, README and mapping documents, owner
RAG profiles, Pydantic schemas, QWEN and Ministral boundaries, orchestration,
performance weighting, exchange gateways, AWS execution placeholders, and
initial schema tests.

2026-07-05 — `74da2b2`: unified Python environment

Moved dependency management to the project-level environment and removed the
nested BitMart MCP environment files.

2026-07-13 — `daadae5`: signal deduplication scaffold

Added exact input deduplication and semantic signal-deduplication boundaries,
updated schemas, normalizers, QWEN/Ministral orchestration, tests, and the
Figma asset.

2026-07-13 — `793fa1d`: standardized repository guidance

Replaced the singular agent guidance with `AGENTS.md`, expanded `SKILLS.md`,
and added the project-level `uv` configuration and lock file.

2026-07-14 — `faf0968`: simplified repository README

Moved the trading-bot README to the repository root and removed the redundant
nested README configuration.

2026-07-16 — `6138bc3`: refined owner routing

Clarified owner-channel routing and the backtesting-only status of inactive
channels.

2026-07-17 — `24d44e7`: defined the QWEN RAG harness

Documented serial RAG message handling, owner-specific examples, confidence
calculation, and the order-analysis workflow in `AGENTS.md` and `SKILLS.md`.

2026-07-18 — `5dc724d`: added TP/SL inference and pair blacklisting

Added documentation for stop-loss inference, take-profit handling, and
deterministic trading-pair blacklisting.

2026-07-21 — `7cdd829`: migrated ingestion to AG2 TelegramAgent

Replaced the Telegram webhook concept with pull-based AG2 TelegramAgent
retrieval, durable per-channel cursors, provenance-preserving normalization,
media metadata, AWS boundaries, dependencies, documentation, and ingestion
tests.

2026-07-21 — `3580b10`: implemented the corrected ingestion flow

Added the ingestion pipeline, S3 and DynamoDB storage contracts, Bedrock handoff
boundary, and additional cursor and pipeline tests.

2026-07-21 — `9cabcef`: clarified the deployment model

Documented one shared Lightsail worker, one authorized Telegram user session,
lightweight per-chat retrieval adapters, and the distinction between channel
adapters and owner QWEN agents.

2026-07-22 — `c7abbbd`: added confidence policy and serial parent context

Replaced generic risk gating with confidence-based strategy selection and the
two explicit hard rejection checks, added the indexed in-memory message cache
and tree-derived chronological parent context, renamed the mapping document,
and expanded the related schemas, prompts, tests, and boundaries.

2026-07-22 — `ba782d6`: refined owner-specific Telegram guidance

Documented delayed TP/SL follow-ups, duplicate risk, and the narrowly scoped
minimalist Chinese acknowledgment workflow for the A-zhu private chat.

2026-07-22 — `b4424d6`: minimized guidance and added active priorities

Reduced `AGENTS.md` to its essential contract and added `TODO.md` with the
Telethon image hydrator and authentic serial RAG examples as the first two
priorities, followed by production adapters, restart recovery, and replay
testing.
