# STATUS.md

Maintenance rule: **OVERWRITE** this file on every update. It is the single
source of current state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-08-27

## Phase

Agentic perpetual-futures trading-bot scaffold. Priority implementation is
`0/2` complete.

## Current State

- The repository is a human-harnessed, non-executing scaffold; it is not live
  trading software.
- The full CrewAI replacement is currently a documented target architecture;
  the existing source layout has not yet been migrated.
- Manual codebase review by the repository owner and manual addition of
  authentic serial RAG examples are explicit priorities before further use.
- README wording now clarifies that five-tier candidates cover every incoming
  signal, primarily lifecycle continuations.
- Forty-one commits are summarized in `HISTORY.md`; current HEAD is `d6143c0`.
- `OwnerQwenAPI` includes shared review-only synonym and reduce-and-protect
  skills, while `MinistralFilterAPI` includes MCP take-profit protection; no
  agent has direct exchange access.
- AG2 TelegramAgent provides pull-based retrieval through one shared Lightsail
  worker, per-chat adapters, one authorized user session, and per-message
  durable receipts rather than a channel-level cursor.
- The scaffold preserves provenance, uses ElastiCache-compatible owner reply
  trees, supports private S3/DynamoDB boundaries, and sends chronological parent
  context to QWEN and Ministral.
- Parent-message IDs resolve concurrent live trade cursors by symbol, exchange
  network, and direction. Each cursor retains active Aster/Hyperliquid order and
  position IDs in a DynamoDB repository boundary until the position is fully
  closed.
- Testnet-first Aster and Hyperliquid augmented proxies use pinned upstream
  dependencies and contracts. Aster has a dynamic official `aster-mcp` client
  path; Hyperliquid currently uses direct `/info` reads and emits an upstream
  handoff contract without invoking `mcp-hyperliquid` directly. Lambda order
  submission remains unimplemented. Paired P/L comparison uses only identical
  signals on both testnets.
- Each owner QWEN agent emits five strategy candidates for every incoming
  signal. At lifecycle commencement, confidence selects the initial tier,
  recommended size, leverage, and provenance; continuations inherit that
  policy unless an explicit parent-linked update advances its revision.
  Deterministic risk separately enforces pair blacklisting, price-deviation
  thresholds, leverage, and cumulative owner/pair position-value limits.
- Omitted stop-loss inference now combines pair type, volume, and
  `5m`/`15m`/`1h`/`4h` EMA, MACD, KDJ, RSI, Bollinger, ATR, and volatility
  components, bounded to `1.2%`-`8%` from entry 1 or the first two-entry
  average within a one-second budget.
- Ministral also exposes typed MCP-event protection for TP1 entry protection
  and TP2-to-TP1 stop movement while TP3 remains pending, with idempotent
  decisions that never loosen an existing stop.
- The Telethon image hydrator and authentic serial RAG corpus are not yet
  implemented. Current media archival and QWEN multimodal delivery remain
  scaffold boundaries; synonym inference remains a placeholder until RAG is
  populated. RAG profile JSON now reserves ordered Telegram message IDs and
  URLs plus a private S3 archive URI, but no authentic examples are fabricated.
- Last verification: all 105 tests passed under Python 3.11; Ruff and
  `compileall` also passed.

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
- Record every example message's Telegram ID and URL in JSON and archive the
  complete example in private AWS S3 with its URI in the same JSON object.
- Label `new_signal`, `continuation`, `duplicate`, and `ambiguous` cases.
- Preserve omitted TP/SL updates, intended orders, media provenance, and
  correct or incorrect outcomes; redact unnecessary personal data.
- Version the JSON profiles and add replay fixtures and evaluation metrics.

Complete when every owner QWEN agent has a small, manually added and
human-reviewed replayable serial RAG set with authentic text/image patterns,
Telegram IDs/URLs, and S3 archive references.

## Further Priorities

- Replace in-memory test storage with production S3, message-receipt, and
  versioned trade-cursor DynamoDB adapters.
- Implement model-specific Bedrock QWEN and Ministral multimodal adapters.
- Complete Aster/Hyperliquid MCP market-analysis adapters for the typed
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
