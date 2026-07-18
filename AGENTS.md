# AGENTS.md

## Scope

This repository is a deliberately non-executing scaffold for a Telegram-driven
multi-agent perpetual-futures bot. Keep changes small, explicit, and consistent
with the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch-Flowchart).
The implementation map is
[`draft_agentic_perp_trading_bot/docs/figma_flowchart_mapping.md`](draft_agentic_perp_trading_bot/docs/figma_flowchart_mapping.md).

Do not describe placeholder code as live trading code. Never commit API keys,
Telegram tokens, MCP tokens, signatures, or local secret files.

## Architecture Contract

The flow is:

```text
Telegram webhook/bot
  -> Lambda ingestion
  -> normalize, filter, OCR-package, and deduplicate input
  -> S3 raw media + DynamoDB message metadata
  -> one QWEN3-VL agent per owner
  -> Ministral3-8B or -14B validation and trading-signal deduplication
  -> performance/weight engine
  -> deterministic risk and policy engine
  -> Bitget/BitMart gateway
  -> Lambda execution with Secrets Manager
```

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
cooldowns, conflicts, and slippage remain deterministic code.

When an order omits a stop-loss, the owner-specific QWEN stop-loss inference
skill must propose a candidate price from serial RAG examples and market
context. Before evaluating that candidate, the deterministic risk engine must
reject pairs on the temporary blacklist. An instant trading order with an
inferred stop-loss is never an automatic execution authorization.

The temporary pair blacklist is calculated deterministically from net closed
trade outcomes over a trailing 90-day window. QWEN confidence or reasoning
cannot override a blacklisted exchange/symbol pair.

Input deduplication and signal deduplication are separate:

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
Telegram sequence
  -> retrieve owner/strategy-specific RAG examples
  -> QWEN reasoning
  -> structured trade hypothesis
  -> MCP validation or simulation
  -> deterministic risk checks
  -> result, error, and evaluation record
```

The RAG examples must preserve serial Chinese message context, intended
execution orders for each strategy tier, and incorrectly executed examples.
QWEN interprets the sequence and produces the hypothesis; it never submits an
order. MCP validation or simulation checks exchange-specific behavior, while
deterministic risk code remains the final policy gate. Every accepted,
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
- Keep owner-specific RAG profiles and labeled examples JSON, versionable, and
  free of credentials. The examples must contain serial Chinese message
  sequences paired with intended execution orders for each strategy tier, plus
  annotated incorrectly executed examples.

## Commands

Run from the single-environment project root:

```bash
cd draft_agentic_perp_trading_bot
uv sync --extra aws --extra dev
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
   filter and risk layers.
8. Evaluate a labeled replay set for false merges, missed duplicates,
   continuation-link accuracy, incorrect-execution detection, and new-signal
   recall. A false merge is more dangerous than processing one repeated
   message.

The deterministic Python layer should own byte/media hashing, candidate
retrieval, idempotent persistence, schema validation, and policy gates. QWEN
must own the interpretation of owner-specific, serial Chinese language and
execution examples. For an order-path change, add or update the deterministic
policy test before connecting any MCP or Lambda execution code.
