# Agentic Perpetual Trading Bot Status

Maintenance rule: **OVERWRITE** this file on every update. It is the current
state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-09-22

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
- `agent_interfaces/` is the canonical responsibility boundary. `skills_api/`
  now remains a compatibility facade, with typed QWEN relation, synonym, and
  position-reduction capabilities defined separately.
- A-zhu's active source is a conventional private Telegram channel. The former
  direct-chat acknowledgment workflow has been retired; neither `SKILLS.md`
  nor `skills_api/` defines a reply skill, and Telegram ingestion remains
  retrieval-only.
- Aster uses the V1 REST/HMAC boundary; Hyperliquid remains behind its approved
  upstream boundary. Both remain testnet-first, with Lambda order submission
  guarded and not production-complete.
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
  `HISTORY.md` with the last known commit ID; the latest deferred-labelling
  record is finalized as `9f193149`.
- Concrete implementations throughout `crewai_app` now explicitly inherit
  from their local `Protocol` contracts. Shared Flow interfaces live in
  `flows/interfaces.py`, and `TradeCursorResolver` is defined with the cursor
  lifecycle contract so reviewers can see each implementation boundary.

## Current Task Series

The primary current task is owner-led human review of every skill in `SKILLS.md`
that was reviewed by GPT-6 Astra-xhigh and refactored by GPT-5.6 Luna for
straightforward changes or GPT-5.6 Sol-xhigh for complex changes. Review is
complete through `## Agentic Deduplication`; the next commit will resume at
`## QWEN-Agent RAG-loading`.

## Verification

- The deferred-labelling contracts, compatibility APIs, and schema checks pass
  their focused suites (`13 passed` total), plus targeted Ruff, compilation,
  and whitespace checks.
- The explicit-protocol-inheritance refactor passes targeted Ruff,
  compilation, and whitespace checks; runtime imports still require the
  project dependencies, including `httpx`.
- The earlier private-channel routing suite passed (`17 passed`); it was not
  rerun for this labelling change.
- The previous wider migration baseline was `123 passed, 4 deselected`; it was
  not rerun for this documentation and route cleanup.
- The full suite is not certified: CrewAI 1.15.17 Flow integration can stall
  in the installed Python 3.11 runtime's executor/event shutdown path. This is
  an environment/runtime limitation, not evidence of full Flow correctness.

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
- Complete typed Aster/Hyperliquid market snapshots, observability, and guarded
  testnet acceptance before any authorized mainnet enablement.

## Document Map

| File | Purpose | Maintenance |
| --- | --- | --- |
| `STATUS.md` | Current state and priorities | Overwrite |
| `HISTORY.md` | Committed development history | Append-only |
| `AGENTS.md` | Agent and repository contract | Update at boundary changes |
| `SKILLS.md` | Repeatable implementation skills | Update at workflow changes |
