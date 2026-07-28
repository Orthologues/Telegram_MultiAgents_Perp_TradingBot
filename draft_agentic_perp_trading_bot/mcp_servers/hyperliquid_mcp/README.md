# Hyperliquid MCP

The preliminary server exposes Hyperliquid `/info` reads and a guarded,
unsigned order handoff. API-wallet signing and HTTPS `/exchange` submission
remain in the Secrets Manager and Lambda boundary. Its pending market-analysis
adapter must derive typed liquidity plus 5m/15m/1h/4h KDJ, Bollinger, and ATR
snapshots for Ministral.
