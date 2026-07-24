# HISTORY.md

Maintenance rule: **APPEND-ONLY**. Never edit or delete past entries. Append
new sessions at the bottom, newest last.

This file summarizes the committed development history. Current state is
maintained in `STATUS.md`.

## Committed History

### 2026-06-25 — `75e43bc`: initial scaffold

Created the first Telegram-based multi-agent perpetual-futures scaffold, with
repository guidance, a BitMart MCP server, dependency files, and lock data.

### 2026-07-02 — `d1c97e5`: Figma-based application scaffold

Added the Figma-derived project structure, README and mapping documents, owner
RAG profiles, Pydantic schemas, QWEN and Ministral boundaries, orchestration,
performance weighting, exchange gateways, AWS execution placeholders, and
initial schema tests.

### 2026-07-05 — `74da2b2`: unified Python environment

Moved dependency management to the project-level environment and removed the
nested BitMart MCP environment files.

### 2026-07-13 — `daadae5`: signal deduplication scaffold

Added exact input deduplication and semantic signal-deduplication boundaries,
updated schemas, normalizers, QWEN/Ministral orchestration, tests, and the
Figma asset.

### 2026-07-13 — `793fa1d`: standardized repository guidance

Replaced the singular agent guidance with `AGENTS.md`, expanded `SKILLS.md`,
and added the project-level `uv` configuration and lock file.

### 2026-07-14 — `faf0968`: simplified repository README

Moved the trading-bot README to the repository root and removed the redundant
nested README configuration.

### 2026-07-16 — `6138bc3`: refined owner routing

Clarified owner-channel routing and the backtesting-only status of inactive
channels.

### 2026-07-17 — `24d44e7`: defined the QWEN RAG harness

Documented serial RAG message handling, owner-specific examples, confidence
calculation, and the order-analysis workflow in `AGENTS.md` and `SKILLS.md`.

### 2026-07-18 — `5dc724d`: added TP/SL inference and pair blacklisting

Added documentation for stop-loss inference, take-profit handling, and
deterministic trading-pair blacklisting.

### 2026-07-21 — `7cdd829`: migrated ingestion to AG2 TelegramAgent

Replaced the Telegram webhook concept with pull-based AG2 TelegramAgent
retrieval, durable per-channel cursors, provenance-preserving normalization,
media metadata, AWS boundaries, dependencies, documentation, and ingestion
tests.

### 2026-07-21 — `3580b10`: implemented the corrected ingestion flow

Added the ingestion pipeline, S3 and DynamoDB storage contracts, Bedrock handoff
boundary, and additional cursor and pipeline tests.

### 2026-07-21 — `9cabcef`: clarified the deployment model

Documented one shared Lightsail worker, one authorized Telegram user session,
lightweight per-chat retrieval adapters, and the distinction between channel
adapters and owner QWEN agents.

### 2026-07-22 — `c7abbbd`: added confidence policy and serial parent context

Replaced generic risk gating with confidence-based strategy selection and the
two explicit hard rejection checks, added the indexed in-memory message cache
and tree-derived chronological parent context, renamed the mapping document,
and expanded the related schemas, prompts, tests, and boundaries.

### 2026-07-22 — `ba782d6`: refined owner-specific Telegram guidance

Documented delayed TP/SL follow-ups, duplicate risk, and the narrowly scoped
minimalist Chinese acknowledgment workflow for the A-zhu private chat.

### 2026-07-22 — `b4424d6`: minimized guidance and added active priorities

Reduced `AGENTS.md` to its essential contract and added `TODO.md` with the
Telethon image hydrator and authentic serial RAG examples as the first two
priorities, followed by production adapters, restart recovery, and replay
testing.

### 2026-07-22 — `554200e`: added history and status tracking

Added this append-only commit history and the overwrite-style `STATUS.md`,
including the current scaffold state, next actions, and open gaps. The
codebase is mostly prompted GPT-5.6 Luna and Sol coding produced under time
constraints and requires careful human review before further use.

### 2026-07-22 — `510098f`: removed the redundant TODO file

Deleted `TODO.md` and kept the active priorities in `STATUS.md`, while
preserving the append-only history and current-state documentation split.

### 2026-07-23 — `27cce05`: defined shared agent skill APIs and owner QWEN synonym inference

Corrected the Trading Message Synonym Inference skill and added the explicit
`skills_api/` package. Merged the review-only synonym skill into every
`OwnerQwenAgent`, updated the scaffold documentation and file map, and kept the
boundary free of exchange calls.

### 2026-07-23 — `a02e839`: synchronized status and editor imports

Updated `HISTORY.md` and `STATUS.md` for `27cce05` and added the VS Code source
path needed for Pylance to resolve the package.

### 2026-07-24 — `1c1c768`: added position-management skills

Added multi-timeframe deterministic omitted stop-loss derivation, the owner
QWEN reduce-and-protect hypothesis, and Ministral MCP take-profit fill
protection. Added typed skill APIs, gateway boundaries, schemas, and focused
tests; the scaffold remains non-executing and requires human review.

### 2026-07-24 — `f0f609b`: clarified human-review requirements

Clarified in `AGENTS.md` that this prompted-generated scaffold requires careful
human code review and backtesting of previous Telegram trading signals before
further use.

### 2026-07-24 — `a2c9a5c`: aligned instant-order deviation thresholds

Implemented deterministic `0.5%`, `0.25%`, and `0.125%` price-deviation limits
for generic altcoins, major/TradFi perpetuals, and BTC, respectively, with
explicit mixed-channel TradFi classification and boundary tests.

### 2026-07-25 — pending: separated ingestion receipts and live trade cursors

Removed the channel-wide ingestion cursor, retained independent message
receipts, and added concurrent parent-linked trade cursors with versioned
BitMart/Bitget order and position metadata for DynamoDB.
