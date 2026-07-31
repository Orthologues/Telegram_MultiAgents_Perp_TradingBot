# Aster MCP

The scaffold exposes Aster Futures V3 public reads and a guarded, testnet-first
order handoff. Lambda loads the API wallet and delegates EIP-712 signing and
`POST /fapi/v3/order` to the pinned official `aster-mcp` client.
