# Project Skills

This file is a compact index of repeatable repository workflows. It complements
`AGENTS.md`; it is not a second architecture specification.

## Flowchart to Scaffold

Use the Figma board as the design source and
`draft_agentic_perp_trading_bot/docs/figma_flowchart_mapping.md` as the code
mapping.

Example:

```text
new Figma node: "Input Normalizer"
  -> telegram_ingestion/normalizer.py
  -> schemas.py for traceable fields
  -> tests/test_deduplication.py for behavior
```

When a boundary moves, update the mapping document and README together. Do not
copy the entire flowchart into source code comments.

## Telegram Ingestion

Normalize Chinese text and image metadata before model inference. Archive raw
media in S3, store searchable metadata in DynamoDB, and compute a stable input
deduplication key.

Example path:

```text
Telegram update
  -> TelegramMessageEnvelope
  -> content/media hashes
  -> shared-store conditional write
  -> QWEN only for a first-seen input
```

Preserve `owner_id`, `channel_id`, `asset_group`, and `strategy_tier_hint` so
multiple channels can feed one owner agent without losing provenance.

## Agentic Deduplication

Do not understand serial Chinese trading messages with Python keyword,
substring, or regular-expression rules. The owner-specific QWEN agent must
apply this deduplication reasoning skill to the message sequence and RAG
examples. Use Python only for exact byte/media identity, candidate retrieval,
persistence, and state.

This is a reasoning skill within each owner-specific QWEN agent, not a separate
keyword-based Python service. It receives:

- the original Chinese text and available images;
- the owner/channel/asset-group context;
- the versioned owner RAG profile with serial message-to-execution examples for
  conservative, intermediate, and radical strategy tiers;
- annotated incorrectly executed examples and their error explanations; and
- a small set of candidate prior messages and active signal state.

It returns a structured decision, not an order:

```json
{
  "relation": "continuation",
  "matched_message_ids": ["owner_c_channel_1842"],
  "confidence": 0.91,
  "reason_codes": ["same_symbol", "updated_entry_range"],
  "needs_human_review": false
}
```

The RAG unit should preserve the complete sequence rather than an isolated
message:

```json
{
  "strategy_tier": "conservative",
  "messages": ["... Chinese signal ...", "... Chinese execution update ..."],
  "intended_execution": {"symbol": "BTCUSDT", "direction": "long"},
  "execution_label": "incorrect",
  "error_reason": "stop-loss update was applied to the wrong position"
}
```

Use these relations:

- `duplicate`: a repost, quoted message, repeated screenshot, or materially
  identical signal;
- `continuation`: an update to an existing entry, position, target, stop, or
  execution state;
- `new_signal`: a distinct trade hypothesis;
- `ambiguous`: insufficient evidence to merge safely.

For example, a later Chinese message saying to add to an existing position may
be a continuation, not a duplicate. A message announcing that an order was
executed may update state without creating a new entry hypothesis. The QWEN
agent must learn these distinctions from the owner and channel RAG examples,
including examples where the resulting execution was wrong.

The runtime sequence is:

```text
byte-identical hash shortcut only
  -> retrieve bounded candidate history
  -> owner-specific QWEN deduplication reasoning skill
  -> persist decision and provenance
  -> owner-specific QWEN trade hypothesis for accepted new or continuation input
```

Low-confidence and ambiguous cases are retained and routed for review. Measure
the skill with a labeled replay set: duplicate precision/recall, continuation
link accuracy, false-merge rate, and new-signal recall. Test fixtures should
contain complete serial message sequences, not only isolated first-seen and
repeated-message pairs.

## Owner QWEN Agent

Load the owner-specific serial JSON RAG profile, provide recent signal and
position context, and request only a `QwenSignalHypothesis`.

Example output boundary:

```json
{
  "owner_id": "owner_c_bi_jia_suo",
  "asset_group": "btc_eth",
  "strategy_tier": "intermediate",
  "intent_type": "open",
  "symbol": "BTCUSDT",
  "direction": "long",
  "entries": ["65000"],
  "stop_loss": "64200",
  "take_profit": ["66000", "67000"],
  "confidence": 0.78,
  "evidence": ["Chinese source message", "chart attachment"]
}
```

The example is a hypothesis, not an order. Do not add exchange credentials or
position sizing to the model prompt as a substitute for deterministic policy.

## Confidence Calculation

Confidence is a synthetic, traceable feature for ranking and weighting trade
hypotheses. It is not a risk approval and it must not override the deterministic
risk engine.

The initial feature groups are:

- owner and strategy performance from recent simulation runs, including recent
  win rate and cumulative gain for the relevant strategy tier;
- technical alignment across 15-minute, 1-hour, and 4-hour MACD, KDJ, and
  Bollinger Band features;
- 4-hour and 1-day EMA trend features; and
- recent coin volatility, with higher volatility lowering the volatility
  component of confidence.

The first implementation should expose the components separately and combine
normalized values through a versioned synthetic function, for example:

```text
confidence_synthetic = clip(
    w_performance * performance_score
  + w_technical   * technical_alignment_score
  + w_trend       * ema_trend_score
  + w_volatility  * volatility_penalty,
    0,
    1,
)
```

The weights, normalization windows, volatility measure, and indicator
aggregation are provisional research parameters, not established truth. Store
the feature snapshot, simulation window, strategy tier, weights, formula
version, and timestamp with every confidence result so it can be replayed.

The intended learned version requires chronological ML experiments, initially
with an RNN or LSTM over the time-ordered feature and outcome history. Define
the target from simulated execution outcomes, prevent future-data leakage,
compare against the synthetic baseline, and calibrate the resulting score
before using it for agent weighting. Preserve separate train, validation, and
forward-test periods. Until that evaluation is complete, use the synthetic
score only for analysis or conservative weighting and never as permission to
execute an order.

## Ministral Validation

Run the 8B and 14B variants through the same adapter and record the model id.
Validate schema and source evidence, reject prompt injection and unresolved
ambiguity, deduplicate equivalent hypotheses, then emit a canonical intent.

Example decision flow:

```text
QWEN hypothesis
  -> schema and evidence checks
  -> signal deduplication
  -> approve/reject with reasons
  -> CanonicalTradeIntent only on approval
```

Keep explanations and labels available to the performance engine, but never let
free-form model reasoning override hard risk rules.

## Weight and Risk

Use realized, replayable metrics such as TP1/TP2 hit rate, stop-loss rate,
cumulative P/L, and post-stop-loss reversal rate to update owner/channel and
strategy-tier weights. The deterministic risk engine remains the final policy
gate for symbol allowlists, maximum position value, leverage, cooldowns,
conflicting positions, and slippage.

Example order path:

```text
canonical intent
  -> weight-adjusted sizing
  -> risk approval
  -> ApprovedExecutionRequest
```

## Exchange and AWS Boundary

Keep Bitget and BitMart adapters behind the MCP gateway. Use ECS WebSockets for
market-data transport when low latency is required, and signed HTTPS REST for
order execution. Lambda retrieves exchange credentials and kill-switch settings
from Secrets Manager; secrets never enter logs, fixtures, RAG files, or commits.

## Verification

For every behavior change, add the smallest focused test first, then run:

```bash
cd draft_agentic_perp_trading_bot
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
```

If the change is documentation-only, at minimum run `git diff --check` and
verify that all referenced paths exist.
