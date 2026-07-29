# Telegram MultiAgent Perpetual Trading Bot

This repository contains a non-executing Python scaffold for converting four
owner-specific Chinese Telegram trading channels into confidence-ranked,
weighted, and backtestable perpetual-futures strategy requests.

The primary challenge is the hyper-unstructured and often vague language of
Chinese text in Telegram trading channels, including implicit entries,
exits, context, screenshots, and owner-specific terminology.

Telegram ingestion runs as one shared polling worker using one authorized user
session. Channel-specific chat IDs, per-message receipts, and provenance are
handled by lightweight retrieval adapters within that worker. The scaffold does
not require one independently deployed TelegramAgent service per channel. Each
delivered message includes oldest-to-newest `parent_messages` IDs for serial
reply-tree context retrieval. ElastiCache stores the owner reply-tree indexes,
while DynamoDB stores enriched metadata and concurrent live trade cursors,
including Hyperliquid or Bitget active orders and open positions.

Each owner QWEN agent emits five reviewable strategy-tier candidates for every
incoming trading signal, including continuations of an existing perpetual
position lifecycle.
Ministral validates them; confidence selects and persists one position-lifecycle
strategy, including recommended size and leverage, while deterministic risk
enforces pair, price, leverage, and cumulative position-value limits.

Manual serial RAG JSON profiles will preserve each example message's Telegram
ID and URL together with its private AWS S3 archive URI; authentic examples are
not yet populated.

Omitted stop-losses are derived at the Ministral boundary from typed MCP
liquidity plus KDJ, Bollinger-width, and Average True Range (ATR) inputs at
`5m`, `15m`, `1h`, and `4h`, constrained to `1.25%`-`7.5%` from entry 1 or
the average of entry 1 and entry 2. QWEN does not infer them.

## Fastest Test

From the repository root:

```bash
cd draft_agentic_perp_trading_bot && uv sync --extra aws --extra dev && uv run pytest -q
```

## Repository Map

- `draft_agentic_perp_trading_bot/`: source package, schemas, tests, RAG
  profiles, and Bitget/Hyperliquid MCP drafts.
- `AGENTS.md`: architecture contract and repository rules.
- `SKILLS.md`: concise implementation workflows.
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/skills_api/`:
  typed skill APIs for TelegramAgent, QWEN order-translation agents, and the
  Ministral validation agent.
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/qwen_agents/owner_agent.py`:
  owner QWEN API and shared review-only synonym and position-management skills.
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/trade_cursor.py`:
  parent-linked concurrent trade-cursor lifecycle and DynamoDB boundary.
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/risk_engine/`:
  deterministic execution constraints.
- `preliminary_flowchart_Figma.png`: local architecture snapshot.

The design source is the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch?node-id=402-140).
The scaffold is intentionally incomplete and must not be treated as a live
trading system.

For the current state and active priorities, see [`STATUS.md`](STATUS.md). For
the chronological development record, see [`HISTORY.md`](HISTORY.md).
