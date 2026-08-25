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

## <code>Crew.ai</code> refactoring

This is a full replacement of the current agent-orchestration scaffold with a
CrewAI application, not a parallel adapter. Follow [Build agentic systems with
CrewAI and Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/build-agentic-systems-with-crewai-and-amazon-bedrock/)
and its [reference repository](https://github.com/aws-samples/sample-agentic-frameworks-on-aws/tree/main/crewai/aws-security-auditor-crew).
CrewAI owns the agents, tasks, crews, flows, Bedrock LLM wiring (one trading
channel per agent), structured outputs (Hyperliquid/Aster-readable trading
execution JSON objects), and tracing (Phoenix for agent-level investigation;
Grafana for cross-channel strategy summaries). Keep only the external boundaries that require explicit
control: retrieval-only TelegramAgent/Telethon ingestion, canonical AWS state,
deterministic trading policies, and Aster/Hyperliquid MCP plus Lambda signing.

### Target Flow

```text
TelegramAgent/Telethon on Lightsail
  -> normalize, hydrate, archive, deduplicate, and publish to AWS Simple Queue Service (SQS)
  -> CrewAI TelegramSignalFlow
     -> load chronological parent context and active DynamoDB cursors
     -> select one owner QWEN definition
     -> sequential Crew: selected QWEN -> shared Ministral
     -> validate five strategy candidates and apply deterministic policies
     -> persist the decision and publish an approved execution intent
  -> guarded Aster/Hyperliquid MCP and Lambda boundary
  -> PositionLifecycleFlow and PerformanceEvaluationFlow
```

- Configure four owner-specific QWEN agents but instantiate only the selected
  one for each message. Each QWEN run returns all five strategy candidates, informed by available RAG examples indexed by strategy tier and position-lifecycle stage; Ministral validates them. Do not add manager agents or delegation.
- Use CrewAI `Flow` for application-level dispatch, not Telegram transport:
  select the correct owner-specific QWEN workflow, distinguish a new signal
  from a lifecycle continuation, load parent context and active cursors, and
  invoke existing deterministic Python services. Keep the deterministic logic
  outside CrewAI. Use a sequential `Crew` only for QWEN and Ministral
  reasoning.
- Pass ID-labelled parent messages, serial RAG examples, media hashes, S3
  references, and active cursor snapshots into the flow state. S3, DynamoDB,
  and ElastiCache remain canonical; CrewAI memory is not trading truth.
- QWEN agents only propose strategy candidates. The shared Ministral gatekeeping agent may  invoke deterministic policy services and review their results, but no agent may send Telegram messages, mutate cursors, sign orders, or call an exchange. Only an approved deterministic step may publish an execution intent.

### Canonical CrewAI Layout

Follow the AWS sample's generated project shape. `crew.py`, `main.py`, and the
package-level `config/agents.yaml` and `config/tasks.yaml` are the canonical
CrewAI files. Keep the top-level `crew.py` as the canonical composition facade;
put genuinely separate Crew definitions under `crews/`, not owner- or
channel-specific copies.

```text
draft_agentic_perp_trading_bot/
  pyproject.toml
  .env.aws
  src/crewai_bot/
    __init__.py
    main.py
    crew.py
    crews/
      __init__.py
      signal_evaluation_crew.py
      rag_evaluation_crew.py
    config/
      agents.yaml
      tasks.yaml
    tools/
      market_snapshot_tool.py
      serial_rag_tool.py
      confidence_policy_tool.py
      stop_loss_policy_tool.py
    flows/
      __init__.py
      telegram_signal_flow.py
      position_lifecycle_flow.py
      performance_evaluation_flow.py
    domain/
      contracts/
        schemas.py            # stable typed contract and re-export surface
        telegram.py           # message, provenance, and RAG models
        trading.py            # signals, strategies, positions, and cursors
        execution.py          # market snapshots and execution intents
        performance.py        # outcomes and venue-comparison records
      lifecycle/              # trade_cursor.py and cursor state transitions
      policies/
        confidence/           # confidence_engine/
        validation/            # ministral_filter/
    services/
      performance/            # performance_engine/
    adapters/
      telegram/               # telegram_ingestion/
      exchanges/
        mcp/                   # mcp_gateway/
      aws/
        execution/             # aws_execution/
```

### Domain Contract Boundary

- `domain/contracts/` contains persistence-agnostic Pydantic schemas, enums, and
  cross-field validators shared by CrewAI flows, tools, and deterministic
  services. `domain/contracts/schemas.py` is the stable import surface; the
  neighboring modules hold bounded type definitions rather than I/O or
  orchestration logic.
- Telegram provenance, parent-message context, serial RAG references, trading
  signals, lifecycle cursors, market snapshots, execution intents, and
  performance records belong here. AWS clients, MCP calls, prompts, agents,
  and CrewAI task logic do not.

- `crew.py` is the canonical `@CrewBase` composition facade. It defines or
  exports the primary signal-evaluation Crew, its `@agent`, `@task`, and `@crew`
  methods, and Bedrock `LLM` construction. It instantiates only the selected
  owner QWEN agent and has no manager agent or delegation.
- `crews/*_crew.py` contains only genuinely separate multi-agent Crews, such as
  signal evaluation or RAG evaluation; do not create one for each owner or
  channel. Add `rag_evaluation_crew.py` only when that evaluation needs agent
  collaboration rather than deterministic replay.
- `main.py` is the application entrypoint and exposes the standard CrewAI
  commands needed for `run`, replay, training, or evaluation. It delegates
  message execution to the Flow rather than duplicating Crew logic.
- `__init__.py` makes each directory an explicit Python package and stabilizes
  imports, packaging, and test discovery. It is recommended for this scaffold
  and the CrewAI-generated layout, although modern Python namespace packages
  can technically operate without it; `main.py` is an entrypoint, not a
  replacement for the package marker.
- `config/agents.yaml` and `config/tasks.yaml` contain role/task configuration;
  tools are typed `BaseTool` classes in `tools/*_tool.py`; stateful routing is
  implemented in `flows/*_flow.py`.
- This is a planned relocation of the non-CrewAI boundaries only; do not move
  code until the plan is approved. CrewAI `tools/` call these typed services,
  while `flows/` coordinate them. Keep the currently existing `skills_api/` as the public contract
  layer and remove it only after equivalent CrewAI adapters have parity.

### Observability

Use Phoenix for agent-level investigation and Grafana for cross-channel
strategy summaries. Phoenix should expose each flow run, parent-message chain,
RAG result and relevance score, model step, candidate set, deterministic
decision, latency, and execution intent. A representative trace is:

```text
telegram_signal_flow: owner_1:1024
├── load_parent_messages
├── retrieve_owner_rag_examples
│   ├── example owner_1:811 relevance=0.94
│   ├── example owner_1:917 relevance=0.89
│   └── example owner_1:1002 relevance=0.82
├── owner_qwen_inference
│   └── five strategy candidates
├── ministral_review
├── confidence_selection
├── deterministic_stop_loss
└── execution_intent
```

Grafana should aggregate channel, owner, asset, strategy tier, confidence,
execution, and Aster/Hyperliquid performance metrics without exposing private
Telegram content, credentials, or raw media.

### Implementation Order

1. Freeze the current tests, schemas, idempotency, parent ordering, concurrent
   cursor behavior, and deterministic decisions as the migration contract.
2. Pin CrewAI and tools, configure Bedrock model IDs, AWS region, SQS, RAG,
   observability, and IAM-based credentials. Never pass access keys to agents.
3. Add typed CrewAI state and `BaseTool` wrappers for reply-tree context, S3
   serial RAG JSON, DynamoDB cursors, market data, and decision persistence.
4. Build the Bedrock model factory, YAML-configured QWEN/Ministral Crew, and
   `TelegramSignalFlow` with structured outputs and bounded retries.
5. Add lifecycle and performance flows. A cursor closes only after its position
   and active orders are fully closed; paired Aster/Hyperliquid evaluation uses
   the intersection of positions sharing a signal key.
6. Deploy the CrewAI worker with an IAM task role. Keep Telegram sessions on
   Lightsail, secrets in AWS-managed boundaries, and live execution disabled by
   default.
7. Add parity, tool-permission, replay, RAG, Bedrock opt-in, and observability
   tests. Remove compatibility code only after all tests pass.

### Completion Gate

One normalized Telegram message must replay through a traced CrewAI Flow, route
to exactly one owner QWEN agent, produce and validate five strategies, preserve
deterministic policy and cursor behavior, and stop before execution or use the
guarded testnet boundary according to configuration. Human review of prompts,
tool permissions, IAM, RAG examples, deterministic policies, and execution code
remains mandatory.
