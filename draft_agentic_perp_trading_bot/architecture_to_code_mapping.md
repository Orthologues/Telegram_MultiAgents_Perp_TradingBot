# FigJam Flowchart Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, three legacy channels retained for replay plus one active
  private chat/public channel route for BTC/ETH and alts

## Runtime Layer Mapping

- CrewAI orchestration, typed Flow state, and owner-selected sequential Crew:
  `draft_agentic_perp_trading_bot/src/crewai_app/`
- Planned post-CrewAI LangGraph implementation:
  `draft_agentic_perp_trading_bot/src/langgraph_app/`
- TelegramAgent retrieval and ingestion compatibility layer:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/`
- Per-channel polling and message receipts:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/agent_worker.py`
- S3/DynamoDB ingestion persistence and Bedrock handoff:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/pipeline.py`
- Storage contracts:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/storage.py`
- ElastiCache-compatible owner reply trees:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/reply_tree.py`
- Concurrent parent-linked trade cursors:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/trade_cursor.py`
- Telegram multimodal input deduplication:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/telegram_ingestion/deduplication.py`
- CrewAI agent interfaces:
  `draft_agentic_perp_trading_bot/src/crewai_app/agent_interfaces/`
- Compatibility skill APIs:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/skills_api/`
- Owner QWEN agents and shared interpretation skills:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/qwen_agents/owner_agent.py`
- Owner serial RAG JSON profiles with Telegram/S3 provenance:
  `draft_agentic_perp_trading_bot/rag_profiles/`
- Ministral validation, signal deduplication, and MCP fill protection:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/ministral_filter/`
- Deterministic omitted stop-loss policy:
  `draft_agentic_perp_trading_bot/src/crewai_app/domain/policies/stop_loss.py`
- DynamoDB execution history and position weighting:
  `draft_agentic_perp_trading_bot/src/frameworkless_app/performance_engine/`
- Confidence and five-tier strategy selection:
  `draft_agentic_perp_trading_bot/src/crewai_app/domain/policies/confidence.py`
- Deterministic blacklist, price, leverage, and cumulative-notional limits:
  `draft_agentic_perp_trading_bot/src/crewai_app/domain/policies/execution_gate.py`
- Aster/Hyperliquid MCP gateway:
  `draft_agentic_perp_trading_bot/src/crewai_app/adapters/exchanges/mcp/`
  and `draft_agentic_perp_trading_bot/src/frameworkless_app/mcp_gateway/`
- AWS Secrets Manager and Lambda execution:
  `draft_agentic_perp_trading_bot/src/crewai_app/adapters/aws/`

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
  Aster/Hyperliquid order IDs, open position IDs, and the persisted
  confidence-selected lifecycle strategy
- Execution and P/L history: append-only DynamoDB position-lifecycle events
- Normalized message handoff: Bedrock publisher after metadata persistence
- Model inference: IAM-authenticated AWS Bedrock through CrewAI
- Strategy candidates: all five tiers from ultra-conservative to ultra-radical
- Exchange live state: ECS WebSocket workers
- Stop-loss market inputs: MCP pair type, price, volume, EMA, MACD, KDJ, RSI,
  Bollinger, ATR, and volatility snapshots at 5m, 15m, 1h, and 4h
- Venue comparison: paired testnet P/L for identical signal deduplication keys
- Signed execution: AWS Lambda using Secrets Manager API wallets and pinned
  Aster V3 EIP-712 or Hyperliquid MCP/SDK upstream interfaces

The board's "pushes real-time updates" label maps to near-real-time polling in
the scaffold. AG2 TelegramAgent does not expose a native push listener or
webhook; it retrieves messages since a date or message id. TelegramAgent is an
ingestion adapter only and does not push source content directly to Bedrock.
