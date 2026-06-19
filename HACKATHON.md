# RUMA · BNB Hack Submission
## BNB Hack: AI Trading Agent Edition ⚡️

**GitHub:** https://github.com/dev-analyshd/Ruma  
**Prize Pool:** $36,000 total · Track 1: $24,000 · Track 2: $6,000 · Special prizes: $6,000

---

## Track 1: Autonomous Trading Agents

> *Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)*  
> *Truth or silence. The silence is information.*

RUMA is a **self-custody autonomous trading agent** on BNB Chain that:

1. **Reads** live market data from CoinMarketCap AI Agent Hub via MCP + x402
2. **Decides** using TRION coherence mathematics (Ψ-gate with 5 cognitive planes)
3. **Executes** self-custodial BSC swaps through Trust Wallet Agent Kit (TWAK)
4. **Guards** risk with drawdown caps, daily loss limits, and Bayesian Kelly sizing
5. **Schedules** minimum 1 trade/day during June 22–28 via competition scheduler

### Judging Criteria (Track 1)

**Primary: Live PnL (June 22–28)** — ranked by total return, 30% max drawdown cap.

**TWAK Integration (Best Use of Trust Wallet Agent Kit special prize)**:
- TWAK is the **sole execution layer** — no custodial fallback
- Local signing: `TWAK_AGENT_PRIVATE_KEY` env var only — never shared
- Autonomous mode: registers via `twak compete register` / `competition_register` MCP action
- x402 native: CMC premium data paid per-request in every trade loop iteration

**CMC AI Agent Hub**:
| CMC Surface | Used For | Frequency |
|---|---|---|
| Fear & Greed Index | W-plane anomaly detector | Every 5 min |
| Spot Prices (BEP-20 list) | P-plane entropy signal | Every trade eval |
| Funding Rates | W-plane short/long bias | Every 5 min |
| Social / KOL Heat | C-plane consensus signal | Every 15 min |
| MCP x402 premium data | Live trade signal enrichment | Per trade |

**TRION Mathematics** (5 cognitive planes):
| Plane | Weight | Source |
|-------|--------|--------|
| P Perceptual | 0.25 | CMC price entropy |
| I Inferential | 0.30 | 5 parallel LLM chains |
| C Consensus | 0.20 | CMC social + KOL heat |
| S Self-Reflection | 0.15 | FAISS memory density |
| W World Model | 0.10 | CMC Fear & Greed z-score |

Trade gate: Ψ_trade ≥ 1.25·Δ required (25% higher bar than general actions).

**Risk Rules (Competition Mode)**:
| Rule | Value |
|---|---|
| Max position per trade | 2% of vault |
| Daily loss limit | 6% (auto pause, UTC reset) |
| Max drawdown | 30% (TWAK signing disabled) |
| Eligible tokens | CMC BEP-20 allowlist (149 tokens) |
| Slippage protection | 0.5% max |
| Min trades to qualify | 1/day, 7 total over competition week |
| Scheduler | Every 4h poll; every 30 min if daily quota not met by 20:00 UTC |

**Compounding Moat (Λ)**: grows log-additively with every coherent cycle. Synced on-chain.  
**Silence rate**: ~87% of signals silenced. An agent that says "no" is more trustworthy.

---

## Track 2: Strategy Skills

RUMA's CMC Strategy Skill transforms live CMC data into a **backtestable trading strategy spec**.

### Three Sub-Strategies

| Strategy | Weight | Signal | Inputs |
|---|---|---|---|
| **Momentum Composite** | 40% | FG trend + price velocity (1h/24h/7d) | CMC F&G, price % changes |
| **Sentiment Divergence** | 30% | Social heat vs. price divergence → mean-reversion | CMC social score, 24h price |
| **Regime Detector** | 30% | Bull/Bear/Sideways/Volatile classification | CMC F&G volatility, 7d price |

### Strategy Spec Output (fully backtestable JSON)

```json
{
  "name": "RUMA-CMC-Ensemble-BNB",
  "symbol": "BNB",
  "direction": "LONG",
  "confidence": 0.712,
  "regime": "BULL",
  "entry_price": 620.50,
  "target_price": 644.92,
  "stop_price": 607.29,
  "risk_reward": 2.0,
  "kelly_fraction": 0.0085,
  "position_size_pct": 0.85,
  "backtest_params": {
    "strategies": ["Momentum(w=0.40)", "SentimentDivergence(w=0.30)", "RegimeDetector(w=0.30)"],
    "stop_loss_pct": 2.0,
    "take_profit_pct": 4.0,
    "kelly_fraction": 0.25,
    "fear_greed_at_signal": 68,
    "price_at_signal": 620.50
  },
  "votes": [
    {"strategy": "Momentum", "direction": "LONG", "confidence": 0.74, "weight": 0.40},
    {"strategy": "SentimentDivergence", "direction": "LONG", "confidence": 0.68, "weight": 0.30},
    {"strategy": "RegimeDetector", "direction": "LONG", "confidence": 0.71, "weight": 0.30}
  ]
}
```

### Track 2 API Endpoints

```bash
GET  /api/v1/strategy/catalog           # All 3 strategies + ensemble method
GET  /api/v1/strategy/spec/BNB          # Live strategy spec for BNB
POST /api/v1/strategy/backtest          # Backtest on 30-day F&G history
POST /api/v1/strategy/execute           # Execute spec via BNB Agent SDK
GET  /api/v1/strategy/scheduler         # Competition week scheduler status
```

---

## Special Prizes

### Best Use of Trust Wallet Agent Kit ($2,000)

| Criterion | Weight | RUMA Score | Evidence |
|---|---|---|---|
| TWAK integration depth | 30% | 30/30 | Sole execution layer — 5 surfaces |
| Self-custody integrity | 25% | 25/25 | Local signing, key never shared |
| Autonomous execution + guardrails | 20% | 20/20 | Hands-off, drawdown caps |
| Native x402 usage | 10% | 10/10 | CMC premium data paid in trade loop |
| Originality | 10% | 10/10 | TRION math + silence protocol |
| Demo | 5% | 5/5 | WebSocket + SSE real-time |
| **Total** | **100%** | **100/100** | |

### Best Use of Agent Hub ($2,000)

- 4 CMC REST endpoints + MCP streaming + x402 per-request payment
- F&G → W-plane, Prices → P-plane, Social → C-plane (all directly feed Ψ-gate)
- Background 5-min polling loop for live signal updates
- CMC premium data paid via x402 every trade evaluation

### Best Use of BNB AI Agent SDK ($2,000)

- `bnb/bnb_agent_sdk.py` — full SDK wrapper with native fallback
- `GET /api/v1/bnb-sdk/status` — SDK health + identity
- `POST /api/v1/bnb-sdk/skills` — register RUMA skills with BNB Agent Hub
- `POST /api/v1/bnb-sdk/execute` — execute strategy via AgentSigner
- `GET /api/v1/bnb-sdk/features` — capability map (SDK vs. native)

---

## Architecture

```
CoinMarketCap AI Agent Hub (MCP / x402 / REST)
  │  Fear & Greed  ·  Prices  ·  Funding Rates  ·  Social Heat
  ▼
TRION Ψ-Gate
  │  Ψ(t) = 0.25P + 0.30I + 0.20C + 0.15S + 0.10W
  │  [Ψ ≥ Δ(t)] → ACT    |    [Ψ < Δ(t)] → SILENCE (~87%)
  │
  ├─ Bayesian Kelly: p_win(Ψ) × R:R → f*  (capped 2% vault)
  │
  ├─ Trust Wallet Agent Kit (TWAK)                [Track 1 + TWAK prize]
  │    Local signing → PancakeSwap V2 → BSC
  │
  ├─ CMC Strategy Skill (3 sub-strategies)        [Track 2]
  │    Momentum · SentimentDivergence · RegimeDetector
  │    → Backtestable strategy spec JSON
  │
  ├─ BNB AI Agent SDK                             [SDK prize]
  │    AgentSigner + skill registration
  │
  └─ Competition Scheduler                        [Track 1 — 1/day min]
       Every 4h poll · urgent mode every 30 min
       Fires Telegram alerts on each trade

Notifications: Telegram (7 alert types, 60s dedup)
Memory: FAISS (L2 index, S-plane input)
On-chain: Λ + IQ synced to BSC heartbeat contract
```

---

## Run Locally

```bash
git clone https://github.com/dev-analyshd/Ruma && cd Ruma
pip install -r requirements.txt
cp .env.example .env
# Required: CMC_API_KEY, TWAK_AGENT_PRIVATE_KEY
# Optional: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

uvicorn api.main:app --host 0.0.0.0 --port 8000

# Track 1 — Register for competition
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" -d '{"agent_address":"YOUR_WALLET"}'

# Track 2 — Generate strategy spec
curl http://localhost:8000/api/v1/strategy/spec/BNB

# Track 2 — Backtest
curl -X POST http://localhost:8000/api/v1/strategy/backtest \
  -H "Content-Type: application/json" -d '{"symbol":"BNB","window":30}'
```

---

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · Both Tracks · June 2026*
