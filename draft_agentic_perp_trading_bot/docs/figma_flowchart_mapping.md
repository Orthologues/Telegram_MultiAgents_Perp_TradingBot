# FigJam Flowchart Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, BTC/ETH day trading, alts/TradFi day trading, alts/TradFi longer trading

## Runtime Layer Mapping

- TelegramAgent retrieval and ingestion: `agentic_perp_trading_bot.telegram_ingestion`
- Per-channel polling and cursor commit: `agentic_perp_trading_bot.telegram_ingestion.agent_worker`
- S3/DynamoDB ingestion persistence and Bedrock handoff: `agentic_perp_trading_bot.telegram_ingestion.pipeline`
- Storage contracts: `agentic_perp_trading_bot.telegram_ingestion.storage`
- Telegram multimodal input deduplication: `agentic_perp_trading_bot.telegram_ingestion.deduplication`
- Owner QWEN agents: `agentic_perp_trading_bot.qwen_agents`
- Ministral filter and trading-signal deduplication: `agentic_perp_trading_bot.ministral_filter`
- Performance and weight engine: `agentic_perp_trading_bot.performance_engine`
- Deterministic risk engine: `agentic_perp_trading_bot.risk_engine`
- Bitget/BitMart MCP gateway: `agentic_perp_trading_bot.mcp_gateway`
- AWS Secrets Manager and Lambda execution: `agentic_perp_trading_bot.aws_execution`

## Deduplication Split

- Input normalizer deduplicates mixed Chinese text, screenshots, charts, and media packages before QWEN inference.
- Ministral filter deduplicates semantically equivalent QWEN trading hypotheses before performance weighting, risk checks, and exchange execution.

## Transport Split

- Telegram retrieval: one AG2 TelegramAgent configuration per target chat,
  exposed through a retrieval-only executor and hosted by a long-running
  Lightsail worker with EC2 as the scale-up path
- Delivery semantics: bounded polling after a DynamoDB message-id cursor;
  archive and persist before a conditional cursor advance
- Telegram media: adjacent authenticated hydration because AG2 retrieval
  returns media presence rather than media bytes
- Raw media: S3
- Message metadata: DynamoDB
- Normalized message handoff: Bedrock publisher after metadata persistence
- Model inference: AWS Bedrock
- Exchange live state: ECS WebSocket workers
- Signed execution: AWS Lambda using Secrets Manager

The board's "pushes real-time updates" label maps to near-real-time polling in
the scaffold. AG2 TelegramAgent does not expose a native push listener or
webhook; it retrieves messages since a date or message id. TelegramAgent is an
ingestion adapter only and does not push source content directly to Bedrock.
