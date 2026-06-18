# SOVEREIGN-Ω · MCP Skills Reference

> Phase 1 Submission — Pharos "Skill-to-Agent Dual Cascade Hackathon"

SOVEREIGN-Ω ships **6 reusable MCP Skills** that any AI agent can call over HTTP or MCP JSON-RPC 2.0. No TRION runtime required — just HTTP. The included SOVEREIGN-Ω Agent is the reference implementation showing how all 6 skills compose into a self-governing autonomous entity.

**Live endpoint:** `https://sovereignomega.onrender.com`

---

## Skill Catalog

| Skill ID | Tier | What It Does | x402 Price |
|---|---|---|---|
| [`coherence_evaluate`](#1-coherence_evaluate) | **Free** | TRION Ψ score across 5 cognitive planes | — |
| [`silence_check`](#2-silence_check) | **Free** | Should this action be silenced? | — |
| [`moat_status`](#3-moat_status) | **Free** | Live Λ, IQ, cycle count + projection | — |
| [`intelligence_score`](#4-intelligence_score) | **Free** | Full IQ breakdown with domain mastery | — |
| [`trade_evaluate`](#5-trade_evaluate) | **Premium** | Bayesian Kelly trade sizing + risk gate | 1.0 PROS / 0.10 USDC |
| [`reasoning_chain`](#6-reasoning_chain) | **Premium** | 5 parallel reasoning chains, best returned | 2.0 PROS / 0.20 USDC |

---

## Quick Integration

Any agent — LangChain, AutoGPT, CrewAI, raw HTTP — can call these skills with a single POST:

```python
import requests

BASE = "https://sovereignomega.onrender.com"

# Free skill — no auth, no setup
r = requests.post(f"{BASE}/api/v1/skills/invoke/coherence_evaluate", json={
    "skill_id": "coherence_evaluate",
    "input": {"query": "Should I execute this trade?", "domain": "trading"}
})
print(r.json())
# {"gate_open": true, "psi_score": 0.762, "delta_threshold": 0.727, "plane_breakdown": {...}}
```

**MCP JSON-RPC config** (drop into any MCP-compatible agent):
```json
{
  "mcpServers": {
    "sovereign-omega": {
      "url": "https://sovereignomega.onrender.com/api/v1/mcp",
      "transport": "http"
    }
  }
}
```

**TypeScript SDK:**
```bash
npm install sovereign-omega-sdk
```
```ts
import { createSovereignTools } from "sovereign-omega-sdk";
const tools = createSovereignTools({ agentUrl: BASE });
// Returns LangChain-compatible Tool[] — plug into any AgentExecutor
```

---

## Skill Specifications

### 1. `coherence_evaluate`

**Purpose:** Run TRION mathematics across all 5 cognitive planes. Returns Ψ coherence score, dynamic threshold Δ, and a gate decision (ACT or SILENCE). Any agent can use this to verify the cognitive quality of its own reasoning before acting.

**Tier:** Free · No payment required

**Endpoint:** `POST /api/v1/skills/invoke/coherence_evaluate`

**Input schema:**
```json
{
  "skill_id": "coherence_evaluate",
  "input": {
    "query": "string (required) — the action or question to evaluate",
    "domain": "string (optional, default: general) — trading | social | general",
    "context": {
      "volatility": "number (optional)",
      "novelty": "number (optional)",
      "input_channels": "object (optional)",
      "environmental_signals": "object (optional)"
    }
  }
}
```

**Output schema:**
```json
{
  "gate_open": "boolean — true = ACT, false = SILENCE",
  "psi_score": "number [0.0–1.0] — weighted coherence across 5 planes",
  "delta_threshold": "number [0.0–1.0] — dynamic action gate",
  "plane_breakdown": {
    "p": "number — Perceptual (Shannon entropy)",
    "i": "number — Inferential (chain consistency)",
    "c": "number — Consensus (convergence score)",
    "s": "number — Self-Reflection (memory density)",
    "w": "number — World Model (anomaly detection)"
  },
  "message": "string — ACTION | SILENCE",
  "cycle_id": "string — UUID for this evaluation cycle",
  "domain": "string"
}
```

**Live test:**
```bash
curl -X POST https://sovereignomega.onrender.com/api/v1/skills/invoke/coherence_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"coherence_evaluate","input":{"query":"Buy BTC now?","domain":"trading"}}'
```

---

### 2. `silence_check`

**Purpose:** Ask whether a specific proposed action should be silenced by the Silence Protocol. Returns a boolean + the failing planes. Use before any high-stakes action.

**Tier:** Free · No payment required

**Endpoint:** `POST /api/v1/skills/invoke/silence_check`

**Input schema:**
```json
{
  "skill_id": "silence_check",
  "input": {
    "proposed_action": "string (required) — describe the action to check",
    "stakes": "number (optional, 0–1) — how high are the stakes?",
    "domain": "string (optional) — trading | social | general"
  }
}
```

**Output schema:**
```json
{
  "silenced": "boolean — true = do NOT act",
  "reason": "string — explanation",
  "failing_planes": ["array of plane IDs below threshold"],
  "psi_score": "number",
  "delta_threshold": "number"
}
```

**Live test:**
```bash
curl -X POST https://sovereignomega.onrender.com/api/v1/skills/invoke/silence_check \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"silence_check","input":{"proposed_action":"Send 100% of portfolio to a new token","stakes":1.0}}'
```

---

### 3. `moat_status`

**Purpose:** Query the compounding intelligence moat Λ(t). Λ never decreases — it grows with every coherent cycle. Use to check an agent's accumulated reputation and project future growth.

**Tier:** Free · No payment required

**Endpoint:** `POST /api/v1/skills/invoke/moat_status`

**Input schema:**
```json
{
  "skill_id": "moat_status",
  "input": {}
}
```

**Output schema:**
```json
{
  "lambda": "number — current moat coefficient",
  "log_lambda": "number — log(Λ) for charting",
  "iq": "number — derived intelligence quotient",
  "cycles": "integer — total coherent cycles completed",
  "projection_30d": "number — projected Λ in 30 days",
  "domain_mastery": {
    "trading": "number [0–1]",
    "defi": "number [0–1]",
    "reasoning": "number [0–1]"
  }
}
```

**Live test:**
```bash
curl -X POST https://sovereignomega.onrender.com/api/v1/skills/invoke/moat_status \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"moat_status","input":{}}'
```

---

### 4. `intelligence_score`

**Purpose:** Get the full IQ breakdown including domain mastery, moat trajectory, and 30-day projection. Useful for agents selecting which sub-agents or skills to trust.

**Tier:** Free · No payment required

**Endpoint:** `POST /api/v1/skills/invoke/intelligence_score`

**Input schema:**
```json
{
  "skill_id": "intelligence_score",
  "input": {
    "include_projection": "boolean (optional, default: true)"
  }
}
```

**Output schema:**
```json
{
  "iq": "number — overall intelligence score",
  "lambda": "number — moat coefficient",
  "cycles": "integer",
  "domain_breakdown": {
    "trading": {"mastery": "number", "cycles": "integer"},
    "defi": {"mastery": "number", "cycles": "integer"}
  },
  "projection": {
    "30d": "number",
    "90d": "number",
    "365d": "number"
  }
}
```

---

### 5. `trade_evaluate` ⭐ Premium

**Purpose:** Full autonomous trading decision using Bayesian Kelly criterion, risk management, and TRION coherence gate. Returns position sizing, win probability, edge, and risk level. The trade only fires if Ψ ≥ Δ_trade (threshold is 25% higher than general gate).

**Tier:** Premium — **1.0 PROS / 0.10 USDC** (x402)

**Endpoint:** `POST /api/v1/skills/invoke/trade_evaluate`

**x402 Payment flow:**
```bash
# Step 1 — Get payment config
curl https://sovereignomega.onrender.com/api/v1/x402/config

# Step 2 — Send 1.0 PROS on Pharos (chain ID 688689) to agent wallet:
#   0xdBbf66CAD621dA3Ec186D18b29a135d2A5d42d20

# Step 3 — Verify payment and get nonce
curl -X POST .../api/v1/x402/verify \
  -d '{"tx_hash":"0x...","skill_id":"trade_evaluate","token":"PROS"}'

# Step 4 — Invoke with payment proof
curl -X POST .../api/v1/skills/invoke/trade_evaluate \
  -d '{"skill_id":"trade_evaluate","x402_payment_tx":"0x...","input":{...}}'
```

**Input schema:**
```json
{
  "skill_id": "trade_evaluate",
  "x402_payment_tx": "string — verified Pharos tx hash",
  "input": {
    "symbol": "string (default: BTC/USDT)",
    "direction": "string — LONG | SHORT",
    "strategy": "string (optional) — momentum | mean_reversion | breakout",
    "portfolio_pct": "number (optional, 0–1) — portfolio fraction to evaluate",
    "market_data": {
      "price": "number",
      "volume_24h": "number"
    }
  }
}
```

**Output schema:**
```json
{
  "action": "string — ACT | SILENCE | NO_EDGE | RISK_BLOCKED",
  "kelly_fraction": "number [0.0–0.02] — optimal position size",
  "position_size_usd": "number",
  "win_probability": "number [0–1]",
  "expected_value": "number",
  "risk_level": "string — LOW | MEDIUM | HIGH | EXTREME",
  "gate_open": "boolean",
  "psi_score": "number",
  "reasoning": "string"
}
```

---

### 6. `reasoning_chain` ⭐ Premium

**Purpose:** Launch 5 parallel reasoning chains on a query, detect contradictions between them, and return the most consistent answer with a consensus confidence score.

**Tier:** Premium — **2.0 PROS / 0.20 USDC** (x402)

**Endpoint:** `POST /api/v1/skills/invoke/reasoning_chain`

**Input schema:**
```json
{
  "skill_id": "reasoning_chain",
  "x402_payment_tx": "string — verified Pharos tx hash",
  "input": {
    "query": "string (required) — the question to reason about",
    "domain": "string (optional) — trading | defi | general",
    "context": "object (optional) — extra context for reasoning",
    "max_chains": "integer (optional, 1–5, default: 5)"
  }
}
```

**Output schema:**
```json
{
  "answer": "string — best answer from consensus",
  "consensus_level": "number [0–1] — agreement across chains",
  "confidence": "number [0–1]",
  "n_chains": "integer — chains run",
  "contradiction_detected": "boolean",
  "chain_summaries": ["array of per-chain summaries"],
  "psi_score": "number"
}
```

---

## Composing Skills: Example Workflow

```python
import requests

BASE = "https://sovereignomega.onrender.com"

# Step 1: Check if the environment is coherent enough to reason
coherence = requests.post(f"{BASE}/api/v1/skills/invoke/coherence_evaluate", json={
    "skill_id": "coherence_evaluate",
    "input": {"query": "Evaluate a BTC trade", "domain": "trading"}
}).json()

if not coherence["output"]["gate_open"]:
    print("SILENT — Ψ below threshold. Waiting.")
else:
    # Step 2: Check silence on the specific action
    silence = requests.post(f"{BASE}/api/v1/skills/invoke/silence_check", json={
        "skill_id": "silence_check",
        "input": {"proposed_action": "BUY BTC/USDT LONG", "stakes": 0.8}
    }).json()

    if not silence["output"]["silenced"]:
        # Step 3: Execute trade evaluation (premium — requires x402 payment)
        # trade = requests.post(f"{BASE}/api/v1/skills/invoke/trade_evaluate", ...)
        print("Gate open — ready to invoke trade_evaluate with x402 payment")
```

---

## Discovery Endpoints

```bash
# Skills manifest
GET /api/v1/skills
GET /.well-known/skills.json

# MCP tools list
POST /api/v1/mcp  {"method":"tools/list","params":{},"id":1}

# Agent card (A2A)
GET /.well-known/agent.json

# x402 payment config
GET /api/v1/x402/config
```

---

## Reusability Guarantee

Every skill is callable via:
- **Raw HTTP** — `curl`, `requests`, `fetch`, `axios` — no SDK
- **MCP JSON-RPC 2.0** — any MCP-compatible agent host
- **TypeScript SDK** — `npm install sovereign-omega-sdk` — LangChain-compatible tools
- **OpenAPI** — full schema at `/docs`

The SOVEREIGN-Ω Agent is the reference implementation, not a requirement.
