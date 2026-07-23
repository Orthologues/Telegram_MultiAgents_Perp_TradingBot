# Telegram MultiAgent Perpetual Trading Bot

This repository contains a non-executing Python scaffold for converting four
owner-specific Chinese Telegram trading channels into confidence-ranked,
weighted, and backtestable perpetual-futures strategy requests.

The primary challenge is the hyper-unstructured and often vague language of
Chinese text in Telegram trading channels, including implicit entries,
exits, context, screenshots, and owner-specific terminology.

Telegram ingestion runs as one shared polling worker using one authorized user
session. Channel-specific chat IDs, cursors, and provenance are handled by
lightweight retrieval adapters within that worker; the scaffold does not
require one independently deployed TelegramAgent service per channel. Each
delivered message includes oldest-to-newest `parent_messages` IDs for serial
reply-tree context retrieval. The reply-tree index is maintained in memory per
owner QWEN agent; DynamoDB receives enriched metadata but is not read for this
context.

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
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/skills_api/`:
  typed skill APIs for TelegramAgent, QWEN, Ministral, and synonym inference.
- `draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/qwen_agents/owner_agent.py`:
  owner QWEN API and shared review-only trading-message synonym skill.
- `preliminary_flowchart_Figma.png`: local architecture snapshot.

The design source is the [AgenticPerpTradingBotArch flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch).
The scaffold is intentionally incomplete and must not be treated as a live
trading system.

For the current state and active priorities, see [`STATUS.md`](STATUS.md). For
the chronological development record, see [`HISTORY.md`](HISTORY.md).
