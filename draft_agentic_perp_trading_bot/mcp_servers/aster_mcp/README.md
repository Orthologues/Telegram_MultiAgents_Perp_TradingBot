# Aster MCP

The scaffold exposes Aster Futures V1 public reads and a guarded, testnet-first
order handoff. Lambda loads the API credentials, signs the request with the
API secret using HMAC-SHA256, and submits `POST /fapi/v1/order` only after the
deterministic execution gates pass.
