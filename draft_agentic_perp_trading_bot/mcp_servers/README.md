# MCP Servers

This folder contains exchange-specific MCP servers that back the scaffolded exchange gateway.

- `bitmart_mcp/`: existing BitMart Futures v2 Streamable HTTP MCP boilerplate.
- `bitget_mcp/`: planned Bitget perpetual futures MCP server.

The intended split is:

- MCP transport: Streamable HTTP at `/mcp`
- market/account state: WebSocket workers where practical
- signed order execution: REST requests or AWS Lambda execution after filter and explicit confidence-policy approval
