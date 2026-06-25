## Blueprint of the trading bot I (empowered by Codex GPT-5.5)

### Telegram Chinese Text/Images

<span style="font-size: 32px;">⇅</span>

### QWEN3-VL Agents
OCR / chart interpretation
News/sentiment extraction
Produce JSON trade hypotheses only

<span style="font-size: 32px;">⇅</span>

### Ministral3-8B/14B Validation Agent
Validates schema
Compares QWEN outputs
Rejects prompt-injected content
Produces normalized TradeIntent

<span style="font-size: 32px;">⇅</span>

### Deterministic Risk/Policy Engine
Max size
Leverage cap
Symbol allowlist
Cooldowns
Position conflict checks

<span style="font-size: 32px;">⇅</span>

### Remote MCP Server: https://your-domain/mcp
BitMart Futures v2 tools
Market/account/order/cancel tools

<span style="font-size: 32px;">⇅</span>

### BitMart Futures v2 API

<div style="height: 32px;"></div>


## Blueprint of the trading bot II (in Figma flowchart)
TODO: ...