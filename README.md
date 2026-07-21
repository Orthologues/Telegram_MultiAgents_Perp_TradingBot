# Telegram MultiAgent Perpetual Trading Bot

This repository contains a non-executing Python scaffold for retrieving four
owners' Chinese Telegram trading channels through AG2 TelegramAgent, then
converting the messages into validated, weighted, and risk-checked
perpetual-futures execution requests.

The primary challenge is the hyper-unstructured and often vague language of
Chinese text in Telegram trading channels, including implicit entries,
exits, context, screenshots, and owner-specific terminology.

## Telegram Ingestion

The previous Telegram bot webhook and Lambda ingestion entrypoint have been
removed from the architecture. A long-running Lightsail worker, with EC2 as the
scale-up path, polls one AG2 TelegramAgent per configured channel through a
retrieval-only executor using an authorized Telegram user account. This avoids
requiring a bot to be approved as a channel administrator.

TelegramAgent retrieval is pull-based rather than native push. The worker reads
messages after a durable per-channel message-id cursor, normalizes them, archives
available media in S3, stores metadata in DynamoDB, and advances the cursor only
after those writes succeed. AG2 returns a media-presence flag but not media
bytes, so media download remains an explicit adjacent adapter using the same
authorized Telegram session.

## Fastest Test

From the repository root:

```bash
cd draft_agentic_perp_trading_bot && uv sync --extra aws --extra telegram --extra dev && uv run pytest -q
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
