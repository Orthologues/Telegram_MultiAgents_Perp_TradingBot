# Bitget MCP Server

The preliminary server exposes Bitget v2 futures ticker, price, and candle
reads plus a guarded, unsigned order handoff. API-key signing and HTTPS order
submission remain in the Secrets Manager and Lambda boundary.

Current and planned responsibilities:

- Streamable HTTP MCP endpoint
- Bitget WebSocket market/account state adapters
- typed market cap, volume, and 5m/15m/1h/4h KDJ, Bollinger, and ATR snapshots
  for Ministral
- narrow public read tools for ticker, price, and candles
- guarded approved-order handoff
- Lambda REST signing for final order execution
