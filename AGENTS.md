# AGENTS.md

## Scope

This repository is a human-harnessed, non-executing scaffold for a
Telegram-driven perpetual-futures bot, generated predominantly by Codex
GPT-5.6 Sol and GPT-5.6 Luna. Careful human review of the codebase and
backtesting of previous Telegram trading signals are required before further
use. Keep changes small and consistent with
the [Figma architecture flowchart](https://www.figma.com/board/IosVAXW713NeWhTTU962vC/AgenticPerpTradingBotArch-Flowchart?node-id=402-140)
and [`architecture_to_code_mapping.md`](draft_agentic_perp_trading_bot/architecture_to_code_mapping.md).
Never commit credentials, Telegram sessions, tokens, signatures, or secret
files. Do not describe placeholders as live trading code.

## Architecture Contract

```text
TelegramAgent retrieval
  -> one Lightsail worker with per-chat adapters and per-message receipts
  -> normalize, hydrate media, deduplicate, and build reply-tree context
  -> ElastiCache reply trees + private S3 media + DynamoDB metadata
  -> one owner-specific QWEN agent per owner, producing five strategy tiers
  -> Ministral validation and signal deduplication
  -> confidence/strategy and deterministic risk policies
  -> Aster/Hyperliquid MCP gateway and Lambda execution boundary
```

- Use one authorized Telegram user session and one shared polling worker.
- TelegramAgent is pull-based and retrieval-only in the ingestion worker; do
  not register `TelegramSendTool` or connect it directly to an exchange.
- Retrieve a bounded recent window without a channel-level cursor. Persist
  media and metadata, publish each message, and then conditionally record its
  `(channel_id, telegram_message_id)` receipt; unacknowledged messages may be
  delivered again.
- AG2 retrieval exposes a media-presence flag in this scaffold. Use an
  authenticated Telethon hydrator to download, hash, and archive images in
  private S3 before model delivery.
- Keep one ElastiCache-backed reply-tree index per owner, with a process-local
  read-through cache. Include all available parent IDs and snapshots in
  chronological order, and query DynamoDB by those IDs for active trade cursors.
- Pass the same ID-labelled `TelegramPromptContext` to QWEN and Ministral.
- Store concurrent `TradeThreadCursor` metadata in DynamoDB. Each cursor tracks
  one parent-linked symbol, exchange network, settlement asset, direction,
  active-order set, and open-position set, plus its confidence-selected
  lifecycle strategy; close it only after the position is fully closed and no
  active orders remain.
- Retain DynamoDB metadata for live coordination, replay, backtesting, and
  strategy optimization, including omitted TP/SL outcomes and blacklist data.
- Compare Aster-USDT and Hyperliquid-USDC testnet P/L only across the intersection
  of closed positions sharing the same signal deduplication key.

## Agent Boundaries

- Maintain four owner-specific QWEN agents; channels and asset groups route into
  them and do not create additional agents.
- QWEN interprets serial Chinese text/images and emits one candidate for each
  tier from ultra-conservative to ultra-radical, never orders.
  RAG examples must preserve chronological messages, media, intended orders,
  and correct or incorrect outcomes. Each manually curated JSON example must
  include every Telegram message ID and URL in order, plus the private S3 URI
  containing the archived example.
- Ministral validates schema/evidence, deduplicates equivalent hypotheses,
  handles authenticated MCP take-profit fill protection, and deterministically
  derives omitted stop-losses from pair type, volume, and `5m`/`15m`/`1h`/`4h`
  EMA, MACD, KDJ, RSI, Bollinger, ATR, and volatility inputs within one second.
- Confidence selects one of the five initial lifecycle strategies, including
  its recommended size and leverage. Parent-linked updates inherit that policy;
  only an explicit `strategy_tier_hint` whose target candidate passes Ministral
  review may increment its revision. Deterministic risk separately enforces
  pair blacklisting, instant-order price deviation, leverage, and cumulative
  owner/pair position-value limits. QWEN must leave an omitted stop-loss unset.
- A-zhu's private-chat workflow may use a separately authorized minimalist
  Chinese acknowledgment skill; it must not infer parameters or confirm
  execution.

## Agent API Interfaces

Typed contracts live in
`draft_agentic_perp_trading_bot/src/agentic_perp_trading_bot/skills_api/`:

```text
TelegramAgentAPI.retrieve_messages(...) -> TelegramAgentRetrievalBatch
QwenAgentRagLoadingAPI.load_rag_profile(...) -> OwnerRagProfile
OwnerQwenAPI.infer_strategy_candidates(...) -> QwenStrategyCandidateSet
OwnerQwenAPI.infer_signal(...) -> QwenSignalHypothesis
OwnerQwenAPI.infer_synonym(...) -> TradingMessageSynonymDecision
OwnerQwenAPI.infer_position_reduction(...) -> PositionReductionHypothesis
MinistralFilterAPI.protect_entry_after_take_profit(...) -> TakeProfitProtectionDecision
MinistralFilterAPI.record_execution_event(...) -> None
OmittedStopLossInferenceAPI.infer_omitted_stop_loss(...) -> OmittedStopLossDecision
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
- Keep live parent-linked cursor lifecycle logic in `trade_cursor.py`; use
  conditional DynamoDB version writes so independent cursors can progress
  concurrently.
- Keep exchange-specific behavior behind MCP; agents must not call exchanges.
- Default both venues to testnet. Keep both API wallets inside Secrets Manager
  and Lambda; delegate signing to the pinned Aster and Hyperliquid upstreams.
- Preserve owner, channel, Telegram message ID, timestamps, parent IDs, media
  hashes, deduplication key, model ID, confidence, and strategy tier.

## Repository Rules

- Application code: `draft_agentic_perp_trading_bot/src/`
- Tests: `draft_agentic_perp_trading_bot/tests/`
- Owner RAG profiles: versioned JSON without credentials. Populate them
  manually with authentic serial examples and their Telegram/S3 provenance.
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

## Prompts for the most recent Agentic Update

Due to the depreciation of the legacy `HMAC-SHA256`-based Aster V1-API (`https://www.asterdex.com/en/api-management`) and the introduction of Aster V3-Pro-API (`https://www.asterdex.com/en/api-wallet`), the codebase needs to be revamped substantially. The necessary major updates:

- Refactor the target API of the Aster MCP under this repository from `V1-API` to `V3-API`, i.e., switching from `HMAC-SHA256` to `EIP-712` authentication.
- Use the baseline official Aster MCP at `https://github.com/asterdex/aster-mcp` to restructure the Aster MCP at this repository as an interface-style augmented proxy MCP. Use the available `EIP-712`-authentication modules here, do not reinvent the wheels.
- Use the baseline non-official Hyperliquid MCP at `https://github.com/Dakkshin/hyperliquid-mcp` to restructure the Aster MCP at this repository as an interface-style augmented proxy MCP. Avoid reinventing the wheels as well.
- update the range of derived distance from entry 1, or from the average of entry 1 and entry 2 from `1.25%`-`7.5%` to `1.2%`-`8%` for the skill `Omitted Stop-Loss Inference` at `./SKILLS.md`. You should draft a deterministic recipe combining `5m, 15m, 1h, 4h` level EMA, MACD, KDJ, RSI and Bollinger Band, as well as the type (tradfi, mainstream coins, altcoins), trading volume and volatality of trading-pair to determine the inferred stop-loss deviation. I will inspect the draft calculation recipe myself and adjust it.

Caveats:

- I changed the title names of a few skills at `SKILLS.md`. Please DO NOT CHANGE my staged updates there. Rename the skills under `skills_api` accordingly instead, and refactor its comments wherever necessary as well.
- Do not change the paragraphs under the subtitle `prompts for the most recent Agentic Update` under this file unless there is a basic grammatic error.
- Introduce only minimalist and necessary changes to the `.md` files across the repository.
