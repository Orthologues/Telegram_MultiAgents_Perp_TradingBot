# STATUS.md

Maintenance rule: **OVERWRITE** this file on every update. It is the single
source of current state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-07-22

## Phase

Agentic perpetual-futures trading-bot scaffold. Priority implementation is
`0/2` complete.

## Current State

- The repository is a human-reviewed, non-executing scaffold; it is not live
  trading software.
- Fifteen commits are summarized in `HISTORY.md`; current HEAD is `b4424d6`.
- AG2 TelegramAgent provides pull-based retrieval through one shared Lightsail
  worker, per-chat adapters, one authorized user session, and durable cursors.
- The scaffold preserves provenance, supports private S3/DynamoDB boundaries,
  maintains owner-scoped in-memory reply trees, and sends chronological parent
  context to QWEN and Ministral.
- Confidence selects strategy tiers. Hard rejection is limited to a pair
  blacklist or an instant-order MCP price too far from the message reference.
- The Telethon image hydrator and authentic serial RAG corpus are not yet
  implemented. Current media archival and QWEN multimodal delivery remain
  scaffold boundaries.
- Last verification: 20 tests passed; compilation and diff checks passed.

## Next Actions

### 1. Telethon Image Hydrator

- Retrieve media by `chat_id` and message ID through the authorized session.
- Validate, hash, archive, and attach private S3 provenance before metadata,
  reply-tree, QWEN, and cursor processing.
- Send current and chronological parent images to QWEN as multimodal inputs.
- Add network-free tests for success, failures, limits, duplicate hashes, and
  parent-image prompts.

Complete when every available current and parent image reaches QWEN with an ID,
hash, and private S3 provenance before the cursor advances.

### 2. Authentic Serial RAG Examples

- Add authorized chronological text/image sequences for every owner and
  channel, including multi-level replies.
- Label `new_signal`, `continuation`, `duplicate`, and `ambiguous` cases.
- Preserve omitted TP/SL updates, intended orders, media provenance, and
  correct or incorrect outcomes; redact unnecessary personal data.
- Version the JSON profiles and add replay fixtures and evaluation metrics.

Complete when every owner QWEN agent has a small, human-reviewed, replayable
serial RAG set with authentic text/image patterns.

## Further Priorities

- Replace in-memory test storage with production S3 and DynamoDB adapters.
- Implement model-specific Bedrock QWEN and Ministral multimodal adapters.
- Rebuild owner reply-tree indexes after worker restarts without DynamoDB reads
  for live prompt context.
- Add end-to-end replay tests before any live execution experiment.

## Document Map

| File | Purpose | Maintenance |
| --- | --- | --- |
| `STATUS.md` | Current state and active priorities | Overwrite |
| `TODO.md` | Detailed task list | Update with priorities |
| `HISTORY.md` | Committed development history | Append-only |
| `AGENTS.md` | Agent and repository contract | Update when boundaries change |
| `SKILLS.md` | Repeatable implementation skills | Update when workflows change |
