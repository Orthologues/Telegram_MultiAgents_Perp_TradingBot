# HISTORY.md

Maintenance rule: **APPEND-ONLY**. Never edit or delete past entries. Append
new sessions at the bottom, newest last.

This file summarizes the committed development history. Current state is
maintained in `STATUS.md`.

## Committed History

### 2026-06-25 — `75e43bc`: initial scaffold

Created the first Telegram-based multi-agent perpetual-futures scaffold, with
repository guidance, a BitMart MCP server, dependency files, and lock data.

### 2026-07-02 — `d1c97e5`: Figma-based application scaffold

Added the Figma-derived project structure, README and mapping documents, owner
RAG profiles, Pydantic schemas, QWEN and Ministral boundaries, orchestration,
performance weighting, exchange gateways, AWS execution placeholders, and
initial schema tests.

### 2026-07-05 — `74da2b2`: unified Python environment

Moved dependency management to the project-level environment and removed the
nested BitMart MCP environment files.

### 2026-07-13 — `daadae5`: signal deduplication scaffold

Added exact input deduplication and semantic signal-deduplication boundaries,
updated schemas, normalizers, QWEN/Ministral orchestration, tests, and the
Figma asset.

### 2026-07-13 — `793fa1d`: standardized repository guidance

Replaced the singular agent guidance with `AGENTS.md`, expanded `SKILLS.md`,
and added the project-level `uv` configuration and lock file.

### 2026-07-14 — `faf0968`: simplified repository README

Moved the trading-bot README to the repository root and removed the redundant
nested README configuration.

### 2026-07-16 — `6138bc3`: refined owner routing

Clarified owner-channel routing and the backtesting-only status of inactive
channels.

### 2026-07-17 — `24d44e7`: defined the QWEN RAG harness

Documented serial RAG message handling, owner-specific examples, confidence
calculation, and the order-analysis workflow in `AGENTS.md` and `SKILLS.md`.

### 2026-07-18 — `5dc724d`: added TP/SL inference and pair blacklisting

Added documentation for stop-loss inference, take-profit handling, and
deterministic trading-pair blacklisting.

### 2026-07-21 — `7cdd829`: migrated ingestion to AG2 TelegramAgent

Replaced the Telegram webhook concept with pull-based AG2 TelegramAgent
retrieval, durable per-channel cursors, provenance-preserving normalization,
media metadata, AWS boundaries, dependencies, documentation, and ingestion
tests.

### 2026-07-21 — `3580b10`: implemented the corrected ingestion flow

Added the ingestion pipeline, S3 and DynamoDB storage contracts, Bedrock handoff
boundary, and additional cursor and pipeline tests.

### 2026-07-21 — `9cabcef`: clarified the deployment model

Documented one shared Lightsail worker, one authorized Telegram user session,
lightweight per-chat retrieval adapters, and the distinction between channel
adapters and owner QWEN agents.

### 2026-07-22 — `c7abbbd`: added confidence policy and serial parent context

Replaced generic risk gating with confidence-based strategy selection and the
two explicit hard rejection checks, added the indexed in-memory message cache
and tree-derived chronological parent context, renamed the mapping document,
and expanded the related schemas, prompts, tests, and boundaries.

### 2026-07-22 — `ba782d6`: refined owner-specific Telegram guidance

Documented delayed TP/SL follow-ups, duplicate risk, and the narrowly scoped
minimalist Chinese acknowledgment workflow for the A-zhu private chat.

### 2026-07-22 — `b4424d6`: minimized guidance and added active priorities

Reduced `AGENTS.md` to its essential contract and added `TODO.md` with the
Telethon image hydrator and authentic serial RAG examples as the first two
priorities, followed by production adapters, restart recovery, and replay
testing.

### 2026-07-22 — `554200e`: added history and status tracking

Added this append-only commit history and the overwrite-style `STATUS.md`,
including the current scaffold state, next actions, and open gaps. The
codebase is mostly prompted GPT-5.6 Luna and Sol coding produced under time
constraints and requires careful human review before further use.

### 2026-07-22 — `510098f`: removed the redundant TODO file

Deleted `TODO.md` and kept the active priorities in `STATUS.md`, while
preserving the append-only history and current-state documentation split.

### 2026-07-23 — `27cce05`: defined shared agent skill APIs and owner QWEN synonym inference

Corrected the Trading Message Synonym Inference skill and added the explicit
`skills_api/` package. Merged the review-only synonym skill into every
`OwnerQwenAgent`, updated the scaffold documentation and file map, and kept the
boundary free of exchange calls.

### 2026-07-23 — `a02e839`: synchronized status and editor imports

Updated `HISTORY.md` and `STATUS.md` for `27cce05` and added the VS Code source
path needed for Pylance to resolve the package.

### 2026-07-24 — `1c1c768`: added position-management skills

Added multi-timeframe deterministic omitted stop-loss derivation, the owner
QWEN reduce-and-protect hypothesis, and Ministral MCP take-profit fill
protection. Added typed skill APIs, gateway boundaries, schemas, and focused
tests; the scaffold remains non-executing and requires human review.

### 2026-07-24 — `f0f609b`: clarified human-review requirements

Clarified in `AGENTS.md` that this prompted-generated scaffold requires careful
human code review and backtesting of previous Telegram trading signals before
further use.

### 2026-07-24 — `a2c9a5c`: aligned instant-order deviation thresholds

Implemented deterministic `0.5%`, `0.25%`, and `0.125%` price-deviation limits
for generic altcoins, major/TradFi perpetuals, and BTC, respectively, with
explicit mixed-channel TradFi classification and boundary tests.

### 2026-07-25 — `f2360bb`: separated ingestion receipts and live trade cursors

Removed the channel-wide ingestion cursor, retained independent message
receipts, and added concurrent parent-linked trade cursors with versioned
exchange order and position metadata for DynamoDB.

### 2026-07-28 — `eb79b05`: committed-history reconciliation

Recorded the previously omitted `ec30dc3`, `cb076bb`, `eb79b05`, `f2360bb`,
and `7200911` commits. They resolved root documentation, synchronized status,
finalized concurrent parent-linked trade cursors, and anchored omitted
stop-losses to entry prices.

### 2026-07-28 — `1d73978`: reconstructed the Figma architecture scaffold

Reconstructed the code scaffold against the current Figma architecture,
including the revised TelegramAgent, QWEN/Ministral, lifecycle, MCP, and AWS
execution boundaries.

### 2026-07-29 — `1d0ea8a`: clarified lifecycle candidates and RAG provenance

Clarified that each incoming new or continuation signal receives five QWEN
strategy candidates. Added typed serial-RAG JSON references for chronological
Telegram message IDs and URLs with private S3 archive URIs, and marked manual
code review plus authentic RAG curation as priorities.

### 2026-07-29 — `20c843f`: corrected README lifecycle wording

Clarified that five-tier QWEN candidates cover every incoming signal, with
existing perpetual-position continuations as the primary lifecycle case.

### 2026-07-30 — `c9f04a5`: replaced the exchange scaffold with Aster

Replaced the legacy exchange adapter with testnet-first Aster/Hyperliquid
contracts and added paired testnet P/L comparison for identical signals.

### 2026-07-30 — `a9abb7e`: fixed standalone MCP test imports

Made MCP server tests load their standalone modules by repository path so
`uv run pytest` passes without relying on the repository root being importable.

### 2026-07-30 — `fe3811c`: switched Aster execution to v1 REST/HMAC

Replaced the Aster v3 EIP-712 contract with v1 REST paths, API-key/HMAC secret
isolation, deterministic request signing, and focused tests.

### 2026-07-31 — pending: restored upstream-backed Aster V3 execution

Replaced local Aster V1 signing with pinned Aster V3 and Hyperliquid augmented
proxy contracts, and expanded deterministic omitted stop-loss inference to the
revised multi-indicator `1.2%`-`8%` policy.

### 2026-07-31 — `77b840e`: refactored exchange proxies and stop-loss inference

Replaced local Aster V1 signing with pinned upstream Aster V3 and Hyperliquid
proxy contracts, expanded omitted stop-loss inference, and updated the related
tests and documentation.

### 2026-08-25 — `c05f386`: planned the CrewAI-Bedrock orchestration migration

Prepared the full CrewAI replacement plan, pinned the exchange MCP upstreams,
updated trading skills and MCP status, and retained human-review gates.

### 2026-08-25 — `4e73484`: clarified CrewAI agent boundaries and Flow dispatch

Clarified owner-specific QWEN selection, shared Ministral review, and the
separation between CrewAI orchestration and deterministic services.

### 2026-08-25 — `61be966`: defined the canonical CrewAI scaffold

Specified the AWS-aligned CrewAI package layout, typed domain contracts, crews,
flows, tools, adapters, and agent interfaces.

### 2026-08-25 — `c6f6604`: corrected CrewAI domain boundaries

Refined the target placement of contracts, lifecycle state, performance logic,
policies, and adapters in the planned application layout.

### 2026-08-25 — `4206ac9`: corrected CrewAI environment and observability references

Aligned the planned environment configuration and Phoenix/Grafana observability
roles with the CrewAI application architecture.

### 2026-08-25 — `fa22db4`: clarified CrewAI interfaces and inference boundaries

Clarified typed Flow state, agent interfaces, structured outputs, and the
boundary between model inference and deterministic execution policy.

### 2026-08-27 — `d6143c0`: refined the CrewAI app migration architecture

Consolidated the migration target, implementation order, completion gate, and
human-review requirements in `AGENTS.md`.

### 2026-08-27 — `ebb33c4`: synchronized migration status and history

Recorded the CrewAI planning commits and marked the source migration as pending.

### 2026-08-27 — `48837a7`: added the preliminary CrewAI application

Added the canonical CrewAI package, owner-selected sequential Crew, typed
Telegram/lifecycle/performance Flows, explicit tool permissions, deterministic
depth and slippage gates, compatibility adapters, and offline tests.

### 2026-08-29 — `7dfa72b`: renamed the deterministic scaffold

Renamed the compatibility package to `frameworkless_app` and retained shared
VS Code settings while ignoring other workspace-specific files.

### 2026-08-29 — pending: updated scaffold status and documentation

Recorded the planned LangGraph implementation at
`draft_agentic_perp_trading_bot/src/langgraph_app/`, synchronized README paths
with the frameworkless rename, and updated the current scaffold status.

### 2026-09-08 — `15d376d`: relocated risk engine and CrewAI skill APIs

Moved deterministic execution-gate implementation into
`crewai_app/domain/policies/execution_gate.py`, retained legacy risk imports as
compatibility exports, and added the flow-only market-snapshot validation tool.
Moved canonical agent skill APIs to `crewai_app/skills_api/` and updated internal
imports; focused migration checks pass. The entry point
`draft_agentic_perp_trading_bot/src/crewai_app/main.py` has been reviewed and
the migration issues there have been addressed; the remaining code files still
require human review before use.

### 2026-09-08 — `dc7f1c6`: recorded CrewAI migration review status

Updated the CrewAI migration status and history records while keeping review
of the remaining codebase explicitly pending.

### 2026-09-08 — `d66f474`: aligned migration boundaries and provenance

Added explicit file-to-file provenance to migrated CrewAI interfaces, policies,
Flows, skills, and tools.

### 2026-09-09 — `1379b09`: migrated frameworkless modules into CrewAI

Relocated contracts, lifecycle, policies, performance, Telegram, MCP, AWS, and
orchestration modules into `crewai_app`, while preserving `frameworkless_app`
for comparison and review. Applied the same explicit file-to-file provenance
method established by `d66f474`.

### 2026-09-10 — `ae9193f`: consolidated Astra migration and skills review

Established canonical CrewAI contracts and responsibility interfaces, separated
message observation from successful delivery, preserved shared QWEN/Ministral
context, validated reviewed intents against their source, and delayed cursor
attachment until deterministic market gates passed. Aligned MCP execution with
Aster V1 REST/HMAC, added five-tier performance grouping by owner/channel/asset/
lifecycle dimensions, refreshed the architecture map, and retained
`frameworkless_app` for comparison. Focused checks pass; full CrewAI Flow
verification and human review of execution-sensitive code remain pending.

Reworked `SKILLS.md` around ownership, invariants, implementation status, and
verification. Made `skills_api` compatibility-only, added canonical QWEN
message-relation, synonym, and position-reduction interfaces, and added a
chronological typed relation contract. Updated the architecture map and active
CrewAI boundary notes; no commit ID is assigned yet.

### 2026-09-10 — pending: trimmed completed CrewAI guidance

Removed the historical Agentic Update prompts and completed CrewAI scaffold,
layout, domain-boundary, and local implementation instructions from `AGENTS.md`.
Retained only the outstanding production integration, observability, deployment,
reliability, and completion-gate requirements, and synchronized `STATUS.md`.

### 2026-09-16 — `a781805`: retired the private-chat acknowledgment workflow

Migrated A-zhu's active source from a direct chat to a conventional private
Telegram channel. Removed the obsolete Minimalist Chinese Reply guidance and
direct-chat routing while preserving A-zhu's owner-specific QWEN and replay
data. Confirmed that the reply skill had remained documentation-only: no Python
implementation or `skills_api` export existed to remove. Telegram access
remains retrieval-only with no send capability.

### 2026-09-17 — `9f193149`: added deferred QWEN labelling persistence

Replaced the immediate `needs_human_review` output flag with
`needs_human_labelling` across canonical and frameworkless QWEN contracts.
Added a typed deferred-labelling record, an application queue, a DynamoDB table
adapter, and an in-memory repository so flagged message context can be labelled
offline and curated into later RAG datasets. Updated the active documentation
to state that ingestion does not wait for human action and that queued model
outputs require validation before RAG promotion.
The newly created adapter repository file
`draft_agentic_perp_trading_bot/src/crewai_app/adapters/aws/persistence/message_labelling.py`
requires explicit awareness during subsequent human review.

### 2026-09-22 — `fc0b9b6`: made protocol inheritance explicit across `crewai_app`

Applied the explicit-inheritance rule to concrete Telegram, persistence,
cursor, Flow, QWEN, Ministral, and Aster implementations. Added shared Flow
interfaces in `flows/interfaces.py` and moved `TradeCursorResolver` into the
cursor lifecycle boundary so interface ownership is visible to reviewers.
Preserved marker classes and protocols without concrete implementations. The
refactor passed targeted Ruff, compilation, and whitespace checks.

### 2026-09-23 — `da86f1a`: organized protocol and export-only modules

Renamed pure `Protocol` declaration modules to capability-specific
`interfaces.py` paths and added package `__init__.py` re-export surfaces.
Unified the canonical domain contract exports in
`domain/contracts/__init__.py`, removed redundant export-only modules, and
preserved the public package imports and retained `frameworkless_app`
compatibility path. Updated canonical and test imports, including the retained
`frameworkless_app` Telegram compatibility import. Ruff, compilation, runtime
package-export, stale-reference, and whitespace checks pass.

### 2026-09-24 — `3168989`: added new-cycle funding-rate filtering

Added a deterministic per-venue funding-rate decision and required signed
`annualized_funding_rate_fraction` values in execution snapshots. New
`IntentType.NEW_ORDER` cycles are rejected when any target venue's absolute
annualized rate is strictly greater than
`maximum_baseline_multiplier * baseline_binance_value`; the defaults are `10`
and `0.125`, producing a `1.25` (125%) threshold. Existing-cycle intents remain
eligible. The canonical Flow persists the decisions and precise rejection
reason together with the market observation timestamp. The full suite passes
(`145 passed`), Ruff and compilation pass, and a duplicate `persist_decision`
trace append exposed by the checks was removed.

### 2026-09-24 — `3168989`: documented deferred MCP mainnet switching

Replaced the completed `CHANGELOG` instruction in the Aster MCP server with
explicit `TODO` comments for the Aster and Hyperliquid `network` defaults and
their `ASTER_NETWORK` and `HYPERLIQUID_NETWORK` fallbacks. The comments defer
switching from `ExchangeNetwork.TESTNET` to `ExchangeNetwork.MAINNET` until
testing and deployment are complete. Both MCP servers pass Ruff and
`py_compile` checks.

### 2026-09-24 — `3168989`: annotated all deferred-mainnet network defaults

Extended the deferred-mainnet `TODO` annotations from the MCP server configs to
all 34 defaulted `network` and `execution_network` declarations in canonical
and legacy contracts, exchange gateways, profile helpers, deterministic policy
parameters, and the venue-comparison test helper. Each remains
`ExchangeNetwork.TESTNET` until testing and deployment are complete.

### 2026-09-25 — `pending`: refreshed the architecture-to-code mapping

Updated `draft_agentic_perp_trading_bot/architecture_to_code_mapping.md` for the
capability-specific `interfaces.py` layout, shared `flows/interfaces.py`,
split Telegram/AWS persistence boundaries, and implemented QWEN relation and
deferred-labelling Flow wiring. Clarified that `frameworkless_app` remains a
legacy comparison implementation. Added an `AGENTS.md` rule requiring mapping
updates whenever package, module, interface, or export-only naming changes.
