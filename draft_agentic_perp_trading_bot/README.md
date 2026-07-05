# Agentic Perp Trading Bot Draft Scaffold

This draft scaffold was generated from the FigJam flowchart:

- Figma file key: `IosVAXW713NeWhTTU962vC`
- Section: `Diagram`
- Purpose: convert Chinese Telegram trading signals into validated, weighted, risk-checked perpetual futures execution requests.

The scaffold is intentionally non-executing. It defines project boundaries, schemas, and module placeholders for later implementation.

## Install

This draft project uses `uv` to manage one Python environment for the whole scaffold, including the BitMart MCP server. Run all install commands from the scaffold root so dependencies are resolved into a single local `.venv`.

Create the full development environment:

```bash
cd draft_agentic_perp_trading_bot
uv sync --extra aws --extra dev
```

For runtime-only work without AWS/dev extras:

```bash
cd draft_agentic_perp_trading_bot
uv sync
```

Then either activate the environment:

```bash
source .venv/bin/activate
```

or run commands through `uv`:

```bash
uv run python -m pytest
```

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

The BitMart MCP dependencies are now declared in the root `pyproject.toml`; the nested BitMart MCP project metadata was removed to keep a single Python environment.

## Safety Boundary

QWEN agents only produce JSON hypotheses. The Ministral filter validates and scores them. Deterministic code computes position size and risk approval. AWS Lambda performs signed order execution only after an approved execution request exists.
