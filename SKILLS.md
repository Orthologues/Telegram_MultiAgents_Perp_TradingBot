# Project Skills

This file is a compact index of repeatable repository workflows. It complements
`AGENTS.md`; it is not a second architecture specification.

## Flowchart to Scaffold

Use the Figma board as the design source and
`draft_agentic_perp_trading_bot/architecture_to_code_mapping.md` as the code
mapping.

Example:

```text
new Figma node: "TelegramAgent"
  -> telegram_ingestion/agent_worker.py
  -> telegram_ingestion/normalizer.py
  -> telegram_ingestion/storage.py and pipeline.py
  -> schemas.py for traceable fields
  -> tests/test_telegram_agent_ingestion.py for behavior
```

When a boundary moves, update the mapping document and README together. Do not
copy the entire flowchart into source code comments.

## TelegramAgent Ingestion

Run one long-lived polling service on Lightsail, with EC2 as the scale-up path,
and one authorized Telegram user session. Schedule the target channels through
lightweight per-chat retrieval adapters that preserve each `chat_id`,
per-message receipt, and provenance boundary. Because AG2 retrieval is scoped to
one `chat_id`, an
adapter may wrap a per-chat TelegramAgent object internally, but these objects
remain in the same worker and are not independently deployed services. Expose
only retrieval through the executor. Do not register `TelegramSendTool` and do
not route TelegramAgent output directly to an exchange or trading model.

TelegramAgent retrieval is pull-based. Retrieve a bounded recent window without
a channel-level cursor, normalize Chinese text and image metadata before model
inference, archive raw media in S3, store searchable metadata in DynamoDB, and
compute a stable input deduplication key. AG2 exposes only a media-presence flag,
so use an adjacent authenticated media hydrator to obtain bytes and hashes
before recording the message receipt.

For the A-zhu private-chat workflow, use the minimalist Chinese reply skill
when a short acknowledgment is explicitly required. Keep this response path
separate from retrieval and exchange execution: it may acknowledge receipt, but
it must not infer trade parameters, confirm execution, or replace QWEN analysis.

Example path:

```text
TelegramAgent retrieval with no channel cursor
  -> validate structured retrieval batch
  -> order messages chronologically
  -> TelegramMessageEnvelope
  -> traverse prior reply-tree messages from the owner QWEN in-memory index
     into parent_messages (oldest first)
  -> TelegramPromptContext with ID-labeled parent blocks and current block last
  -> query active DynamoDB trade cursors by parent message IDs
  -> expose matching pair/exchange/order/position state to QWEN and Ministral
  -> pass the same context to QWEN and Ministral prompts
  -> hydrate/archive media and persist metadata
  -> exact content/media identity check
  -> retrieve candidate message history
  -> owner-specific QWEN deduplication reasoning
  -> accepted new or continuation context
  -> conditionally record each `(channel_id, telegram_message_id)` receipt
```

Keep retrieval and per-message receipt recording as separate operations. Use a
conditional DynamoDB receipt write and only one active, leased worker per
Telegram user session. Preserve `owner_id`,
`channel_id`, `telegram_chat_id`, `telegram_message_id`, `source_timestamp`,
`parent_messages`, `asset_group`, and `strategy_tier_hint`
so multiple channels can feed one owner agent without losing provenance.
DynamoDB is both a live coordination store and a replay dataset. Query active
trade cursors by parent message IDs, but keep chronological message bodies in
the owner QWEN ElastiCache reply tree with a process-local read-through cache.
Retain omitted take-profit/stop-loss cases, inferred levels, later updates,
execution outcomes, and pair-blacklisting inputs.

## Concurrent Trade Cursors

Maintain one active `TradeThreadCursor` per parent-linked symbol, exchange, and
direction. A new message may resolve several concurrent candidates from its
chronological `parent_messages`; match the intended cursor by canonical symbol,
Aster or Hyperliquid exchange, network, and long/short direction. Store only
messages assigned to that cursor, not the complete parent list.

Each cursor stores sets of active order IDs and open position IDs in DynamoDB.
Use conditional version writes so unrelated cursors update independently. An
order fill, reduction, or partial close updates the sets but does not close the
cursor. Close it only after a position has opened, no open position remains,
and all active orders are gone.

## Minimalist Chinese Reply

Use this skill only for the A-zhu private-chat workflow when a concise response
is explicitly required. Produce a brief Chinese acknowledgment equivalent to
"yes" or "ok", without adding market commentary, inferred stop-loss or
take-profit levels, execution claims, or new trading instructions. Preserve the
source message and response provenance for later replay and review.

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
  "example_id": "owner-c-btc-001",
  "strategy_tier": "conservative",
  "messages": [
    {
      "telegram_message_id": "1001",
      "telegram_message_url": "https://t.me/c/123456/1001"
    },
    {
      "telegram_message_id": "1002",
      "telegram_message_url": "https://t.me/c/123456/1002"
    }
  ],
  "s3_archive_uri": "s3://PRIVATE_RAG_BUCKET/owner_c_btc-001.json",
  "execution_label": "incorrect",
  "error_reason": "stop-loss update was applied to the wrong position"
}
```

Manually add authentic examples only. Keep their Telegram IDs and URLs in the
owner JSON profile, archive the complete text/media sequence in private S3,
and record its S3 URI in the same example object. Do not invent message URLs,
IDs, or execution outcomes.

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

## QWEN-Agent RAG-loading

Load the owner-specific serial JSON RAG profile, provide recent signal and
position context, and request a `QwenStrategyCandidateSet` containing all five
tiers. Include the same `TelegramPromptContext` supplied by ingestion: parent
messages must remain ID-labeled, ordered oldest-to-newest, and available to both
QWEN and Ministral.

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

Confidence is a synthetic, traceable feature for ranking trade hypotheses and
selecting one of five tiers from ultra-conservative to ultra-radical. It does
not perform hard rejection; deterministic risk owns execution constraints.
Persist the selected tier, recommended size, leverage, and confidence
provenance on each trade cursor. Parent-linked lifecycle updates inherit this
policy; only an explicit `strategy_tier_hint` with a Ministral-approved target
candidate creates the next policy revision.

The initial feature groups are:

- owner and strategy performance from recent simulation runs, including recent
  win rate and cumulative gain for the relevant strategy tier;
- technical alignment from `5m`, `15m`, `1h`, and `4h` KDJ, Bollinger-width,
  and ATR features, plus the existing MACD features;
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

## Omitted Stop-Loss Inference

When an order omits its stop-loss, QWEN must leave `stop_loss` unset. The
Aster/Hyperliquid MCP boundary supplies current price, market capitalization,
24-hour quote volume, trading-pair type, and EMA, MACD, KDJ, RSI, Bollinger,
ATR, and realized-volatility snapshots for `5m`, `15m`, `1h`, and `4h`.
Ministral applies the versioned deterministic policy in
`agentic_perp_trading_bot.ministral_filter.stop_loss_policy`.

The draft pair-type bands are `1.2%`-`3.5%` for TradFi, `1.5%`-`5%` for
mainstream coins, and `2.5%`-`8%` for altcoins. Score timeframes at
`10%`/`20%`/`30%`/`40%`, and score EMA, MACD, KDJ, RSI, Bollinger width, ATR,
and realized volatility at `12%`/`12%`/`10%`/`10%`/`18%`/`23%`/`15%`.
Adverse EMA/MACD direction receives the full normalized component; aligned
direction receives half. Combine `35%` volume score with `65%` technical score,
then interpolate inside the pair-type band.

The final distance remains globally bounded to `1.2%`-`8%` from entry 1, or
from the average of entry 1 and entry 2. Place the stop below that reference
for a long and above it for a short.

Record the MCP snapshot, pair type, liquidity tier, component scores, distance,
policy version, and derived price. Keep Ministral stop-loss reasoning within a
one-second budget. Explicit source stop-losses are preserved, and omitted
stop-loss derivation does not add another hard-rejection rule. Backtest all
thresholds and weights before production use. Its API contract is
`agentic_perp_trading_bot.skills_api.omitted_stop_loss_inference.OmittedStopLossInferenceAPI`.

## Pair Blacklisting

Use a deterministic temporary blacklist to reject exchange/symbol pairs whose
recent realized performance is persistently poor. This is a deterministic
risk rejection, not a QWEN decision.

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
  "exchange_id": "hyperliquid",
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
Apply the blacklist before order execution, and do not allow QWEN, Ministral,
or a confidence score to override it. Deterministic risk also enforces
instant-order price deviation plus owner/pair leverage and cumulative
position-value limits. If profit-to-loss amount
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
free-form model reasoning override the pair blacklist or instant-order price
distance check.

## Reduce Position and Protect Entry (QWEN)

Use this owner-QWEN skill when a Telegram message instructs the bot to reduce an
existing position and move its stop-loss into profit. Return a reviewable
position-management hypothesis, not an executable order.

The hypothesis must request a reduction of `30%`-`40%` of the position's
configured maximum total quantity. Move the stop-loss `0.15%` beyond the
average entry price in the profitable direction: above entry for a long and
below entry for a short. The live direction, average entry, maximum quantity,
exchange constraints, and current order state must come from MCP and be
validated by Ministral.

After the reduction is confirmed, cancel and replace only the still-unfilled
TP1, TP2, and TP3 reduce-only limit orders so their quantities match the
remaining position. Preserve filled take-profit orders and execution history.
Its API contract is
`agentic_perp_trading_bot.skills_api.owner_qwen.OwnerQwenAPI.infer_position_reduction`.

## Take-Profit Fill Entry Protection (Ministral)

Use this skill when the MCP boundary emits an authenticated take-profit fill
event independently of TelegramAgent. After TP1 fills, Ministral must
immediately request that the stop-loss move `0.15%` beyond the average entry
price in the profitable direction.

After TP2 fills following TP1, move the stop-loss to the recorded TP1 price only
when TP3 is configured and remains unfilled. Validate the position direction,
fill sequence, configured take-profit levels, average entry, TP1 price, and
current stop-loss. Never loosen a stop that is already more profitable.

Deduplicate repeated fill events by their stable event ID and return a typed
adjustment decision for MCP execution; Ministral must not call an exchange
directly. Its API contract is
`agentic_perp_trading_bot.skills_api.ministral_filter.MinistralFilterAPI.protect_entry_after_take_profit`.

## Weight and Confidence

Use realized, replayable metrics such as TP1/TP2 hit rate, stop-loss rate,
cumulative P/L, and post-stop-loss reversal rate to update owner/channel and
strategy-tier weights. The confidence engine selects the strategy tier, while
the deterministic risk engine enforces execution constraints.

Example order path:

```text
canonical intent
  -> weight-adjusted sizing
  -> confidence-based strategy tier
  -> deterministic risk constraints
  -> ApprovedExecutionRequest
```

## Paired Testnet Venue Performance

Compare Aster and Hyperliquid reliability only over the intersection of closed
testnet positions sharing the same `signal_dedup_key`. Aggregate partial closes
per signal and venue, normalize net P/L by entry notional, and report wins,
losses, gross profit, gross loss, net P/L, mean P/L, and profit-to-loss ratio.
Exclude unmatched signals and all mainnet outcomes so differences in signal
selection do not contaminate the Aster-USDT versus Hyperliquid-USDC comparison.
Use `performance_engine.compare_testnet_venue_performance`.

## Trading Message Synonym Inference

Use QWEN reasoning to infer the meaning of Chinese trading messages quickly.
Build a baseline vocabulary of signal classes and associate each class with a
conditional strategy profile indexed by the trading pair's reference price at
message time. Map each incoming Telegram message to its closest baseline
synonym and return the matched class, strategy identifier, evidence, and
confidence. Pass this structured result to Ministral for validation. This skill
produces no execution command and must not call Aster or Hyperliquid APIs.
Its API contract is
`agentic_perp_trading_bot.skills_api.owner_qwen.OwnerQwenAPI.infer_synonym`.

## Exchange and AWS Boundary

Keep Aster and Hyperliquid adapters behind the MCP gateway and default both to
testnet. Use ECS WebSockets for low-latency market data and signed HTTPS REST for
execution. The local augmented proxies preserve deterministic guards, while
Lambda retrieves API-wallet and kill-switch secrets and delegates signing to
the pinned official Aster V3 client or referenced Hyperliquid MCP/SDK. Secrets
never enter logs, fixtures, RAG files, or commits.

## Verification

For every behavior change, add the smallest focused test first, then run:

```bash
cd draft_agentic_perp_trading_bot
uv sync --extra aws --extra telegram --extra exchange-upstreams --extra dev --extra crewai
uv run pytest -q
uv run ruff check .
uv run python -m compileall -q src tests
```

If the change is documentation-only, at minimum run `git diff --check` and
verify that all referenced paths exist.
