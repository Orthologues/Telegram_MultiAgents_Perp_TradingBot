# Project Skills

This file is a compact index of repeatable repository workflows. It complements
`AGENTS.md`; it is not a second architecture specification.

## Flowchart to Scaffold

Use the Figma board as the design source and
`draft_agentic_perp_trading_bot/docs/figma_flowchart_mapping.md` as the code
mapping.

Example:

```text
new Figma node: "TelegramAgent"
  -> telegram_ingestion/agent_worker.py
  -> telegram_ingestion/normalizer.py
  -> schemas.py for traceable fields
  -> tests/test_telegram_agent_ingestion.py for behavior
```

When a boundary moves, update the mapping document and README together. Do not
copy the entire flowchart into source code comments.

## TelegramAgent Ingestion

Run a long-lived polling service on Lightsail, with EC2 as the scale-up path.
Configure one AG2 TelegramAgent per target `chat_id`, backed by the same
authorized Telegram user account, and expose it through a retrieval-only
executor. Do not register `TelegramSendTool` in that executor and do not route
TelegramAgent output directly to an exchange or trading model.

TelegramAgent retrieval is pull-based. Poll from the last committed message id,
normalize Chinese text and image metadata before model inference, archive raw
media in S3, store searchable metadata in DynamoDB, and compute a stable input
deduplication key. AG2 exposes only a media-presence flag, so use an adjacent
authenticated media hydrator to obtain bytes and hashes before cursor commit.

Example path:

```text
TelegramAgent retrieval after durable channel cursor
  -> validate structured retrieval batch
  -> order messages chronologically
  -> TelegramMessageEnvelope
  -> hydrate/archive media and persist metadata
  -> exact content/media identity check
  -> retrieve candidate message history
  -> owner-specific QWEN deduplication reasoning
  -> accepted new or continuation context
  -> atomically advance channel cursor
```

Keep retrieval and cursor commit as separate operations to preserve
at-least-once delivery. Use a conditional DynamoDB cursor update and only one
active, leased worker per Telegram user session. Preserve `owner_id`,
`channel_id`, `telegram_chat_id`, `telegram_message_id`, `source_timestamp`,
`retrieval_cursor`, `asset_group`, and `strategy_tier_hint` so multiple channels
can feed one owner agent without losing provenance.

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

## Stop-Loss Inference

Use this skill when an owner, especially Lao-tu or Bi-jia-suo, gives an instant
altcoin order without an explicit stop-loss. The owner-specific QWEN agent must
infer a candidate from the serial Chinese message sequence and RAG examples,
not from a hardcoded keyword or universal percentage rule.

The QWEN context should include:

- the complete signal and execution-message sequence;
- owner, channel, asset group, strategy tier, and recent channel win rates;
- analogous correct and incorrectly executed RAG examples;
- entry price, direction, leverage, current position state, and exchange
  constraints;
- the 15-minute, 1-hour, and 4-hour technical context used by the confidence
  skill; and
- recent coin volatility and the relevant account-risk budget.

The skill returns a candidate and evidence, not an order:

```json
{
  "stop_loss_status": "inferred",
  "stop_loss": "64200",
  "inference_basis": ["owner_rag_017", "4h_support", "volatility_regime"],
  "confidence": 0.64,
  "needs_human_review": false
}
```

The provisional `0.8%-1.5%` idea must be defined as an account-risk or
position-notional constraint before implementation. It is not itself a
stop-loss price. Convert the candidate price and quantity into maximum loss
deterministically, then check leverage, liquidation distance, symbol rules,
slippage, and existing positions. Reject the trade or request review when the
QWEN agent cannot infer a defensible level.

Evaluate this skill with chronological backtests containing explicit and
omitted stop-losses, correct and incorrect executions, different strategy
tiers, and volatile versus calm markets. Track invalid or missing-stop rate,
stop-loss hit rate, maximum adverse excursion, false-safe decisions, and
whether the inferred level changes after later message updates.

## Pair Blacklisting

Use a deterministic temporary blacklist to reject exchange/symbol pairs whose
recent realized performance is persistently poor. This is a risk-policy
function, not a QWEN decision.

For each canonical `(exchange_id, symbol)` pair, use closed trades whose close
timestamp is within the trailing 90 days from the evaluation time:

1. Use net realized P/L after fees, funding, and execution costs.
2. Count `net_pnl > 0` as a win and `net_pnl < 0` as a loss.
3. Exclude breakeven, open, cancelled, and incomplete trades.
4. Require configurable minimum observations, such as
   `min_closed_trades` and `min_losses`, before making a blacklist decision.
5. Calculate `win_loss_ratio = wins / losses` when losses are nonzero. Treat a
   pair with wins and no losses as having an infinite ratio; do not blacklist
   a pair with insufficient observations.
6. Set `blacklisted = true` only when the ratio is strictly below the
   configured threshold.

Example decision:

```json
{
  "exchange_id": "bitmart",
  "symbol": "ALTUSDT",
  "window_days": 90,
  "wins": 3,
  "losses": 7,
  "win_loss_ratio": 0.4286,
  "threshold": 0.75,
  "min_closed_trades": 10,
  "blacklisted": true,
  "computed_at": "2026-07-18T12:00:00Z"
}
```

Persist the window, trade counts, net-P/L definition, threshold, minimum
sample settings, computation time, and policy version with every decision.
Apply the blacklist before MCP validation or order execution, and do not allow
QWEN, Ministral, or a confidence score to override it. If profit-to-loss amount
is later used instead of win/loss count, define it as a separate metric rather
than silently changing this ratio.

Test the boundary cases: a pair exactly at the threshold, one trade below the
threshold, no losses, insufficient observations, trades outside the 90-day
window, and fees that change a nominal win into a net loss.

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
from Secrets Manager. The Telegram worker separately retrieves Telegram API
ID/hash and the authorized user-session bootstrap. Secrets never enter logs,
fixtures, RAG files, or commits.

## Verification

For every behavior change, add the smallest focused test first, then run:

```bash
cd draft_agentic_perp_trading_bot
uv sync --extra aws --extra telegram --extra dev
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
```

If the change is documentation-only, at minimum run `git diff --check` and
verify that all referenced paths exist.
