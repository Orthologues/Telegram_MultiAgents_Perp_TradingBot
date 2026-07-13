# FigJam Flowchart Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, BTC/ETH day trading, alts/TradFi day trading, alts/TradFi longer trading

## Runtime Layer Mapping

- Telegram source and ingestion: `agentic_perp_trading_bot.telegram_ingestion`
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

- Telegram webhook: AWS Lambda HTTPS entrypoint
- Raw media: S3
- Message metadata: DynamoDB
- Model inference: AWS Bedrock
- Exchange live state: ECS WebSocket workers
- Signed execution: AWS Lambda using Secrets Manager
