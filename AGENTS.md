# AGENTS.md

## Scope

This repository is a human-harnessed, non-executing scaffold for a
Telegram-driven perpetual-futures bot, generated predominantly by Codex
GPT-5.6 Sol and GPT-5.6 Luna. Careful human review of the codebase and
backtesting of previous Telegram trading signals are required before further
use. Keep changes small and consistent with
the [Figma architecture flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch-Flowchart)
and [`architecture_to_code_mapping.md`](draft_agentic_perp_trading_bot/architecture_to_code_mapping.md).
Never commit credentials, Telegram sessions, tokens, signatures, or secret
files. Do not describe placeholders as live trading code.

## Architecture Contract

```text
TelegramAgent retrieval
  -> one Lightsail worker with per-chat adapters and durable cursors
  -> normalize, hydrate media, deduplicate, and build reply-tree context
  -> private S3 media + DynamoDB historical metadata
  -> one owner-specific QWEN agent per owner
  -> Ministral validation and signal deduplication
  -> weighting and confidence policy
  -> Bitget/BitMart MCP gateway and Lambda execution boundary
```

- Use one authorized Telegram user session and one shared polling worker.
- TelegramAgent is pull-based and retrieval-only in the ingestion worker; do
  not register `TelegramSendTool` or connect it directly to an exchange.
- Poll after the last committed message ID. Persist media and metadata before
  atomically advancing the channel cursor for at-least-once delivery.
- AG2 retrieval exposes a media-presence flag in this scaffold. Use an
  authenticated Telethon hydrator to download, hash, and archive images in
  private S3 before model delivery.
- Keep one in-memory reply-tree index per owner. For each message, include all
  available parent IDs and snapshots in chronological order; do not read
  DynamoDB to assemble live context.
- Pass the same ID-labelled `TelegramPromptContext` to QWEN and Ministral.
- DynamoDB is primarily a replay, backtesting, and strategy-optimization store,
  including omitted TP/SL inference outcomes and blacklist criteria.

## Agent Boundaries

- Maintain four owner-specific QWEN agents; channels and asset groups route into
  them and do not create additional agents.
- QWEN interprets serial Chinese text/images and emits hypotheses, never orders.
  RAG examples must preserve chronological messages, media, intended orders,
  and correct or incorrect outcomes.
- Ministral validates schema/evidence, deduplicates equivalent hypotheses,
  handles authenticated MCP take-profit fill protection, and deterministically
  derives omitted stop-losses from MCP liquidity and `5m`/`15m`/`1h`/`4h`
  KDJ, Bollinger-width, and ATR inputs within a one-second budget.
- Confidence selects the strategy tier. Hard rejection is limited to a
  deterministic pair blacklist or an instant-order MCP current price too far
  from the message reference price. Omitted TP/SL inference remains a
  backtestable input, not a separate hard rejection. QWEN must leave an omitted
  stop-loss unset.
- A-zhu's private-chat workflow may use a separately authorized minimalist
  Chinese acknowledgment skill; it must not infer parameters or confirm
  execution.

## Agent API Interfaces

Typed contracts live in
`draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/skills_api/`:

```text
TelegramAgentAPI.retrieve_messages(...) -> TelegramAgentRetrievalBatch
OwnerQwenAPI.infer_signal(...) -> QwenSignalHypothesis
OwnerQwenAPI.infer_synonym(...) -> TradingMessageSynonymDecision
OwnerQwenAPI.infer_position_reduction(...) -> PositionReductionHypothesis
MinistralFilterAPI.protect_entry_after_take_profit(...) -> TakeProfitProtectionDecision
MinistralFilterAPI.review(..., market_snapshot) -> FilterDecision
```

The shared synonym skill is review-only and is implemented by every
`OwnerQwenAgent` in `qwen_agents/owner_agent.py`. The minimalist Chinese reply
skill has no trading API. No agent API may call an exchange; approved execution
remains behind the MCP gateway.

## Data and Execution Rules

- Keep input deduplication, semantic QWEN deduplication, and Ministral signal
  deduplication as separate stages.
- Keep S3 archival, DynamoDB persistence, and Bedrock handoff behind
  `telegram_ingestion/storage.py` and `pipeline.py`.
- Keep exchange-specific behavior behind MCP; agents must not call exchanges.
- Preserve owner, channel, Telegram message ID, timestamps, parent IDs, media
  hashes, deduplication key, model ID, confidence, and strategy tier.
- Use conditional writes for one monotonic cursor per logical channel and do
  not advance it before durable processing completes.

## Repository Rules

- Application code: `draft_agentic_perp_trading_bot/src/`
- Tests: `draft_agentic_perp_trading_bot/tests/`
- Owner RAG profiles: versioned JSON without credentials.
- For Chinese interpretation, use serial RAG and QWEN reasoning; do not add
  keyword, substring, or regular-expression trading rules.
- Add focused tests for behavior changes and run:

```bash
cd draft_agentic_perp_trading_bot
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
git diff --check
```
