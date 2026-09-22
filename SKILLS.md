# Project Skills

This file is the compact workflow index for the scaffold. It complements
`AGENTS.md` and does not replace the architecture mapping. Status labels mean
local (implemented in the scaffold), compatibility (retained for the legacy
comparison path), planned (interface or integration gap), and research (not an
approved runtime policy).

## Flowchart to Scaffold

Use the Figma board as the design source and
`draft_agentic_perp_trading_bot/architecture_to_code_mapping.md` as the
file-to-file map. Update the map when a responsibility moves; update README
only when the public overview changes.

~~~text
TelegramAgent/Telethon retrieval
  -> adapters/telegram/normalize, hydrate, archive, and deduplicate
  -> publish normalized context to the downstream boundary
  -> `flows/telegram_signal_flow.py`
  -> one owner QWEN definition + shared Ministral review
  -> deterministic domain policies and Flow-only persistence
  -> guarded Aster/Hyperliquid execution boundary
~~~

Telegram transport belongs to `adapters/telegram/`; the Flow consumes its
normalized envelope. Do not copy the full flowchart into source comments.

## TelegramAgent Ingestion

Owner: `adapters/telegram/` and the Lightsail retrieval worker. Status: local
worker and in-memory adapters; production S3, DynamoDB, SQS, and media
hydration are planned.

Use one long-lived worker and one authorized user session. Configure lightweight
per-chat retrieval adapters inside the shared worker; do not deploy one
TelegramAgent service per channel. Expose retrieval only. Do not register a
send tool or route TelegramAgent output directly to an exchange.

Session provisioning is an operator-controlled local-login and encrypted
Lightsail handoff; the worker only loads the pre-provisioned session. Follow the
authoritative security and failure-stop rules in `AGENTS.md`.

Process each bounded pull in this order:

~~~text
retrieve and validate batch
  -> normalize text, provenance, and media presence
  -> hydrate media and archive raw bytes
  -> persist source metadata
  -> update the owner reply-tree index
  -> build chronological parent context and load active cursor snapshots
  -> publish the immutable normalized context
  -> record a per-message receipt only after successful publication
~~~

The local pipeline uses an injected publisher and in-memory stores. A failed
publication must remain replayable. A duplicate may be acknowledged only when
a local or durable delivery record proves that the earlier publication
succeeded; metadata persistence alone is not delivery.

Preserve `owner_id`, `channel_id`, `telegram_chat_id`, `telegram_message_id`,
`source_timestamp`, `parent_messages`, `media_hashes`, `asset_group`, and
`strategy_tier_hint`. Parent messages are traversed oldest first and are passed
as ID-labelled blocks to both QWEN and Ministral. Keep message bodies in the
owner reply-tree index/cache; use DynamoDB for durable metadata, concurrent
trade cursors, and replay records. All sources use the same retrieval-only
channel workflow; no private-chat reply path is supported.

## Concurrent Trade Cursors

Owner: `domain/lifecycle/cursor.py` plus its persistence adapter. Status: local
manager and in-memory repository; conditional DynamoDB storage is planned.

Maintain concurrent cursors for parent-linked symbol, exchange, network,
settlement asset, and direction. A message may resolve several candidates from
its ordered parent list. Store only message IDs assigned to a cursor; parent
context is not automatic cursor membership.

Each cursor stores active order IDs and open position IDs. An update, fill,
reduction, or partial close does not close a cursor. Close it only after a
position has opened, all positions are closed, and all active orders are gone.
Policy revisions follow the acceptance rule in [Confidence Calculation](#confidence-calculation);
rejected updates leave the selected policy unchanged. Each cursor replacement
is conditional on that cursor's expected version, so a stale write cannot
overwrite newer state.

## Agentic Deduplication

Owner: owner-specific QWEN reasoning, with deterministic identity helpers.
Status: byte/media identity and deferred-labelling persistence are local;
semantic relation reasoning, production table provisioning, Flow wiring, and
durable signal acceptance are planned.

Keep these stages separate:

1. Input identity: Python may hash exact text and hydrated media bytes.
2. Message relation: QWEN classifies `duplicate`, `continuation`, `new_signal`, or
   ambiguous from chronological context and RAG.
3. Deferred labelling: flagged messages and their prompt context enter the
   dedicated DynamoDB labelling table without blocking ingestion.
4. Signal identity: validated structured hypotheses receive a durable
   `signal_dedup_key`.
5. Delivery receipt: publication success is recorded separately.

Do not use keyword, substring, or regular-expression rules to interpret Chinese
trading messages. The relation result is a structured decision, not an order:

~~~jsonc
{
  "relation": "continuation",
  "matched_message_ids": ["<real channel-scoped Telegram ID, oldest first>"],
  "confidence": 0.91,
  "reason_codes": ["same_symbol", "updated_entry_range"],
  "needs_human_labelling": false
}
~~~

`needs_human_labelling` schedules offline dataset work; it is not a synchronous
approval gate. Ambiguous relations set it automatically, and other low-confidence
outputs may set it explicitly. `DeferredQwenLabellingQueue` stores the complete
ID-labelled prompt context and relation decision through
`DynamoDBMessageLabellingRepository`, keyed by owner/channel and Telegram
message ID. The relation stage and queue call are wired into the canonical Flow;
the local entrypoint uses the in-memory adapter, while production table
provisioning and durable DynamoDB injection remain deployment work.

An illustrative serial RAG object preserves the complete message sequence and
the execution result associated with it:

~~~jsonc
{
  "example_id": "owner-c-btc-001",
  "strategy_tier": "conservative",
  "messages": [
    {
      "telegram_message_id": "<channel-scoped-message-id-1>",
      "telegram_message_url": "https://t.me/c/<channel-id>/<message-id-1>"
    },
    {
      "telegram_message_id": "<channel-scoped-message-id-2>",
      "telegram_message_url": "https://t.me/c/<channel-id>/<message-id-2>"
    }
  ],
  "s3_archive_uri": "s3://PRIVATE_RAG_BUCKET/owner-c-btc-001.json",
  "execution_label": "incorrect",
  "error_reason": "stop-loss update was applied to the wrong position"
}
~~~

This is a shape illustration, not a fixture. IDs are channel-scoped strings;
real curated records must use their authentic Telegram IDs and URLs. A later
add-to-position or execution-update message can be a continuation rather than
a duplicate. Low-confidence and ambiguous outputs are retained for deferred
labelling. Only completed labels that pass curation may become serial RAG
examples; queued model output is not itself trusted RAG data. Measure relation
precision/recall, continuation-link accuracy, false merges, and new-signal
recall using complete serial message sequences.

## QWEN-Agent RAG-loading

Owner: `agent_interfaces.qwen.SerialRagLoaderAPI` and the selected owner QWEN
definition. Status: local profile loading; authenticated S3 retrieval, ranking,
lifecycle filtering, and image-byte delivery are planned.

Load the owner profile and serial examples separately from QWEN inference.
Provide the same immutable TelegramPromptContext, parent IDs/media hashes,
active cursor snapshots, and RAG records to QWEN and Ministral. Each QWEN run
must return all five strategy tiers. Every hypothesis is an order proposal, never a streamlined order execution.

The output boundary requires `owner_id`, `channel_id`, `asset_group`,
`strategy_tier`, `intent_type`, `symbol`/`direction` when known, `entries`,
`confidence`, `evidence`, and `source_dedup_key`. If the source message omits a
stop-loss, leave `stop_loss` unset so the deterministic policy at the Ministral
boundary can derive it later.

Keep serial-RAG curation separate from stop-loss handling. Each curated object
must preserve chronological message references, `s3_archive_uri`,
`strategy_tier`, and a verified `execution_label`. Do not invent message IDs,
URLs, media, or outcomes; current profile examples are empty until manually
populated. Curators may promote completed records from the deferred DynamoDB
labelling table only after validating their labels and provenance.

## Confidence Calculation

Owner: `domain/policies/confidence.py`. Status: local synthetic-v2 baseline;
learned features are research.

Confidence ranks hypotheses and selects one of five strategy tiers. It is not a
hard rejection rule. The current synthetic baseline combines source confidence
(0.45), Ministral quality when available (0.25), and replay performance when
available (0.30), renormalizing available weights. Persist the selected tier,
confidence, size, leverage, formula version, and provenance on the lifecycle
cursor.

At lifecycle commencement, confidence selects the initial policy. A
parent-linked continuation inherits it unless an explicit `strategy_tier_hint` is
reviewed and accepted as a policy revision. This selection is independent of
deterministic execution permission.

The proposed technical/EMA/volatility features and RNN/LSTM experiments are
research. They must use chronological train/validation/forward-test windows,
prevent future-data leakage, and be compared with the synthetic baseline
before influencing live decisions.

## Omitted Stop-Loss Inference

Owner: deterministic `domain/policies/stop_loss.py`, invoked by a Flow through
`tools/stop_loss_policy_tool.py`. Status: local pure policy; complete MCP supplier
and measured deadline are planned.

QWEN leaves an omitted stop-loss unset. The Aster/Hyperliquid market boundary
must provide price, market capitalization, quote volume, pair type, and EMA,
MACD, KDJ, RSI, Bollinger width, ATR, and realized volatility for 5m, 15m, 1h,
and 4h. The deterministic policy uses:

- distance bands: 1.2%-3.5% TradFi, 1.5%-5% mainstream coins, and 2.5%-8%
  altcoins;
- timeframe weights 10%/20%/30%/40%;
- indicator weights EMA/MACD/KDJ/RSI/Bollinger/ATR/realized volatility of
  12%/12%/10%/10%/18%/23%/15%; and
- 35% volume score plus 65% technical score.

The anchor is entry 1, or the arithmetic mean of entry 1 and entry 2. The
result remains globally bounded to 1.2%-8%, below the anchor for a long and
above it for a short. Invalid or missing required market inputs must stop
derivation rather than receive a fabricated fallback. The one-second value is
a computation-budget requirement until elapsed time is measured.

## Pair Blacklisting

Owner: `domain/policies/execution_gate.py`. Status: local deterministic policy
with a pending policy clarification.

For each canonical exchange/symbol pair, evaluate closed net outcomes within
the trailing 90 days. Exclude open, cancelled, incomplete, and breakeven
records; require minimum observations; count net wins and losses; and blacklist
only when the win/loss ratio is strictly below the configured threshold. Keep
the window, counts, threshold, minimums, policy version, and timestamp.

The current code also contains a stop-loss-reversal criterion. Its relationship
to the ratio-only rule is unresolved and requires human policy approval; do not
hide the discrepancy in documentation. No QWEN, Ministral, or confidence score
may override a confirmed blacklist. Deterministic gates also enforce instant-
order price deviation, depth, slippage, leverage, and cumulative limits.

## Ministral Validation

Owner: `agent_interfaces.ministral.MinistralReviewAPI` and the shared Ministral
agent. Status: local one-model structured review; model comparison and stronger
evidence/injection checks are planned.

Review all five QWEN candidates against the same immutable source context.
Validate source identity, evidence, ambiguity, candidate/review binding, and
semantic signal duplication. Emit one typed review per tier. Only an approved
reviewed proposal can reach deterministic canonicalization:

~~~text
QWEN five-tier candidates
  -> shared Ministral review
  -> source and structure validation
  -> deterministic confidence, sizing, and execution gates
  -> Flow-only persistence or execution intent
~~~

The 8B/14B comparison is an evaluation workflow, not current runtime behavior.
Ministral never calls an exchange, mutates a cursor, or overrides a
deterministic gate.

## Reduce Position and Protect Entry (QWEN)

Owner: `agent_interfaces.qwen.QwenPositionReductionAPI`. Status: typed
compatibility contract; lifecycle integration is planned.

Return a reviewable hypothesis requesting a 30%-40% reduction of the
configured maximum total quantity and a 0.15% profitable-direction stop
offset. Deterministic Flow services must validate live quantity, average entry,
venue rounding, reduce-only constraints, confirmation, and unfilled TP1/TP2/TP3
resizing. QWEN does not cancel, replace, or submit orders.

## Take-Profit Fill Entry Protection (Ministral)

Owner: deterministic take-profit policy coordinated by the lifecycle Flow.
Status: legacy pure policy is available; authenticated event ingress, durable
idempotency, and guarded application are planned.

After authenticated TP1 fill, request a stop 0.15% beyond average entry in the
profitable direction. After TP2 follows TP1, move the stop to recorded TP1 only
when TP3 remains configured and unfilled. Never loosen an existing stop.

Deduplicate by stable event ID and return a typed adjustment decision. A
deterministic execution boundary, not Ministral, applies it. "Immediately" is
a service objective until elapsed time is measured.

## Weight and Confidence

Owner: deterministic sizing and confidence policies. Status: fixed scaffold
weights are local; learned updates are research.

Use replayable TP1/TP2, stop-loss, P/L, and reversal metrics to evaluate future
owner/channel/strategy-tier weighting. Confidence selects the tier before
sizing; sizing then applies fixed owner/asset weights, quality scaling, tier
multipliers, and leverage bounds. Do not place blacklist or execution
permission in this skill.

## Paired Testnet Venue Performance

Owner: `domain/performance/venue_comparison.py` and `PerformanceEvaluationFlow`.
Status: local partial implementation.

Compare Aster and Hyperliquid only on the intersection of deduplicated, fully
closed testnet positions sharing the same `signal_dedup_key` and `strategy_tier`.
Aggregate partial closes at the position/signal grain, normalize net P/L by
allocated entry notional, and report the metric units and sample counts.
Exclude unmatched signals and mainnet outcomes. Evaluate all five strategy
tiers separately, including clearly labelled counterfactual replay results.

P/L is not by itself a complete reliability measure. Keep execution status,
position identity, venue/network, owner, channel, asset group, lifecycle stage,
and outcome provenance so later strategy optimization is reproducible.

## Trading Message Synonym Inference

Owner: selected owner QWEN; `agent_interfaces.qwen.QwenSynonymInferenceAPI`.
Status: review-only placeholder.

Infer a closest baseline signal class and conditional strategy profile from
authenticated, timestamped context and serial RAG. Allow abstention when no
baseline is safe. Return the matched class, strategy identifier, evidence, and
confidence for Ministral review. Keep synonym meaning separate from duplicate,
continuation, and new-signal relation. This skill creates no execution command
and calls no Aster or Hyperliquid API.

## Exchange and AWS Boundary

Owner: exchange adapters, MCP proxies, and AWS execution boundaries. Status:
typed/local boundaries; production signing submission, secret retrieval, SQS,
WebSockets, and observability exporters are planned.

Keep Aster and Hyperliquid behind the MCP gateway and default to testnet.
Aster V1 uses REST/HMAC signing; Hyperliquid uses its approved upstream signing
boundary. The local augmented proxies provide read-only market/depth/slippage
snapshots and unsigned handoffs. Lambda is the intended credential and guarded
execution boundary. Secrets never enter prompts, logs, fixtures, RAG files, or
commits. Stable client order IDs support reconciliation but do not prove
execution idempotency.

## Verification

For behavior changes, add a focused test first. From
`draft_agentic_perp_trading_bot/`:

~~~bash
uv sync --extra aws --extra telegram --extra exchange-upstreams --extra dev --extra crewai
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
~~~

For documentation-only edits, run git diff --check and verify referenced
paths. Distinguish static/offline and focused tests from full Flow execution:
the local CrewAI Flow remains an integration scaffold and is not certified by
test collection alone.
