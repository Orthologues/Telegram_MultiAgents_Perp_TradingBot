# MCP Servers

This folder contains exchange-specific MCP servers that back the scaffolded
exchange gateway.

- `bitmart_mcp/`: existing BitMart Futures v2 Streamable HTTP MCP boilerplate.
- `bitget_mcp/`: planned Bitget perpetual futures MCP server.

The intended split is:

- MCP transport: Streamable HTTP at `/mcp`
- market/account state: WebSocket workers where practical
- stop-loss analysis input: typed current price, market cap, 24-hour quote
  volume, and KDJ, Bollinger, and ATR snapshots at 5m, 15m, 1h, and 4h
- authenticated take-profit fill events for idempotent Ministral stop protection
- signed order execution: REST requests or AWS Lambda execution after filter
  and explicit confidence-policy approval
