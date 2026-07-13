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

| Owner | Routing examples |
| --- | --- |
| A, Shu-qin | Mixed BTC/ETH, alts, and TradFi; day or longer strategy |
| B, Lao-tu | Mixed BTC/ETH, alts, and TradFi; day strategy |
| C, Bi-jia-suo | BTC/ETH channel plus alts/TradFi channel |
| D, A-zhu | BTC/ETH channel plus day and longer alts/TradFi channels |

Each QWEN agent uses manually maintained serial JSON RAG profiles and emits
preliminary JSON hypotheses in the conservative, intermediate, and radical
strategy tiers. QWEN output is never an execution command.

The Ministral 8B and 14B variants must implement the same interface so they can
be A/B-tested. The filter validates schema, rejects prompt-injected or
ambiguous content, deduplicates equivalent hypotheses, and emits a normalized
`CanonicalTradeIntent` only when approved. Position sizing, leverage, symbols,
cooldowns, conflicts, and slippage remain deterministic code.

Input deduplication and signal deduplication are separate:

- `telegram_ingestion/deduplication.py` prevents repeated multimodal Telegram
  inputs from reaching QWEN.
- `ministral_filter/signal_deduplication.py` prevents equivalent QWEN signals
  from being weighted or executed twice.

ECS may provide low-latency Bitget/BitMart WebSocket market data. Order
execution uses HTTPS REST with exchange signing and slippage checks. AWS
Lambda retrieves credentials from Secrets Manager at the execution boundary.

## Repository Rules

- Put application code under `draft_agentic_perp_trading_bot/src/`.
- Put tests under `draft_agentic_perp_trading_bot/tests/`.
- Keep exchange-specific behavior behind `mcp_gateway/`; do not call an
  exchange directly from an LLM agent.
- Extend Pydantic schemas before wiring a new stage. Preserve trace fields such
  as owner, channel, strategy tier, deduplication key, and model id.
- Persist production deduplication state in a shared store such as DynamoDB;
  the current in-memory classes are test scaffolds only.
- Keep RAG examples and profiles JSON, versionable, and free of credentials.

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

## Change Example

For a new Telegram deduplication field:

1. Add the field to `schemas.py`.
2. Populate it in `telegram_ingestion/normalizer.py`.
3. Apply it in `telegram_ingestion/deduplication.py`.
4. Add a focused test in `tests/` for first-seen and repeated input.
5. Run the commands above and update the Figma mapping only if the boundary
   changed.

For an order-path change, add or update the deterministic policy test before
connecting any MCP or Lambda execution code.
