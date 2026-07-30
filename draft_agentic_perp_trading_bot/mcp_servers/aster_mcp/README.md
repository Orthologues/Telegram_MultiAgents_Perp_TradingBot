# Aster MCP

The scaffold exposes Aster Futures v1 public market reads and a guarded,
testnet-first order handoff. API-key/HMAC-SHA256 signing and
`POST /fapi/v1/order` remain inside the Secrets Manager and Lambda boundary.
