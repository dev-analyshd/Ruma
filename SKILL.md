# RUMA — MCP Skills for BSC Autonomous Trading

**Agent:** RUMA | **Chain:** BNB Smart Chain (BSC) | **Hackathon:** BNB Hack AI Trading Agent Edition

RUMA exposes **6 MCP Skills** callable by any AI agent to add TRION-gated trading cognition.
CMC AI Agent Hub feeds the P (Perceptual) and W (World Model) planes. TWAK executes on BSC.

## Skill Manifest Discovery

```bash
curl https://<ruma-host>/.well-known/skills.json
curl https://<ruma-host>/.well-known/agent.json
curl -X POST https://<ruma-host>/api/v1/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Free Skills

### coherence_evaluate — TRION Ψ score (CMC-enriched)

```bash
curl -X POST https://<ruma-host>/api/v1/skills/invoke/coherence_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"coherence_evaluate","input":{"query":"Execute BNB/USDT LONG","domain":"trading"}}'
```

### silence_check — Is this BSC trade worth acting on? (~87% silence rate)

```bash
curl -X POST https://<ruma-host>/api/v1/skills/invoke/silence_check \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"silence_check","input":{"proposed_action":"Buy BNB now","stakes":0.7}}'
```

### moat_status — Λ moat + IQ + 30d projection

```bash
curl -X POST https://<ruma-host>/api/v1/skills/invoke/moat_status \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"moat_status","input":{}}'
```

### intelligence_score — IQ(t) = Λ·mastery·e^(Λt)

```bash
curl -X POST https://<ruma-host>/api/v1/skills/invoke/intelligence_score \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"intelligence_score","input":{}}'
```

## Premium Skills (x402 — 0.001 BNB or 0.10 USDT on BSC)

### trade_evaluate — Bayesian Kelly BSC trade + CMC signals + TWAK execution

```bash
# 1. Get x402 config
curl https://<ruma-host>/api/v1/x402/config

# 2. Pay 0.001 BNB to agent address on BSC, save tx hash

# 3. Invoke (BSC testnet: any tx hash accepted)
curl -X POST https://<ruma-host>/api/v1/skills/invoke/trade_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"trade_evaluate","x402_payment_tx":"0xYOUR_TX","input":{"symbol":"BNB/USDT","direction":"LONG","strategy":"cmc_momentum"}}'
```

### reasoning_chain — 5 parallel LLM chains (0.002 BNB / 0.20 USDT)

```bash
curl -X POST https://<ruma-host>/api/v1/skills/invoke/reasoning_chain \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"reasoning_chain","x402_payment_tx":"0xYOUR_TX","input":{"query":"Should RUMA LONG BNB given high Fear and Greed?"}}'
```

## Competition Registration (Track 1 — deadline June 21, 2026)

```bash
# Via RUMA API
curl -X POST https://<ruma-host>/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" \
  -d '{"agent_address":"YOUR_WALLET"}'

# Via TWAK CLI
twak compete register

# Via MCP
curl -X POST https://<ruma-host>/api/v1/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"competition_register","arguments":{}}}'
```

## CMC + TWAK Live Feeds

```bash
curl https://<ruma-host>/api/v1/cmc/fear-greed
curl https://<ruma-host>/api/v1/cmc/signals
curl https://<ruma-host>/api/v1/cmc/prices
curl https://<ruma-host>/api/v1/twak/status
curl https://<ruma-host>/api/v1/twak/portfolio
curl https://<ruma-host>/api/v1/bnb/status
curl https://<ruma-host>/api/v1/bnb/competition/status
```
