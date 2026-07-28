# FigJam Flowchart Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, three legacy channels retained for replay plus one active
  private chat/public channel route for BTC/ETH and alts

## Runtime Layer Mapping

- TelegramAgent retrieval and ingestion: `agentic_perp_trading_bot.telegram_ingestion`
- Per-channel polling and message receipts: `agentic_perp_trading_bot.telegram_ingestion.agent_worker`
- S3/DynamoDB ingestion persistence and Bedrock handoff: `agentic_perp_trading_bot.telegram_ingestion.pipeline`
- Storage contracts: `agentic_perp_trading_bot.telegram_ingestion.storage`
- ElastiCache-compatible owner reply trees: `agentic_perp_trading_bot.telegram_ingestion.reply_tree`
- Concurrent parent-linked trade cursors: `agentic_perp_trading_bot.trade_cursor`
- Telegram multimodal input deduplication: `agentic_perp_trading_bot.telegram_ingestion.deduplication`
- Agent-owned skill contracts: `agentic_perp_trading_bot.skills_api`
- Owner QWEN agents, five-tier candidates, and shared interpretation skills:
  `agentic_perp_trading_bot.qwen_agents.owner_agent`
- Ministral validation, signal deduplication, and MCP fill protection:
  `agentic_perp_trading_bot.ministral_filter`
- Deterministic omitted stop-loss policy: `agentic_perp_trading_bot.ministral_filter.stop_loss_policy`
- DynamoDB execution history and position weighting:
  `agentic_perp_trading_bot.performance_engine`
- Confidence and five-tier strategy selection:
  `agentic_perp_trading_bot.confidence_engine`
- Deterministic blacklist, price, leverage, and cumulative-notional limits:
  `agentic_perp_trading_bot.risk_engine`
- Bitget/Hyperliquid MCP gateway: `agentic_perp_trading_bot.mcp_gateway`
- AWS Secrets Manager and Lambda execution: `agentic_perp_trading_bot.aws_execution`

## Deduplication Split

- Input normalizer deduplicates mixed Chinese text, screenshots, charts, and media packages before QWEN inference.
- Ministral filter deduplicates semantically equivalent QWEN trading hypotheses before performance weighting and confidence-based strategy selection.

## Transport Split

- Telegram retrieval: one AG2 TelegramAgent configuration per target chat,
  exposed through a retrieval-only executor and hosted by a long-running
  Lightsail worker with EC2 as the scale-up path
- Delivery semantics: bounded polling without a channel cursor; archive and
  persist before a conditional per-message receipt write
- Telegram media: adjacent authenticated hydration because AG2 retrieval
  returns media presence rather than media bytes
- Raw media: S3
- Message metadata: DynamoDB
- Reply-tree context: owner-scoped ElastiCache indexes with process-local read-through caches
- Live trade state: parent-linked, versioned DynamoDB cursors containing active
  Hyperliquid/Bitget order IDs, open position IDs, and the persisted
  confidence-selected lifecycle strategy
- Execution and P/L history: append-only DynamoDB position-lifecycle events
- Normalized message handoff: Bedrock publisher after metadata persistence
- Model inference: AWS Bedrock
- Strategy candidates: all five tiers from ultra-conservative to ultra-radical
- Exchange live state: ECS WebSocket workers
- Stop-loss market inputs: MCP price, market cap, 24-hour volume, and KDJ,
  Bollinger, and ATR snapshots at 5m, 15m, 1h, and 4h
- Signed execution: AWS Lambda using Secrets Manager for Bitget credentials and
  the Hyperliquid API wallet

The board's "pushes real-time updates" label maps to near-real-time polling in
the scaffold. AG2 TelegramAgent does not expose a native push listener or
webhook; it retrieves messages since a date or message id. TelegramAgent is an
ingestion adapter only and does not push source content directly to Bedrock.
