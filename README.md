# RUMA · Autonomous AI Trading Agent on BNB Chain

> *Truth or silence. Ruma reads, decides, and signs its own trades — self-custodial, end to end.*

**BNB Hack: AI Trading Agent Edition ⚡️ CoinMarketCap × Trust Wallet**
**Track 1 ($24K) · Track 2 ($6K) · Special Prizes · Deadline: June 21, 2026 13:00 UTC**

RUMA is a **crypto-native autonomous trading agent** on BNB Chain that reads markets via the **CoinMarketCap AI Agent Hub**, decides using **TRION coherence mathematics + ADAPT-Ω strategy registry**, and executes self-custodial trades via the **Trust Wallet Agent Kit (TWAK)** — all without human intervention.

| Layer | Component |
|---|---|
| 🧠 Market Data | CoinMarketCap AI Agent Hub (MCP + x402 + CLI) |
| 🔐 Execution | Trust Wallet Agent Kit — self-custody local signing |
| ⛓ Chain | BNB Smart Chain (BSC, Chain ID 56) |
| 🤖 Cognition | TRION Mathematics — Ψ coherence gate, 5-plane scoring |
| 🎯 Strategy | ADAPT-Ω Registry — 10 self-calibrating strategies |
| 📡 Skills | 6 MCP Skills — free + x402-premium |
| 💹 Trading | Bayesian Kelly sizing, CMC signals, drawdown guard |

---

## Why RUMA?

AI agents are eating crypto. RUMA removes the bottleneck:

- **CMC AI Agent Hub**: live prices, Fear & Greed, funding rates, social KOL signals — all via MCP + x402
- **TWAK Execution**: self-custodial local key signing on BSC — keys never leave the environment
- **TRION Ψ-gate**: RUMA only acts when Ψ ≥ Δ(t). Silence rate ~87%. The gate has no override.
- **ADAPT-Ω**: 10 strategies compete for every cycle; only the highest edge-scorer trades

---

## The TRION Core Equation

```
Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)
```

```
Ψ(t) = 0.25·P(t) + 0.30·I(t) + 0.20·C(t) + 0.15·S(t) + 0.10·W(t)
```

| Plane | Weight | Description | Hard-zero condition |
|-------|--------|-------------|---------------------|
| **P** | 0.25 | Perceptual: signal entropy from CMC market data | — |
| **I** | 0.30 | Inferential: 5-chain reasoning consistency | Contradiction → 0.0 |
| **C** | 0.20 | Consensus: slow independent convergence | — |
| **S** | 0.15 | Self-Reflection: FAISS memory density | — |
| **W** | 0.10 | World Model: CMC Fear & Greed anomaly detection | z > 3σ → 0.0 |

### Dynamic Threshold Δ(t)

```
Δ(t) = BASE · (1 + β·fg_norm) · (1 - γ·λ_norm) · day_factor
```

- `BASE = 0.57` — empirically calibrated floor (commit 9 fix: was 0.60)
- `β = 0.20` — Fear & Greed sensitivity
- `γ = 0.15` — moat bonus (higher Λ → lower gate → more confident trading)
- `day_factor` — rises with fewer competition days remaining
- At `fg=70, Λ=0.01`: Δ≈0.599, gate opens when Ψ≥0.599

### Adaptation Plane A(t)

```
A(t) = κ(t) · session_weight(hour) · regime_weight · volume_weight
```

- **κ(t)**: calibration score, updated after every trade (online learning)
- **session_weight**: UTC peak hours 13–21 weighted 2× dead hours 1–6
- **SESSION_LIQUIDITY** sums exactly to 1.000 (fixed in commit 9)
- At UTC 15: A≈0.550; at UTC 03: A≈0.079

---

## ADAPT-Ω — 10 Self-Calibrating Strategies

Every trading cycle, all 10 strategies are scored. Only the one with the highest `expected_edge = opportunity_score × Ψ × A(t)` fires — if it clears the edge threshold of 0.22.

| Ψ req | Strategy | Signal type | Direction |
|-------|----------|-------------|-----------|
| 0.80 | `cross_exchange_basis` | BSC DEX vs CEX price gap ≥ 0.3% | NEUTRAL (arb) |
| 0.75 | `onchain_flow` | Exchange outflow z-score + whale accumulation | LONG |
| 0.75 | `momentum_surge` | ADX > 25 + RSI 55–75 + volume spike | LONG |
| 0.72 | `liquidity_sweep` | Stop-hunt reversal + volume spike detection | SHORT |
| 0.70 | `funding_rate_arb` | |funding| > 0.05%/8h cycle exploitation | SHORT/LONG |
| 0.70 | `black_swan_insurance` | W(t) < 0.5 tail-risk hedge | HEDGE |
| 0.70 | `volatility_regime_switch` | Realised vs implied vol divergence | SHORT |
| 0.68 | `sentiment_divergence` | Social sentiment vs price gap ≥ 10% | LONG |
| 0.65 | `mean_reversion_fear` | F&G < 25 + negative funding + oversold RSI | LONG |
| 0.50 | `lambda_dca` | Moat-scaled DCA, active at any coherence level | LONG |

**Online learning**: `record_outcome()` updates `EFFECTIVENESS_MATRIX` + κ(t) after every trade. RUMA gets smarter each cycle.

**Edge threshold = 0.22**: calibrated so at Ψ=0.742, A=0.550, `funding_rate_arb` (opp=0.652) yields edge=0.266 → trades. At Ψ=0.40, A=0.12, max edge ≈ 0.044 → SILENCE.

---

## Competition Strategy (Track 1 — June 22–28)

```
1. CMC AI Agent Hub polls Fear & Greed + funding rates every 5 min (MCP + x402)
2. TRION Ψ-gate evaluates signal coherence across 5 planes
3. ADAPT-Ω registry scores all 10 strategies: edge = opp × Ψ × A(t)
4. Best strategy fires if edge > 0.22 AND Ψ ≥ strategy.psi_requirement
5. Bayesian Kelly sizing: max 2% of vault per trade (competition hard cap)
6. TWAK signs and executes BSC swap — self-custodial, local keys
7. record_outcome() feeds the on-chain learning loop after every close
8. Max drawdown guard: 30% → agent pauses
9. Daily loss limit: 6% → trading paused until next UTC day
10. Λ grows with every coherent cycle — the moat never shrinks
```

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
| Trading | ccxt + pandas-ta + Bayesian Kelly + 10 ADAPT-Ω strategies |
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
curl http://localhost:8000/api/v1/trading/strategies?psi=0.75

# Register for Track 1 competition (deadline: June 21, 2026)
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" \
  -d '{"agent_address": "YOUR_AGENT_WALLET"}'
```

---

## Competition Registration (Track 1)

RUMA auto-registers your agent wallet with the BSC competition contract:

- **Contract**: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5` (BSCTrace)
- **Deadline**: June 21, 2026 13:00 UTC (before trading window opens June 22)
- **Via RUMA API**: `POST /api/v1/bnb/competition/register`
- **Via TWAK CLI**: `twak compete register`

---

## Full API Reference

### Dynamic Trading Engine (ADAPT-Ω)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/trading/strategies` | All 10 strategies ranked by `expected_edge = opp×Ψ×A(t)` |
| GET | `/api/v1/trading/strategies/{name}` | Single strategy signal (live CMC context) |
| POST | `/api/v1/trading/strategies/outcome` | Record trade outcome → on-chain learning loop |
| GET | `/api/v1/trading/strategies/performance` | Per-strategy win rates + P&L from recorded outcomes |
| GET | `/api/v1/trading/pipeline` | Full pipeline: opportunities → strategy → size → risk |
| GET | `/api/v1/trading/sizer` | Dynamic position size (Bayesian Kelly) |
| GET | `/api/v1/trading/risk` | Current dynamic risk limits + circuit breakers |
| GET | `/api/v1/trading/threshold` | Current Δ(t) gate value |
| GET | `/api/v1/trading/strategy` | Selected strategy for current CMC regime |
| GET | `/api/v1/trading/opportunities` | Top 5 asset opportunities (live CMC scan) |

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
| POST | `/api/v1/skills/invoke/trade_evaluate` | 0.001 BNB (x402) |
| POST | `/api/v1/skills/invoke/reasoning_chain` | 0.002 BNB (x402) |

### Competition Dashboard (Judges)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/competition/dashboard` | Live PnL, drawdown %, trades, Ψ history, all tx hashes |
| GET | `/api/v1/competition/proof` | On-chain proof — agent address, registration tx, BscScan links |
| GET | `/api/v1/competition/rank` | Registration status on competition contract |
| POST | `/api/v1/competition/emergency-stop` | Manual kill switch (disables all TWAK signing) |
| GET | `/api/v1/strategy/catalog` | Track 2: all 10 ADAPT-Ω strategies documented |
| GET | `/api/v1/docs` | Full Swagger UI — all endpoints |

---

## The Rules (Never Broken)

1. FAISS persists to disk on every write
2. Λ (moat) never decreases — ever
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
13. ADAPT-Ω edge threshold = 0.22 — no strategy fires below this
14. Ψ requirement per strategy — cross_exchange_basis needs Ψ ≥ 0.80, lambda_dca accepts Ψ ≥ 0.50

---

## Test Suite — 28/28 PASSED

All fixes and new modules are covered by an automated regression suite:

```
Section A — Core regression (18 tests)
  ✓ SESSION_LIQUIDITY sums to 1.000
  ✓ get_eligible_symbols() — 149 BNB-eligible symbols, sorted
  ✓ httpx lazy-import guards (trading.asset_selector + cmc_strategy_skill)
  ✓ Dynamic threshold: BASE=0.57, fg=70 → Δ=0.599
  ✓ W-plane raw-ctx fallback: BULL=0.841, empty=0.45
  ✓ A-plane override_hour: dead(UTC 3)=0.079 vs peak(UTC 15)=0.550
  ✓ ActionGate: HARD_SILENCE / SOFT_SILENCE / OPEN tiers + overflow guard
  ✓ SilenceProtocol: HARD / SOFT / NONE
  ✓ MoatAccumulator: monotonic + zero-ρ guard
  ✓ DynamicPositionSizer: 6 regimes + NaN guards
  ✓ DynamicRiskManager: daily cap + FLASH_CRASH circuit breaker
  ✓ DynamicStrategySelector: regime probabilities sum to 1.0
  ✓ E2E peak-hour loop: 5/5 cycles traded, Λ 0.0100→0.0119
  ✓ Adversarial: extreme volatility, e^(Λ·t) overflow, silence cascade

Section B — ADAPT-Ω strategies (10 tests)
  ✓ All 10 strategies load with unique names
  ✓ Registry selects funding_rate_arb at Ψ=0.742, A=0.550 (edge=0.266)
  ✓ Low-Ψ (0.40) → SILENCE
  ✓ Fear scenario (F&G=12) → lambda_dca (edge=0.369)
  ✓ CRASH regime → SILENCE (all directional strategies suppressed)
  ✓ High funding (0.25%/8h) + Ψ=0.85 → funding_rate_arb edge=0.551 size=$42.48
  ✓ Online learning: record_outcome → win_rate=0.50 after 2 outcomes
  ✓ All 10 signals: opportunity_score ∈ [0,1], direction ∈ {LONG,SHORT,NEUTRAL,HEDGE}
  ✓ Strategies ordered by Ψ requirement descending: [0.80, 0.75, 0.75, 0.72, 0.70, 0.70, 0.70, 0.68, 0.65, 0.50]
  ✓ All opportunity_score() calls bounded [0,1]
```

Run locally:
```bash
python3 tests/run_all.py   # or inline: python3 -c "..."
```

---

## Commit History

| Commit | Description |
|--------|-------------|
| `ed1b63e` | feat: 10 ADAPT-Ω trading strategies + StrategyRegistry + 4 new API endpoints |
| `4025a9f` | fix: 4 bugs (SESSION_LIQUIDITY, get_eligible_symbols, httpx ×2, BASE 0.60→0.57) + W-plane raw-ctx fallback + A-plane override_hour |
| earlier | Core TRION engine, TWAK integration, CMC MCP skills, competition registration |

---

## BNB Chain Details

- **Mainnet**: Chain ID 56 | RPC: `https://bsc-dataseed.binance.org` | Explorer: `https://bscscan.com`
- **Testnet**: Chain ID 97 | RPC: `https://data-seed-prebsc-1-s1.binance.org:8545`
- **Competition Contract**: `0x212c61b9b72c95d95bf29cf032f5e5635629aed5`

---

## Beyond the Hackathon

### Months 1–2: Live Trading Vault
- Open to external capital via on-chain BSC smart contract vault
- Investors deposit BNB; RUMA trades with 2% max risk per position
- Performance fee: 20% of profits, claimable on-chain
- Every trade verifiable via Ψ scores on BSC — no black box

### Months 3–6: Cross-Chain Expansion
- TWAK adapters for Ethereum, Base, Arbitrum
- Single TRION instance manages multi-chain portfolios
- Λ (moat) is chain-agnostic — reputation follows the agent across chains

### Months 6–12: Agent Economy
- Other AI agents purchase RUMA's reasoning via x402 (0.001 BNB/call)
- Federation: agents with Ψ ≥ threshold gain federated peer access
- The agent becomes infrastructure — not just a trader, but a reasoning oracle

---

## Resources

- [CoinMarketCap AI Agent Hub](https://coinmarketcap.com/api/agent)
- [Trust Wallet Agent Kit](https://portal.trustwallet.com)
- [BNB AI Agent SDK](https://github.com/bnb-chain/bnbagent-sdk)
- [BNB Hack Telegram](https://t.me/+MhiOLT0YUnlmNWFk)
- [DoraHacks Submission](https://dorahacks.io)
- [Strategy Explanation](./STRATEGY.md)
- [Security Policy](./SECURITY.md)

---

*RUMA v2.0.0 · BNB Hack: AI Trading Agent Edition · CoinMarketCap × Trust Wallet · June 2026*
*$36,000 Prize Pool · Track 1 ($24,000) + Track 2 ($6,000) + Special Prizes ($6,000)*
*28/28 tests passing · 10 ADAPT-Ω strategies · 4 trading API endpoint groups*
