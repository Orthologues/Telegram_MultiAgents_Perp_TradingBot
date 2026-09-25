# Architecture to Code Mapping

Source board: `AgenticPerpTradingBotArch Flowchart`

## Source Layer

- Owner A: Shu-qin, mixed BTC/ETH, alts, TradFi, day and longer trading
- Owner B: Lao-tu, mixed BTC/ETH, alts, TradFi, day trading
- Owner C: Bi-jia-suo, separate BTC/ETH and alts/TradFi day-trading channels
- Owner D: A-zhu, legacy replay channels plus one active private Telegram channel

## Canonical Runtime

- CrewAI composition, Bedrock model settings, YAML configuration, and local
  entrypoint:
  `src/crewai_app/{crew.py,main.py,config/}`
- Signal evaluation Crew and application Flows:
  `src/crewai_app/crews/` and `src/crewai_app/flows/`
- Canonical agent responsibility protocols, organized by capability:
  `src/crewai_app/agent_interfaces/{qwen,ministral,telegram}/interfaces.py`
- Shared Flow dependency protocols:
  `src/crewai_app/flows/interfaces.py`
- Legacy compatibility skill contracts and package re-exports:
  `src/crewai_app/skills_api/{ministral_filter,omitted_stop_loss_inference,owner_qwen,qwen_agent_rag_loading}/`
- CrewAI BaseTool wrappers for read-only context and Flow-only services:
  `src/crewai_app/tools/`
- Stable Pydantic contracts and public package exports:
  `src/crewai_app/domain/contracts/{definitions.py,execution.py,__init__.py}`
- Confidence, funding-rate initiation filtering, omitted-stop-loss, execution
  gates, and position sizing:
  `src/crewai_app/domain/{policies,performance}/`
- Parent-linked concurrent cursors:
  `src/crewai_app/domain/lifecycle/cursor.py`

## Adapters and Boundaries

- TelegramAgent retrieval, normalization, reply trees, deduplication, and
  receipts: `src/crewai_app/adapters/telegram/`
- Local deterministic loaders used by the scaffold:
  `src/crewai_app/adapters/local_harness.py`
- AWS persistence, context-loader, decision, history, and deferred-labelling
  boundaries: `src/crewai_app/adapters/aws/persistence/`
- Telegram raw-media, metadata, receipt, and reply-tree persistence adapters:
  `src/crewai_app/adapters/telegram/`
- Deferred QWEN labelling queue and DynamoDB table adapter:
  `src/crewai_app/adapters/aws/persistence/message_labelling.py`
- Aster and Hyperliquid MCP gateway contracts:
  `src/crewai_app/adapters/exchanges/mcp/`
- Standalone augmented MCP proxies:
  `mcp_servers/{aster_mcp,hyperliquid_mcp}/`
- Aster V1 REST/HMAC and guarded Lambda execution boundary:
  `src/crewai_app/adapters/aws/execution/`
- Owner serial-RAG manifests with Telegram and S3 provenance: `rag_profiles/`

## Data and Execution Semantics

- One shared retrieval worker uses per-chat TelegramAgent configurations; it
  polls without a channel cursor and records per-message receipts.
- Media hydration, S3 archival, production SQS delivery, and production AWS
  stores are integration boundaries; the current local harness is non-live.
- Parent messages are traversed oldest first and, with cursor snapshots, are
  passed as the same immutable context to QWEN and Ministral.
- Input identity, delivered identity, and semantic trading-signal identity are
  separate. Failed publication must remain replayable.
- QWEN message-relation reasoning is a separate typed capability for duplicate,
  continuation, new-signal, or ambiguous outcomes. `TelegramSignalFlow` invokes
  the evaluator and the deferred-labelling queue when configured; this must not
  be confused with byte-level deduplication.
- Relation outputs tagged `needs_human_labelling` are persisted asynchronously
  with their prompt context for offline labelling. They enter serial RAG only
  after label and provenance validation; ingestion never waits for a label.
- Each QWEN run returns all five strategy tiers. Confidence selects the
  lifecycle policy; continuations inherit it unless an explicit reviewed update
  advances the revision.
- Deterministic funding-rate, price, depth, slippage, blacklist, and lifecycle
  checks run outside agents and before cursor mutation or execution intent
  persistence. The funding-rate check applies only to new-cycle initiation and
  rejects the cycle when any target venue's absolute annualized rate is above
  the configured Binance-baseline multiple.
- Performance evaluates all five tiers, including counterfactual tiers, by
  owner, channel, asset group, and lifecycle stage. Venue comparison uses only
  deduplicated, fully closed positions with matching signal key and tier.
- Aster V1 uses REST/HMAC signing in the AWS execution boundary; Hyperliquid
  remains behind its approved upstream boundary. Mainnet execution is guarded.

## Compatibility and Planned Work

- `src/frameworkless_app/` is retained as the legacy comparison implementation
  and compatibility path; it is not the canonical runtime or a deletion target
  in this phase.
- `src/langgraph_app/` is reserved for the later LangGraph implementation.
- SQS, Telethon image hydration, authenticated S3 serial-RAG retrieval,
  Phoenix/Grafana instrumentation, and Lambda order submission are planned or
  interface-only until separately implemented and reviewed.

The board's real-time label maps to near-real-time retrieval in this scaffold:
AG2 TelegramAgent retrieves messages since a date or message ID and does not
provide a native webhook or push listener.
