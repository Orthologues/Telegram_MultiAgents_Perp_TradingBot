# MCP Servers

This folder contains exchange-specific MCP servers that back the scaffolded
exchange gateway.

- `hyperliquid_mcp/`: guarded proxy to the pinned Hyperliquid MCP interface.
- `aster_mcp/`: Aster V3 reads and guarded proxy to the official Aster MCP.

The intended split is:

- MCP transport: Streamable HTTP at `/mcp`
- market/account state: WebSocket workers where practical
- stop-loss analysis input: typed pair type, price, volume, EMA, MACD, KDJ,
  RSI, Bollinger, ATR, and volatility snapshots at 5m, 15m, 1h, and 4h
- authenticated take-profit fill events for idempotent Ministral stop protection
- signed order execution: REST requests or AWS Lambda execution after filter
  plus explicit confidence and deterministic-risk decisions
- network policy: testnet by default, with distinct Aster-USDT and
  Hyperliquid-USDC metadata
