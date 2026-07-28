# STATUS.md

Maintenance rule: **OVERWRITE** this file on every update. It is the single
source of current state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-07-28

## Phase

Agentic perpetual-futures trading-bot scaffold. Priority implementation is
`0/2` complete.

## Current State

- The repository is a human-harnessed, non-executing scaffold; it is not live
  trading software.
- Twenty-seven commits are summarized in `HISTORY.md`; current HEAD is `7200911`.
- `OwnerQwenAPI` includes shared review-only synonym and reduce-and-protect
  skills, while `MinistralFilterAPI` includes MCP take-profit protection; no
  agent has direct exchange access.
- AG2 TelegramAgent provides pull-based retrieval through one shared Lightsail
  worker, per-chat adapters, one authorized user session, and per-message
  durable receipts rather than a channel-level cursor.
- The scaffold preserves provenance, uses ElastiCache-compatible owner reply
  trees, supports private S3/DynamoDB boundaries, and sends chronological parent
  context to QWEN and Ministral.
- Parent-message IDs resolve concurrent live trade cursors by symbol, exchange,
  and direction. Each cursor retains active Hyperliquid/Bitget order and position
  IDs in a DynamoDB repository boundary until the position is fully closed.
- Each owner QWEN agent emits five strategy candidates. Confidence selects one;
  its tier, recommended size, leverage, and provenance persist for the position
  lifecycle unless an explicit parent-linked update advances the policy
  revision. Deterministic risk separately enforces pair blacklisting,
  price-deviation thresholds, leverage, and cumulative owner/pair
  position-value limits.
- The scaffold moves omitted stop-loss derivation from QWEN to a versioned
  Ministral policy using MCP market cap, volume, and `5m`/`15m`/`1h`/`4h` KDJ,
  Bollinger-width, and ATR inputs. The derived distance is bounded to
  `1.25%`-`7.5%` from entry 1, or from the average of entry 1 and entry 2 when
  both are present, within a one-second reasoning budget.
- Ministral also exposes typed MCP-event protection for TP1 entry protection
  and TP2-to-TP1 stop movement while TP3 remains pending, with idempotent
  decisions that never loosen an existing stop.
- The Telethon image hydrator and authentic serial RAG corpus are not yet
  implemented. Current media archival and QWEN multimodal delivery remain
  scaffold boundaries; synonym inference remains a placeholder until RAG is
  populated.
- Last verification: 71 tests passed with the active Python 3.11 environment;
  `uv` remains unavailable in the sandbox because of Snap permissions.

## Next Actions

### 1. Telethon Image Hydrator

- Retrieve media by `chat_id` and message ID through the authorized session.
- Validate, hash, archive, and attach private S3 provenance before metadata,
  reply-tree, QWEN, and message-receipt processing.
- Send current and chronological parent images to QWEN as multimodal inputs.
- Add network-free tests for success, failures, limits, duplicate hashes, and
  parent-image prompts.

Complete when every available current and parent image reaches QWEN with an ID,
hash, and private S3 provenance before its message receipt is recorded.

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

- Replace in-memory test storage with production S3, message-receipt, and
  versioned trade-cursor DynamoDB adapters.
- Implement model-specific Bedrock QWEN and Ministral multimodal adapters.
- Complete Bitget/Hyperliquid MCP market-analysis adapters for the typed
  liquidity and indicator snapshot.
- Rebuild owner reply-tree indexes after worker restarts without DynamoDB reads
  for live prompt context.
- Add end-to-end replay tests before any live execution experiment.

## Document Map

| File | Purpose | Maintenance |
| --- | --- | --- |
| `STATUS.md` | Current state and active priorities | Overwrite |
| `HISTORY.md` | Committed development history | Append-only |
| `AGENTS.md` | Agent and repository contract | Update when boundaries change |
| `SKILLS.md` | Repeatable implementation skills | Update when workflows change |
