# Telegram MultiAgent Perpetual Trading Bot

This repository contains a non-executing Python scaffold for converting four
owner-specific Chinese Telegram trading channels into validated, weighted, and
risk-checked perpetual-futures execution requests.

The primary challenge is the hyper-unstructured and often vague language of
Chinese text in Telegram trading channels, including implicit entries,
exits, context, screenshots, and owner-specific terminology.

Telegram ingestion runs as one shared polling worker using one authorized user
session. Channel-specific chat IDs, cursors, and provenance are handled by
lightweight retrieval adapters within that worker; the scaffold does not
require one independently deployed TelegramAgent service per channel.

## Fastest Test

From the repository root:

```bash
cd draft_agentic_perp_trading_bot && uv sync --extra aws --extra dev && uv run pytest -q
```

## Repository Map

- `draft_agentic_perp_trading_bot/`: source package, schemas, tests, RAG
  profiles, and Bitget/BitMart MCP drafts.
- `AGENTS.md`: architecture contract and repository rules.
- `SKILLS.md`: concise implementation workflows.
- `preliminary_flowchart_Figma.png`: local architecture snapshot.

The design source is the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch).
The scaffold is intentionally incomplete and must not be treated as a live
trading system.
