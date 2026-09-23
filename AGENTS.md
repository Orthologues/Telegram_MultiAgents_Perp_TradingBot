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

- Use one authorized Telegram user session and one shared polling worker. The
  operator must perform the initial interactive Telegram login locally, verify
  the expected account and allowlisted chats, disconnect cleanly, and migrate
  the encrypted session to the Lightsail deployment through the approved
  Secrets Manager/KMS boundary. The worker must load only this
  pre-provisioned session; it must never perform interactive login, automated
  re-authentication, proxy or IP rotation, or aggressive retry loops. This is
  an operational safety measure, not a guarantee against Telegram account
  restrictions; stop and alert on FloodWait or authentication failures.
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
- Persist QWEN outputs tagged `needs_human_labelling=true`, together with their
  ID-labelled prompt context, in a dedicated DynamoDB labelling table. This is
  an asynchronous RAG dataset workflow and must not pause message ingestion.
  Promote a record into serial RAG only after its label and provenance have
  been validated.
- Compare Aster-USDT and Hyperliquid-USDC testnet P/L only across the intersection
  of closed positions sharing the same signal deduplication key.

## Package Boundaries

`draft_agentic_perp_trading_bot/src/crewai_app/` is the intended canonical
application. Retain
`draft_agentic_perp_trading_bot/src/frameworkless_app/` as a legacy comparison
implementation during the migration; it is not a second production runtime.
Pure interface-only modules that define parent `Protocol` classes with method
declarations and no implementation must be named `interfaces.py`.
Modules that only re-export classes, methods, interfaces, or modules and have
no implementation must be merged into the owning package's `__init__.py`; do
not retain a standalone export-only module.
Canonical agent responsibility protocols live in
`draft_agentic_perp_trading_bot/src/crewai_app/agent_interfaces/`. Retain
`draft_agentic_perp_trading_bot/src/crewai_app/skills_api/` only for
compatibility with the legacy comparison path; new Flow responsibilities use
`agent_interfaces` and the canonical domain boundaries. Deterministic policies
live under `draft_agentic_perp_trading_bot/src/crewai_app/domain/policies/`,
with Flow-only wrappers under
`draft_agentic_perp_trading_bot/src/crewai_app/tools/`. The later LangGraph
implementation at `draft_agentic_perp_trading_bot/src/langgraph_app/` is a
roadmap item, not a current runtime. Keep the architecture mapping as the
source of truth when responsibilities move.

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

## Agent API Interfaces

Canonical agent contracts live in
`draft_agentic_perp_trading_bot/src/crewai_app/agent_interfaces/`:

```text
TelegramAgentAPI.retrieve_messages(...) -> TelegramAgentRetrievalBatch
SerialRagLoaderAPI.load(...) -> list[SerialRagExample]
QwenCandidateInferenceAPI.infer_strategy_candidates(...) -> QwenStrategyCandidateSet
QwenMessageRelationAPI.classify_message_relation(...) -> TradingMessageRelationDecision
QwenSynonymInferenceAPI.infer_synonym(...) -> TradingMessageSynonymDecision
QwenPositionReductionAPI.infer_position_reduction(...) -> PositionReductionHypothesis
SignalEvaluationAPI.evaluate(...) -> SignalEvaluationResult
MinistralReviewAPI.review(..., market_snapshot) -> FilterDecision
LegacySignalInferenceAPI.infer_signal(...) -> QwenSignalHypothesis
```

The compatibility skill contracts remain in
`draft_agentic_perp_trading_bot/src/crewai_app/skills_api/` for the retained
legacy comparison path; the canonical Flow imports `agent_interfaces` instead.
The shared synonym and message-relation skills are review-only capabilities of
the selected owner QWEN workflow. Omitted-stop-loss and TP protection are
deterministic policy/lifecycle responsibilities, not agent APIs. No agent API
may call an exchange; approved execution remains behind the MCP gateway.

## Data and Execution Rules

- Keep input deduplication, semantic QWEN deduplication, and Ministral signal
  deduplication as separate stages.
- Keep S3 archival, DynamoDB persistence, and the downstream Bedrock handoff
  behind `crewai_app/adapters/telegram/` and its Flow boundary.
- Keep live parent-linked cursor lifecycle logic in
  `crewai_app/domain/lifecycle/cursor.py`; use conditional DynamoDB version
  writes so independent cursors can progress concurrently.
- Keep deferred QWEN labelling persistence in
  `crewai_app/adapters/aws/persistence/message_labelling.py`. The Flow queues a
  flagged result after schema validation and does not wait for a person to
  label it.
- Keep exchange-specific behavior behind MCP; agents must not call exchanges.
- Default both venues to testnet. Keep both API credentials inside Secrets
  Manager and Lambda; use the canonical Aster V1 REST/HMAC and Hyperliquid
  upstream boundaries for signing and submission.
- Preserve owner, channel, Telegram message ID, timestamps, parent IDs, media
  hashes, deduplication key, model ID, confidence, and strategy tier.

## Repository Rules

- Application code: `draft_agentic_perp_trading_bot/src/`
- Tests: `draft_agentic_perp_trading_bot/tests/`
- Owner RAG profiles: versioned JSON without credentials. Populate them
  manually with authentic serial examples and their Telegram/S3 provenance.
- In every source-file comment block and all Markdown prose, strictly enclose
  every variable or field name in backticks, for example `signal_dedup_key`.
  Apply this rule to `COMMENTLOG` and `CHANGELOG` entries as well; preserve
  the native quoting required by JSON, YAML, and other code examples.
- After each commit, replace the `pending` marker in every `HISTORY.md` entry
  covered by that commit with the last known commit ID. Never leave a completed
  entry marked `pending`.
- When concrete classes fulfill a local `Protocol` contract, explicitly inherit
  from that `Protocol` in the class declaration even though structural typing
  would otherwise suffice. This makes the contract visible to reviewers;
  `Protocol` classes are interface contracts, not wrapper implementations.
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

## <code>Crew.ai</code> refactoring

The initial CrewAI composition, typed contracts, application Flows, deterministic
policy boundaries, and local contract tests are implemented. The remaining
work is production integration and operational validation. CrewAI must continue
to own only agent/task/Crew/Flow orchestration; Telegram transport, canonical
AWS state, deterministic policy, and exchange execution remain outside agents.

### Remaining integration work

- Complete the production Telegram-to-SQS boundary, authenticated media
  hydration and private S3 archival, durable DynamoDB/ElastiCache adapters, and
  bounded semantic message-relation/RAG retrieval with lifecycle filtering and
  image delivery.
- Provision the deferred-labelling DynamoDB table and inject its durable
  repository into the already-wired relation stage. Add the offline curation
  path that validates completed labels before promotion into owner RAG
  profiles.
- Ensure the production Flow passes identical ID-labelled source context and
  provenance to QWEN and Ministral, and that decision persistence and execution
  intents are durable and idempotent.
- Complete the guarded Aster/Hyperliquid MCP-to-Lambda submission path,
  including ambiguous-order reconciliation and measured execution safeguards.

### Observability

Use [Arize Phoenix](https://docs.crewai.com/v1.15.17/en/observability/arize-phoenix)
for agent-level investigation and Grafana for cross-channel strategy summaries.
Phoenix should expose each Flow run, parent-message chain, RAG result and
relevance score, LLM inference, structured-output validation, candidate set,
Ministral review, deterministic decision, latency, and execution intent. A
representative trace is:

```text
telegram_signal_flow: owner_1:1037
├── load_parent_messages
├── retrieve_owner_rag_examples
│   ├── example owner_1:811 relevance=0.94
│   ├── example owner_1:917 relevance=0.89
│   └── example owner_1:1002 relevance=0.82
├── owner_qwen_inference
│   └── five strategy candidates
├── validate_structured_output
├── ministral_review
├── confidence_selection
├── load_market_snapshot
├── apply_deterministic_policies
├── persist_decision
└── execution_intent
```

Grafana should aggregate channel, owner, asset, strategy tier, confidence,
execution, and Aster/Hyperliquid performance metrics without exposing private
Telegram content, credentials, or raw media.

### Remaining Implementation Work

1. Complete the production AWS integrations and bounded RAG/relation workflow
   described above. Never pass access keys to agents.
# COMMENTLOG: The order-retry requirement was unclear; rewrite it to explain
# how to handle a timeout or lost response without creating duplicate orders.
2. Add bounded retry handling only for transient Bedrock failures and
   structured-output repair. If an exchange-order request times out or loses its
   response, query the exchange with the same stable client order ID before
   retrying. If the order already exists, treat the original request as
   submitted and do not place a duplicate. Only retry after confirming that no
   order exists, and apply the same idempotency safeguard to the related
   persistence update.
3. Deploy the CrewAI worker with a least-privilege IAM task role. Keep Telegram
   sessions on Lightsail and credentials within AWS Secrets Manager and
   KMS-protected boundaries. Keep mainnet execution disabled throughout the
   guarded testnet phase. After all testnet criteria pass and execution-sensitive
   code receives human review, an authorized operator may explicitly enable
   mainnet execution.
4. Complete smoke, contract, and integration coverage for production adapters,
   observability, replay fixtures, and execution idempotency. Remove compatibility
   code only after these checks pass and execution-sensitive changes receive
   human review.

### Completion Gate

The production path is complete only when a normalized Telegram message
traverses the real ingestion and AWS boundaries through a traced CrewAI Flow,
with telemetry proving the selected owner QWEN, five-candidate review, and
deterministic execution-gate sequence. Before any execution intent is emitted,
those services must preserve cursor invariants and reject an instant order when
the MCP market snapshot indicates excessive deviation from the source message's
reference price, insufficient order-book depth, or excessive expected slippage.

During validation, the Flow may submit orders only through the guarded testnet
boundary when testnet mode is explicitly enabled and all pre-execution checks
pass. Mainnet execution remains disabled until the testnet phase is complete,
all testnet acceptance criteria are satisfied, execution-sensitive changes
receive human review, and an authorized operator explicitly enables mainnet
mode. Human review of prompts, tool permissions, IAM, RAG examples,
deterministic policies, and execution code remains mandatory.
