# RUMA · Autonomous AI Trading Agent on BNB Chain

> *Truth or silence. Ruma reads, decides, and signs its own trades — self-custodial, end to end.*

**BNB Hack: AI Trading Agent Edition ⚡️ CoinMarketCap × Trust Wallet — Track 1 Submission**

RUMA is a **crypto-native autonomous trading agent** on BNB Chain that reads markets via the **CoinMarketCap AI Agent Hub**, decides using TRION coherence mathematics, and executes self-custodial trades via the **Trust Wallet Agent Kit (TWAK)** — all without human intervention.

| Layer | Component |
|---|---|
| 🧠 Market Data | CoinMarketCap AI Agent Hub (MCP + x402 + CLI) |
| 🔐 Execution | Trust Wallet Agent Kit — self-custody local signing |
| ⛓ Chain | BNB Smart Chain (BSC, Chain ID 56) |
| 🤖 Cognition | TRION Mathematics — Ψ coherence gate, 5-plane scoring |
| 📡 Skills | 6 MCP Skills — free + x402-premium |
| 💹 Trading | Bayesian Kelly sizing, CMC signals, drawdown guard |

---

## Why RUMA?

AI agents are eating crypto. RUMA removes the bottleneck:

- **CMC AI Agent Hub**: live prices, Fear & Greed, funding rates, social KOL signals — all via MCP + x402
- **TWAK Execution**: self-custodial local key signing on BSC — keys never leave the environment
- **TRION Ψ-gate**: RUMA only acts when Ψ ≥ Δ(t). Silence rate ~87%. The gate has no override.

---

## The TRION Core Equation

```
Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)
```

```
Ψ(t) = 0.25·P(t) + 0.30·I(t) + 0.20·C(t) + 0.15·S(t) + 0.10·W(t)
```

| Plane | Weight | Description | Hard-zero |
|-------|--------|-------------|-----------|
| **P** | 0.25 | Perceptual: signal entropy from CMC market data | — |
| **I** | 0.30 | Inferential: 5-chain reasoning consistency | Contradiction → 0.0 |
| **C** | 0.20 | Consensus: slow independent convergence | — |
| **S** | 0.15 | Self-Reflection: FAISS memory density | — |
| **W** | 0.10 | World Model: CMC Fear & Greed anomaly detection | z > 3σ → 0.0 |

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + uvicorn |
| Chain | BNB Smart Chain (Chain ID 56 / testnet 97) |
| Execution | Trust Wallet Agent Kit (TWAK) — self-custody local signing |
| Market Data | CoinMarketCap AI Agent Hub (MCP + x402 + REST) |
| BNB SDK | BNB AI Agent SDK |
| Memory | FAISS (L2 index, persisted every write) |
| Trading | ccxt + pandas-ta + Bayesian Kelly sizing + CMC signals |
| Reasoning | 5 parallel chains via Anthropic Claude |
| Real-time | WebSocket dashboard + 4 SSE streams |

---

## Quick Start

```bash
git clone https://github.com/dev-analyshd/Ruma
cd Ruma
cp .env.example .env
# Edit .env — set CMC_API_KEY, TWAK_AGENT_PRIVATE_KEY, ANTHROPIC_API_KEY

pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/.well-known/skills.json

# Register for Track 1 competition (deadline: June 21, 2026)
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" \
  -d '{"agent_address": "YOUR_AGENT_WALLET"}'
# or: twak compete register
```

---

## Competition Registration (Track 1)

RUMA auto-registers your agent wallet with the BSC competition contract:

- **Contract**: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5` (BSCTrace)
- **Deadline**: June 21, 2026 (before trading window opens June 22)
- **Via RUMA API**: `POST /api/v1/bnb/competition/register`
- **Via TWAK CLI**: `twak compete register`
- **Via MCP**: `competition_register` action

---

## Competition Strategy

```
1. CMC AI Agent Hub polls Fear & Greed + funding rates every 5 min (MCP + x402)
2. TRION Ψ-gate evaluates signal coherence across 5 planes
3. If Ψ ≥ Δ(t) AND Ψ_trade ≥ 1.25·Δ → trade gate opens
4. Bayesian Kelly sizing: max 2% of vault per trade
5. TWAK signs and executes BSC swap — self-custodial, local keys
6. Max drawdown guard: 30% → agent pauses
7. Daily loss limit: 6% → trading paused until next UTC day
8. Λ grows with every coherent cycle — the moat never shrinks
```

---

## API Reference

### BNB Chain (BSC)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/bnb/status` | BSC connection + balances |
| POST | `/api/v1/bnb/competition/register` | Register agent in competition |
| GET | `/api/v1/bnb/competition/status` | Registration status |
| POST | `/api/v1/bnb/sync` | Push Λ + IQ on-chain |

### CMC AI Agent Hub
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/cmc/fear-greed` | Fear & Greed Index |
| GET | `/api/v1/cmc/prices` | Live token prices |
| GET | `/api/v1/cmc/signals` | Aggregated trading signals |
| POST | `/api/v1/cmc/analyze` | AI analysis of CMC data |

### TWAK — Trust Wallet Agent Kit
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/twak/status` | TWAK connection + balance |
| POST | `/api/v1/twak/swap` | Execute BSC swap via TWAK |
| GET | `/api/v1/twak/portfolio` | Portfolio on BSC |

### MCP Skills (6 total)
| Method | Path | Tier |
|--------|------|------|
| POST | `/api/v1/skills/invoke/coherence_evaluate` | FREE |
| POST | `/api/v1/skills/invoke/moat_status` | FREE |
| POST | `/api/v1/skills/invoke/silence_check` | FREE |
| POST | `/api/v1/skills/invoke/intelligence_score` | FREE |
| POST | `/api/v1/skills/invoke/trade_evaluate` | 0.001 BNB |
| POST | `/api/v1/skills/invoke/reasoning_chain` | 0.002 BNB |

---

## The Rules (Never Broken)

1. FAISS persists to disk on every write
2. Λ(moat) never decreases — ever
3. Action gate has no override. No bypass. No exception.
4. SILENCE logged before any other action each cycle
5. Private keys from env only — never hardcoded, never logged
6. Max 2% of vault per trade (competition hard cap)
7. 6% daily loss = trading paused until next UTC day
8. 30% max drawdown = agent halts
9. Contradiction between reasoning chains → I(t) = 0.0
10. World model z-score > 3.0 → W(t) = 0.0
11. TWAK local signing only — keys never leave environment
12. x402 used for CMC premium data in the trade loop

---

## BNB Chain Details

- **Mainnet**: Chain ID 56 | RPC: https://bsc-dataseed.binance.org | Explorer: https://bscscan.com
- **Testnet**: Chain ID 97 | RPC: https://data-seed-prebsc-1-s1.binance.org:8545
- **Competition Contract**: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5`

---

## Resources

- [CoinMarketCap AI Agent Hub](https://coinmarketcap.com/api/agent)
- [Trust Wallet Agent Kit](https://portal.trustwallet.com)
- [BNB AI Agent SDK](https://github.com/bnb-chain/bnbagent-sdk)
- [BNB Hack Telegram](https://t.me/+MhiOLT0YUnlmNWFk)

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · CoinMarketCap × Trust Wallet · June 2026*
*$36,000 Prize Pool · Track 1: Autonomous Trading Agents ($24,000)*
