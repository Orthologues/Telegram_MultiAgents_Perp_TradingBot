# Telegram MultiAgent Perpetual Trading Bot

This repository contains a non-executing Python scaffold for converting four
owner-specific Chinese Telegram trading channels into confidence-ranked,
weighted, and backtestable perpetual-futures strategy requests.
Preliminary orchestration now lives in
`draft_agentic_perp_trading_bot/src/crewai_app`; the original package is
retained as a deterministic compatibility layer in
`draft_agentic_perp_trading_bot/src/frameworkless_app`.

The primary challenge is the hyper-unstructured and often vague language of
Chinese text in Telegram trading channels, including implicit entries,
exits, context, screenshots, and owner-specific terminology.

Telegram ingestion runs as one shared polling worker using one authorized user
session. The initial interactive session login is performed locally by the
operator, then cleanly disconnected and encrypted before being handed off to
the Lightsail deployment; the worker never performs interactive login or
automated re-authentication. Channel-specific chat IDs, per-message receipts,
and provenance are handled by lightweight retrieval adapters within that
worker. The scaffold does not require one independently deployed TelegramAgent
service per channel. Each delivered message includes oldest-to-newest
`parent_messages` IDs for serial reply-tree context retrieval. ElastiCache
stores the owner reply-tree indexes, while DynamoDB stores enriched metadata
and concurrent live trade cursors, including Aster or Hyperliquid active orders
and open positions.

All owner inputs now arrive through Telegram channels, including A-zhu's
conventional private channel. The scaffold has no direct-chat acknowledgment
workflow and exposes no Telegram send capability.

Each owner QWEN agent emits five reviewable strategy-tier candidates for every
incoming trading signal, primarily for continuations of an existing perpetual
position lifecycle.
Ministral validates them; confidence selects and persists one position-lifecycle
strategy, including recommended size and leverage, while deterministic risk
enforces pair, price, leverage, and cumulative position-value limits.
Paired testnet P/L summaries compare only identical, fully closed signal-tier
outcomes executed on both Aster-USDT and Hyperliquid-USDC. The canonical Aster
boundary uses V1 REST/HMAC; guarded local MCP proxies remain non-executing and
delegate exchange submission to the AWS execution boundary.

Manual serial RAG JSON profiles will preserve each example message's Telegram
ID and URL together with its private AWS S3 archive URI; authentic examples are
not yet populated.

Omitted stop-losses are derived at the Ministral boundary from typed MCP
pair type, volume, EMA, MACD, KDJ, RSI, Bollinger, ATR, and volatility inputs
at `5m`, `15m`, `1h`, and `4h`, constrained to `1.2%`-`8%` from entry 1 or the
average of entry 1 and entry 2. QWEN does not infer them.

## Fastest Test

From the repository root:

```bash
cd draft_agentic_perp_trading_bot && uv sync --extra aws --extra dev --extra crewai && uv run pytest -q
```

## Repository Map

- `draft_agentic_perp_trading_bot/`: source package, schemas, tests, RAG
  profiles, and Aster/Hyperliquid MCP drafts.
- `draft_agentic_perp_trading_bot/src/crewai_app/`: CrewAI agents, sequential
  Crew, typed Flows, tools, domain boundaries, and adapters.
- `AGENTS.md`: architecture contract and repository rules.
- `SKILLS.md`: concise implementation workflows.
- `draft_agentic_perp_trading_bot/src/crewai_app/agent_interfaces/`: canonical
  typed TelegramAgent, QWEN, and Ministral responsibilities.
- `draft_agentic_perp_trading_bot/src/crewai_app/adapters/telegram/`: canonical
  retrieval, parent-tree, receipt, and metadata boundaries.
- `draft_agentic_perp_trading_bot/src/crewai_app/domain/`: canonical contracts,
  cursor lifecycle, performance, confidence, stop-loss, and execution gates.
- `draft_agentic_perp_trading_bot/src/frameworkless_app/`: retained legacy
  implementation for comparison until migration review is complete.
- `preliminary_flowchart_Figma.png`: local architecture snapshot.

The design source is the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch?node-id=402-140).
The scaffold is intentionally incomplete and must not be treated as a live
trading system.

For the current state and active priorities, see [`STATUS.md`](STATUS.md). For
the chronological development record, see [`HISTORY.md`](HISTORY.md).
