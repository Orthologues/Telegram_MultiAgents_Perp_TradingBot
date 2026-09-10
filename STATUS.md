# Agentic Perpetual Trading Bot Status

Maintenance rule: **OVERWRITE** this file on every update. It is the current
state, not a development log. The log is `HISTORY.md`.

Last updated: 2026-09-10

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
- `agent_interfaces/` is the canonical responsibility boundary. `skills_api/`
  now remains a compatibility facade, with typed QWEN relation, synonym, and
  position-reduction capabilities defined separately.
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
- The current worktree contains an uncommitted Astra-directed migration
  refactor, including the latest skills/interface review; no commit ID is
  assigned to it yet.

## Verification

- Focused migration tests and the non-Flow suite pass: `123 passed, 4
  deselected`; Ruff, compilation, and whitespace checks also pass.
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
- Store each message ID and URL in JSON with its private S3 archive URI;
  preserve outcomes and redact unnecessary personal data.
- Add replay fixtures and metrics for all five strategy tiers.

## Further Priorities

- Replace remaining compatibility re-exports with reviewed native CrewAI
  implementations and production AWS adapters.
- Integrate the typed QWEN message-relation stage with chronological parent
  context and authenticated serial-RAG retrieval.
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
