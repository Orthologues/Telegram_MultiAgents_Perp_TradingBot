# Aster MCP

The scaffold exposes Aster Futures v3 public market reads and a guarded,
testnet-first order handoff. EIP-712 signer-wallet signing and
`POST /fapi/v3/order` remain inside the Secrets Manager and Lambda boundary.
