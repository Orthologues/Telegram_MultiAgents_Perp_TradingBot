# Agentic Perp Trading Bot Draft Scaffold

This draft scaffold was generated from the FigJam flowchart:

- Figma file key: `IosVAXW713NeWhTTU962vC`
- Section: `Diagram`
- Purpose: convert Chinese Telegram trading signals into validated, weighted, risk-checked perpetual futures execution requests.

The scaffold is intentionally non-executing. It defines project boundaries, schemas, and module placeholders for later implementation.

## Architecture Layers

1. Telegram trading signal source layer
2. Telegram ingestion layer
3. Owner-specific QWEN3-VL multimodal agents
4. Ministral3-8B/14B filter agent
5. Performance and weight engine
6. Deterministic risk engine
7. BitMart/Bitget MCP exchange gateway
8. AWS Secrets Manager and Lambda execution layer

## Included MCP Server Drafts

- `mcp_servers/bitmart_mcp/`: moved from the original repository-level `bitmart_mcp/` folder.
- `mcp_servers/bitget_mcp/`: planned placeholder for a future Bitget MCP server.

## Safety Boundary

QWEN agents only produce JSON hypotheses. The Ministral filter validates and scores them. Deterministic code computes position size and risk approval. AWS Lambda performs signed order execution only after an approved execution request exists.
