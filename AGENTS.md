# AGENTS.md

## Scope

This repository is a deliberately non-executing scaffold for a Telegram-driven
multi-agent perpetual-futures bot. Keep changes small, explicit, and consistent
with the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch-Flowchart).
The implementation map is
[`draft_agentic_perp_trading_bot/docs/arch_to_filename_mapping.md`](draft_agentic_perp_trading_bot/docs/arch_to_filename_mapping.md).

Do not describe placeholder code as live trading code. Never commit API keys,
Telegram API hashes, authorized user sessions, MCP tokens, signatures, or local
secret files.

## Architecture Contract

The flow is:

```text
Telegram channels readable by an authorized user account
  -> one shared AG2 TelegramAgent ingestion worker with per-chat retrieval adapters
  -> Lightsail polling worker (EC2 scale-up) with a durable channel cursor
  -> normalize, filter, OCR-package, and deduplicate input
  -> S3 raw media + DynamoDB message metadata
  -> one QWEN3-VL agent per owner
  -> Ministral3-8B or -14B validation and trading-signal deduplication
  -> performance/weight engine
  -> confidence engine with pair-blacklist and instant-price checks
  -> Bitget/BitMart gateway
  -> Lambda execution with Secrets Manager
```

There is no Telegram bot webhook or Lambda ingestion entrypoint. AG2
TelegramAgent is experimental and its retrieve tool is pull-based: poll by the
last committed Telegram message id and treat the resulting cadence as
near-real-time, not native push. The deployment is one long-lived ingestion
worker and one authorized Telegram user session, scheduled across the target
channels. Each channel has its own `chat_id`, cursor, and provenance
configuration. Because the AG2 retrieval API is scoped to one `chat_id`, the
worker may create or reuse lightweight per-chat TelegramAgent adapters inside
the same process; these are not separate services or additional owner QWEN
trading agents.

The ingestion executor must expose only retrieval; do not register
`TelegramSendTool`. Store Telegram API ID/hash and the authorized user session
outside the repository. Use one active, leased worker per Telegram user session
and serialize access unless the session implementation is proven safe for
concurrent clients. AG2 retrieval returns text and a media-presence flag, not
media bytes, so hydrate media through an adjacent authenticated adapter before
archiving it in S3. Persist message metadata and media first, then atomically
advance the per-channel cursor in DynamoDB. This preserves at-least-once
delivery across worker restarts. Before Bedrock delivery, populate
`parent_messages` with all earlier reply-tree message IDs from the owner-scoped
in-memory index in oldest-to-newest order; write the enriched record to
DynamoDB, but do not read DynamoDB for parent reconstruction.
Build a `TelegramPromptContext` from the in-memory snapshots and pass the same
context to QWEN and Ministral. The prompt must contain one ID-labeled block per
parent, oldest first, followed by the current message block.
DynamoDB message metadata is primarily the historical record for replay,
backtesting, and strategy optimization, including omitted take-profit or
stop-loss inference outcomes and deterministic pair-blacklisting criteria. It
is not a live parent-context source for model prompts.

The four QWEN agents are owner-specific. Channel and asset-group metadata stay
attached to the message; they do not create extra agents:

| Owner | Routing examples | Caveats / challenges |
| --- | --- | --- |
| A, Shu-qin | Mixed BTC/ETH, alts, and TradFi; day or longer strategy | Wording is more ambiguous and message updates are less frequent. |
| B, Lao-tu | BTC/ETH channel plus alts/TradFi channel; strategy lasting 1-3 days | Instant altcoin orders often omit a stop-loss. Use the stop-loss inference skill; do not use a fixed keyword rule. |
| C, Bi-jia-suo | BTC/ETH channel plus alts/TradFi channel; day strategy | Instant altcoin orders often omit a stop-loss. Use the stop-loss inference skill; do not use a fixed keyword rule. |
| D, A-zhu | BTC/ETH channel plus day and longer alts/TradFi channels; three separate channels | Likely inactive since mid-June 2026; use signals for backtesting only. |

Each QWEN agent uses manually maintained serial JSON RAG profiles and emits
preliminary JSON hypotheses in the conservative, intermediate, and radical
strategy tiers. QWEN output is never an execution command.

The Ministral 8B and 14B variants must implement the same interface so they can
be A/B-tested. The filter validates schema, rejects prompt-injected or
ambiguous content, deduplicates equivalent hypotheses, and emits a normalized
`CanonicalTradeIntent` only when approved. Position sizing, leverage, symbols,
strategy-tier selection and the two explicit execution checks remain
deterministic code.

When an order omits a stop-loss, the owner-specific QWEN stop-loss inference
skill must propose a candidate price from serial RAG examples and market
context. Before evaluating that candidate, the confidence engine must reject a
blacklisted pair. For an instant order, the MCP-supplied current price must not
be too distant from the message reference price. An inferred stop-loss remains
a backtestable strategy input, not a separate hard rejection rule.

The temporary pair blacklist is calculated deterministically from net closed
trade outcomes over a trailing 90-day window. QWEN confidence or reasoning
cannot override a blacklisted exchange/symbol pair.

Input deduplication and signal deduplication are separate:

- `telegram_ingestion/agent_worker.py` validates per-channel TelegramAgent
  retrieval batches and keeps cursor commit separate from durable processing.
- `telegram_ingestion/deduplication.py` provides exact-duplicate shortcuts and
  candidate context; the owner-specific QWEN deduplication skill reasons about
  semantic repeats and continuations.
- `ministral_filter/signal_deduplication.py` prevents equivalent QWEN signals
  from being weighted or executed twice.

ECS may provide low-latency Bitget/BitMart WebSocket market data. Order
execution uses HTTPS REST with exchange signing and slippage checks. AWS
Lambda retrieves credentials from Secrets Manager at the execution boundary.

## Agent Harness Workflow

This is the crucial reasoning and validation path for every trading message:

```text
TelegramAgent-retrieved sequence
  -> retrieve owner/strategy-specific RAG examples
  -> QWEN reasoning
  -> structured trade hypothesis
  -> MCP validation or simulation
  -> confidence tier and explicit execution checks
  -> result, error, and evaluation record
```

The RAG examples must preserve serial Chinese message context, intended
execution orders for each strategy tier, and incorrectly executed examples.
QWEN interprets the sequence and produces the hypothesis; it never submits an
order. MCP validation or simulation checks exchange-specific behavior, while
the confidence engine records the strategy tier and explicit rejection reason.
Every accepted,
rejected, simulated, or failed path must produce a traceable evaluation record.

## Repository Rules

- Put application code under `draft_agentic_perp_trading_bot/src/`.
- Put tests under `draft_agentic_perp_trading_bot/tests/`.
- Keep exchange-specific behavior behind `mcp_gateway/`; do not call an
  exchange directly from an LLM agent.
- Extend Pydantic schemas before wiring a new stage. Preserve trace fields such
  as owner, channel, strategy tier, deduplication key, and model id.
- Persist production deduplication state in a shared store such as DynamoDB;
  the current in-memory classes are test scaffolds only.
- Persist one monotonic cursor per logical channel with conditional writes. Do
  not advance it until raw media and searchable message metadata are durable.
- Keep S3 media archival, DynamoDB metadata persistence, and the Bedrock input
  handoff behind `telegram_ingestion/storage.py` and `pipeline.py`; do not mix
  those responsibilities into the owner QWEN agents.
- Keep AG2 TelegramAgent isolated from QWEN and the exchange path. It retrieves
  source messages only and must never emit a trade hypothesis or submit orders.
- Keep owner-specific RAG profiles and labeled examples JSON, versionable, and
  free of credentials. The examples must contain serial Chinese message
  sequences paired with intended execution orders for each strategy tier, plus
  annotated incorrectly executed examples.

## Commands

Run from the single-environment project root:

```bash
cd draft_agentic_perp_trading_bot
uv sync --extra aws --extra telegram --extra dev
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
git diff --check
```

For a runtime-only environment, use `uv sync`. Do not create a nested Python
environment for an individual MCP server.

## Change Workflow

For changes involving Chinese Telegram interpretation or deduplication, do not
add keyword, substring, or regular-expression rules for owner wording. Begin
with the owner-specific QWEN RAG corpus:

1. Add serial examples showing the Chinese messages, the intended execution
   order, strategy tier, and whether the outcome was correct or incorrectly
   executed.
2. Include exact reposts, quoted or screenshot repeats, staged entries, entry
   updates, take-profit or stop-loss updates, execution notices, unrelated
   commentary, genuinely new signals, and ambiguous follow-ups.
3. Label the semantic relation as `duplicate`, `continuation`, `new_signal`, or
   `ambiguous`, and record the linked prior message when one exists.
4. Retrieve a bounded candidate history by owner, channel, asset group, and
   time window. A content/media hash may short-circuit only a byte-identical
   repeat; it must not decide a semantic match.
5. Have the owner-specific QWEN agent reason over the original Chinese
   text/images, the serial RAG examples, the strategy tier, and retrieved
   candidates. It must return a structured decision, confidence, linked
   message ids, intended order context, and reasons.
6. Route `ambiguous`, low-confidence, and incorrect-execution-like cases to
   review or backtesting. Never silently discard them and never let QWEN
   submit an order.
7. Persist the source sequence, candidate set, RAG profile version, model id,
   decision, and confidence before passing accepted context to the downstream
   filter and confidence layers.
8. Evaluate a labeled replay set for false merges, missed duplicates,
   continuation-link accuracy, incorrect-execution detection, and new-signal
   recall. A false merge is more dangerous than processing one repeated
   message.

The deterministic Python layer should own byte/media hashing, candidate
retrieval, idempotent persistence, schema validation, confidence tier mapping,
and the two explicit execution checks. QWEN
must own the interpretation of owner-specific, serial Chinese language and
execution examples. For an order-path change, add or update the deterministic
confidence-policy test before connecting any MCP or Lambda execution code.
