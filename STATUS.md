# Agentic Perpetual Trading Bot Status

Maintenance rule: **OVERWRITE** this file on every update. It is the current
state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-09-24

## Phase

P2 — CrewAI migration scaffold. Priority implementation remains `0/2`:
Telethon image hydration and authentic serial RAG examples.

## Current State

- `crewai_app` is the canonical CrewAI scaffold. `frameworkless_app` remains
  available for independent comparison; it has not been deleted.
- Canonical Pydantic contracts, agent responsibility protocols, Telegram
  adapters, parent-linked cursors, deterministic policies, performance logic,
  MCP boundaries, and AWS execution boundaries are under `crewai_app`.
- The migration now has explicit model compatibility boundaries, separate
  observed/delivered message identity, retryable publication, shared immutable
  QWEN/Ministral context, candidate/review/source validation, and pre-gate
  cursor attachment.
- QWEN relation, synonym, and position-reduction outputs now use the deferred
  `needs_human_labelling` flag. A typed queue, DynamoDB table adapter, and local
  repository preserve flagged prompt context for later RAG curation without
  blocking ingestion. The canonical Flow now runs relation classification and
  invokes the queue; production table provisioning and durable DynamoDB
  injection remain.
- `agent_interfaces/` is the canonical responsibility boundary. Pure protocol
  declarations now live in capability-specific `interfaces.py` modules, with
  package `__init__.py` files preserving the public import surface.
- `skills_api/` now remains a compatibility facade, with typed QWEN relation,
  synonym, and position-reduction capabilities defined separately. Its pure
  protocol declarations follow the same `interfaces.py` and `__init__.py`
  package layout.
- Export-only canonical contract modules were consolidated into
  `domain/contracts/__init__.py`. Redundant `schemas.py`, `performance.py`,
  `telegram.py`, `trading.py`, and `skills_api/telegram_agent.py` modules were
  removed while the package-level exports and the retained
  `frameworkless_app` compatibility import were preserved.
- A-zhu's active source is a conventional private Telegram channel. The former
  direct-chat acknowledgment workflow has been retired; neither `SKILLS.md`
  nor `skills_api/` defines a reply skill, and Telegram ingestion remains
  retrieval-only.
- Aster uses the V1 REST/HMAC boundary; Hyperliquid remains behind its approved
  upstream boundary. Both remain testnet-first, with Lambda order submission
  guarded and not production-complete.
- Aster and Hyperliquid MCP configuration defaults, canonical and legacy schema
  fields, adapter defaults, policy method parameters, and the test helper remain
  `ExchangeNetwork.TESTNET`. All 34 default declarations now carry a nearby
  `TODO` marker to switch to `ExchangeNetwork.MAINNET` only after testing and
  deployment are complete.
- New-cycle initiation now has a deterministic per-venue funding-rate filter.
  The default `baseline_binance_value` is `0.125` and the strict maximum is
  `10` times that baseline, or `1.25` (125% annualized). Rates at the boundary
  pass; either sign above it rejects the entire new cycle. Existing-cycle
  intents bypass this filter. This policy and its integration are committed as
  `3168989`. Production MCP snapshots must still supply the signed live rate.
- Each owner QWEN run produces five strategy candidates. Confidence selects the
  lifecycle tier; continuations inherit it unless a reviewed update advances
  the revision. All five tiers remain available for performance evaluation,
  grouped by owner, channel, asset group, and lifecycle stage.
- The local harness is non-live. SQS delivery, Telethon image hydration,
  production S3/DynamoDB/ElastiCache adapters, Phoenix/Grafana instrumentation,
  and Lambda order submission remain planned or only partially wired.
- Manual human review of the remaining codebase, prompts, tool permissions,
  IAM, deterministic policies, execution paths, and authentic serial RAG data
  remains mandatory. `main.py` received a prior focused review.
- `AGENTS.md` now retains only the outstanding CrewAI production-integration,
  observability, deployment, reliability, and acceptance-gate requirements;
  historical prompts and completed scaffold guidance were removed.
- `AGENTS.md` now requires each commit to replace covered `pending` markers in
  `HISTORY.md` with the last known commit ID. The deferred-labelling record is
  finalized as `9f193149`, and the funding-rate plus deferred-mainnet records
  are finalized as `3168989`.
- The empty untracked `draft_agentic_perp_trading_bot/tests/fixtures/`
  directory was removed; replay fixture files remain a future action and no
  fixture data was deleted.
- Concrete implementations throughout `crewai_app` now explicitly inherit
  from their local `Protocol` contracts. Shared Flow interfaces live in
  `flows/interfaces.py`, and `TradeCursorResolver` is defined with the cursor
  lifecycle contract so reviewers can see each implementation boundary.
- The protocol-module and export-only-module restructuring is committed as
  `da86f1a` and passed Ruff, source compilation, runtime package-export checks,
  stale-reference checks, and whitespace checks.

## Current Task Series

The primary current task is owner-led human review of every skill in `SKILLS.md`
that was reviewed by GPT-6 Astra-xhigh and refactored by GPT-5.6 Luna for
straightforward changes or GPT-5.6 Sol-xhigh for complex changes. Review is
complete through `## Agentic Deduplication`; the next commit will resume at
`## QWEN-Agent RAG-loading`.

## Verification

- The complete deterministic and Flow suite passes (`145 passed`), with `15`
  third-party deprecation warnings and no test failures.
- The funding-rate policy and CrewAI application files pass their focused
  policy, boundary, rejection, persistence, and successful-execution checks
  (`27 passed`).
- Project-wide Ruff checks and compilation of `src/` and `tests/` pass.
- The Aster and Hyperliquid MCP server Ruff and `py_compile` checks pass after
  the deferred-mainnet TODO annotations.
- The complete default-network annotation sweep passes Ruff, compilation, and
  whitespace validation.
- The full-suite result validates the local scaffold only; production MCP
  funding data, AWS integrations, and guarded testnet acceptance remain
  incomplete.

## Next Actions

### 1. Telethon Image Hydrator

- Retrieve current and chronological parent media through the authorized
  session; validate, hash, archive to private S3, and preserve provenance.
- Pass image bytes/references and IDs to QWEN before recording delivery.
- Add network-free tests for success, failure, size limits, duplicate hashes,
  and parent-image prompts.

### 2. Authentic Serial RAG Examples

- Add human-reviewed owner/channel text and image sequences, including
  multi-level replies and omitted TP/SL updates.
- Label queued QWEN records offline, validate their provenance and final labels,
  and promote only curated records into owner RAG profiles.
- Store each message ID and URL in JSON with its private S3 archive URI;
  preserve outcomes and redact unnecessary personal data.
- Add replay fixtures and metrics for all five strategy tiers.

### 3. Funding-Rate Threshold Backtesting

- TODO: Use backtesting to compare the average ROI produced by different
  `DEFAULT_MAXIMUM_BASELINE_MULTIPLIER` values at `draft_agentic_perp_trading_bot/src/crewai_app/domain/policies/funding_rate.py` and select the best-performing
  default.

## Further Priorities

- Replace remaining compatibility re-exports with reviewed native CrewAI
  implementations and production AWS adapters.
- Complete production typed QWEN relation retrieval with chronological parent
  context, authenticated serial-RAG retrieval, table provisioning, and durable
  repository injection.
- Implement `draft_agentic_perp_trading_bot/src/langgraph_app/` after the fast
  CrewAI implementation.
- Rebuild owner reply-tree indexes after worker restarts and add production
  cursor/receipt repositories.
- Complete typed Aster/Hyperliquid market snapshots, including live signed
  annualized funding rates, observability, and guarded testnet acceptance
  before any authorized mainnet enablement.

## Document Map

| File | Purpose | Maintenance |
| --- | --- | --- |
| `STATUS.md` | Current state and priorities | Overwrite |
| `HISTORY.md` | Committed development history | Append-only |
| `AGENTS.md` | Agent and repository contract | Update at boundary changes |
| `SKILLS.md` | Repeatable implementation skills | Update at workflow changes |
