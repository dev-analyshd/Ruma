# RUMA · BNB Hack Submission
## BNB Hack: AI Trading Agent Edition ⚡️ — Track 1: Autonomous Trading Agents

> *Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)*
> *Truth or silence. The silence is information.*

**GitHub:** https://github.com/dev-analyshd/Ruma

---

## What RUMA Is

RUMA is a **self-custody autonomous trading agent** on BNB Chain that:

1. **Reads** live market data from CoinMarketCap AI Agent Hub via MCP + x402
2. **Decides** using TRION coherence mathematics (Ψ-gate with 5 cognitive planes)
3. **Executes** self-custodial BSC swaps through Trust Wallet Agent Kit (TWAK)
4. **Guards** risk with drawdown caps, daily loss limits, and Kelly position sizing

The Ψ-gate is the heart of RUMA: every trade is gated behind coherence scoring. When CMC signals contradict, reasoning chains diverge, or market anomalies exceed 3σ — the gate closes. Silence rate: ~87%.

---

## Judging Criteria

### Technical Execution (on-chain, not cosmetic)

**TWAK Integration (Best Use of Trust Wallet Agent Kit special prize)**:
- TWAK is the **sole execution layer** — no custodial fallback
- Local signing: `TWAK_AGENT_PRIVATE_KEY` env var only — never shared, never uploaded
- Autonomous mode: registers via `twak compete register` CLI / `competition_register` MCP action
- x402 native: CMC premium data (funding rates, KOL signals) paid per-request in every trade loop iteration

**CMC AI Agent Hub (Best Use of Agent Hub special prize)**:
| CMC Surface | Used For | Frequency |
|---|---|---|
| Fear & Greed Index | W-plane anomaly detector | Every 5 min |
| Spot Prices (BEP-20 list) | P-plane entropy signal | Every trade eval |
| Funding Rates | W-plane short/long bias | Every 5 min |
| Social / KOL Heat | C-plane consensus signal | Every 15 min |
| MCP x402 premium data | Live trade signal enrichment | Per trade |

**BNB Chain**:
- Chain ID 56 (mainnet) / 97 (testnet)
- Competition contract: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5`
- All trades signed locally (TWAK) and broadcast to BSC

**TRION Mathematics**:
| Plane | Weight | Source |
|-------|--------|--------|
| P Perceptual | 0.25 | CMC price entropy |
| I Inferential | 0.30 | 5 parallel Claude chains |
| C Consensus | 0.20 | CMC social + KOL heat |
| S Self-Reflection | 0.15 | FAISS memory density |
| W World Model | 0.10 | CMC Fear & Greed z-score |

Trade gate: Ψ_trade ≥ 1.25·Δ required (25% higher bar than general actions)

### Originality

**TRION Mathematics** — novel 5-plane cognitive framework where the W-plane reads CMC Fear & Greed and flags anomalies via z-score. When the index moves > 3σ from its rolling mean, W(t) = 0.0 and the trade gate closes immediately.

**Silence Protocol applied to trading**: RUMA silences ~87% of all potential trade signals. An agent that says "no" 87% of the time is more trustworthy than one that trades everything. The silence is signal.

**Compounding Moat**: Λ grows log-additively with every coherent cycle — permanently accumulating trading intelligence, synced on-chain.

### Real-World Relevance

A self-custody user who wants automated BSC trading without giving up their keys:
- Keys never leave the environment (TWAK local signing)
- 30% drawdown cap, 6% daily limit, 2% max position — TWAK signing disabled if breached
- The agent a self-custody user would actually let run unattended

### Demo (Competition Week June 22–28, 2026)

- `GET /api/v1/bnb/competition/status` — on-chain registration proof
- `GET /api/v1/twak/portfolio` — live portfolio with BSCScan links
- `GET /api/v1/cmc/signals` — CMC signal feed driving decisions
- `/dashboard` — real-time WebSocket (Ψ chart, Λ curve, gate feed, trades)

---

## TWAK Integration Depth

| Criterion | RUMA Implementation |
|---|---|
| Sole execution layer | All BSC swaps through TWAK signing. No custodial fallback. |
| Self-custody integrity | Local signing every trade — TWAK_AGENT_PRIVATE_KEY env only |
| Autonomous mode | competition_register MCP action + twak compete register CLI |
| x402 native usage | CMC funding rate + KOL signals paid per-request in trade loop |
| Guardrails | 30% drawdown → TWAK signing disabled; 2% max position pre-sign |

---

## Architecture

```
CMC AI Agent Hub (MCP / x402)
  │ Fear & Greed · Prices · Funding Rates · Social Heat
  ▼
TRION Ψ-Gate
  │ Ψ(t) = 0.25P + 0.30I + 0.20C + 0.15S + 0.10W
  │ Gate: Ψ ≥ Δ(t) → ACT  |  Ψ < Δ → SILENCE (~87%)
  ├─ Bayesian Kelly: p_win(Ψ) × R:R → f* (capped 2% vault)
  └─ TWAK Execution
      Local signing → BSC swap broadcast
      Competition contract: 0x212c61b9b72c95d95bf29cf032f5e5635629aed5
```

---

## Risk Rules (Competition Mode)

| Rule | Value |
|---|---|
| Max position per trade | 2% of vault |
| Daily loss limit | 6% (auto pause, UTC reset) |
| Max drawdown | 30% (TWAK signing disabled) |
| Eligible tokens | CMC BEP-20 allowlist (149 tokens) |
| Slippage protection | 0.5% max (hardcoded in TWAK swap calls) |
| Min trades to qualify | 1/day, 7 total over competition week |

---

## Run Locally

```bash
git clone https://github.com/dev-analyshd/Ruma
pip install -r requirements.txt
cp .env.example .env
# Required: CMC_API_KEY, TWAK_AGENT_PRIVATE_KEY

uvicorn api.main:app --host 0.0.0.0 --port 8000

curl http://localhost:8000/api/v1/cmc/fear-greed
curl http://localhost:8000/api/v1/twak/status
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" \
  -d '{"agent_address":"YOUR_WALLET"}'
```

---

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · Track 1 · June 2026*
*$36,000 Prize Pool · Track 1: $24,000 · Special prizes: $6,000*
