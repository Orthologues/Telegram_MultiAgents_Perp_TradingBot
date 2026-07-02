# FigJam Flowchart Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, BTC/ETH day trading, alts/TradFi day trading, alts/TradFi longer trading

## Runtime Layer Mapping

- Telegram source and ingestion: `agentic_perp_trading_bot.telegram_ingestion`
- Owner QWEN agents: `agentic_perp_trading_bot.qwen_agents`
- Ministral filter: `agentic_perp_trading_bot.ministral_filter`
- Performance and weight engine: `agentic_perp_trading_bot.performance_engine`
- Deterministic risk engine: `agentic_perp_trading_bot.risk_engine`
- Bitget/BitMart MCP gateway: `agentic_perp_trading_bot.mcp_gateway`
- AWS Secrets Manager and Lambda execution: `agentic_perp_trading_bot.aws_execution`

## Transport Split

- Telegram webhook: AWS Lambda HTTPS entrypoint
- Raw media: S3
- Message metadata: DynamoDB
- Model inference: AWS Bedrock
- Exchange live state: ECS WebSocket workers
- Signed execution: AWS Lambda using Secrets Manager
