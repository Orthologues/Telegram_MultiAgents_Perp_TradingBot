# MCP Servers

This folder contains exchange-specific MCP servers that back the scaffolded
exchange gateway.

- `hyperliquid_mcp/`: Hyperliquid read and guarded Lambda-handoff scaffold.
- `bitget_mcp/`: Bitget read and guarded Lambda-handoff scaffold.

The intended split is:

- MCP transport: Streamable HTTP at `/mcp`
- market/account state: WebSocket workers where practical
- stop-loss analysis input: typed current price, market cap, 24-hour quote
  volume, and KDJ, Bollinger, and ATR snapshots at 5m, 15m, 1h, and 4h
- authenticated take-profit fill events for idempotent Ministral stop protection
- signed order execution: REST requests or AWS Lambda execution after filter
  plus explicit confidence and deterministic-risk decisions
