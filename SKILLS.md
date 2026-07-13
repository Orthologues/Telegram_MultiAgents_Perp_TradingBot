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
