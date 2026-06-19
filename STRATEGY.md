# RUMA Trading Strategy — BNB Hack Competition

> *Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)*

**Agent wallet:** set via `TWAK_AGENT_PRIVATE_KEY`  
**Competition contract:** `0x212c61b9b72c95d95bf29cf032f5e5635629aed5`  
**On-chain trade verification:** `bscscan.com/address/{wallet}`  

---

## Philosophy

Most trading agents maximize returns. RUMA maximizes **coherence** — the mathematical certainty that its reasoning is sound before it acts.

The Ψ-gate is binary: either all five cognitive planes agree the trade is valid, or the agent stays silent. Silence rate during testing: **~87%**. That is not a bug. That is the strategy.

The silence is information.

---

## Signal Sources — CoinMarketCap AI Agent Hub

RUMA reads four independent CMC data streams and converts them to plane inputs:

| CMC Endpoint | Plane | What It Measures |
|---|---|---|
| `/v2/cryptocurrency/quotes/latest` | **P (Perceptual)** | Shannon entropy of multi-token price distribution |
| `/v3/fear-and-greed/latest` | **W (World Model)** | Market anomaly: z-score of F&G vs. 30-day rolling mean |
| Social / KOL heat score | **C (Consensus)** | Independent social signal, separated from price |
| `/v3/fear-and-greed/historical` | **W** + backtest | 30-day F&G trend for strategy backtesting |
| MCP premium stream (x402) | **P + C** | Real-time enrichment during trade evaluation |

All four streams are pulled live — no hardcoded prices, no mocked data.

---

## TRION Evaluation — The 5-Plane Ψ Gate

```
Ψ(t) = 0.25·P(t) + 0.30·I(t) + 0.20·C(t) + 0.15·S(t) + 0.10·W(t)
```

### P — Perceptual Plane (weight: 0.25)
**What:** CMC price entropy signal.  
**How:** Shannon entropy computed across the BEP-20 price distribution. Low entropy (prices moving together) = high signal quality.  
**Hard zero:** never (graduated signal).

### I — Inferential Plane (weight: 0.30)
**What:** 5 parallel LLM reasoning chains evaluate the same trade.  
**How:** Claude runs 5 independent chains. If any two contradict each other → I(t) = 0.0 → gate closes.  
**Hard zero:** contradiction detected. This is the strongest veto in TRION.

### C — Consensus Plane (weight: 0.20)
**What:** CMC social sentiment / KOL heat as an independent signal.  
**How:** Normalised social score, compared against price trend. Divergence → mean-reversion signal. Alignment → trend confirmation.  
**Hard zero:** never (graduated signal).

### S — Self-Reflection Plane (weight: 0.15)
**What:** FAISS memory density — has RUMA seen this pattern before?  
**How:** Current market state is vectorised and queried against RUMA's FAISS index. High memory density = familiar pattern = higher confidence.  
**Hard zero:** never (graduated signal).

### W — World Model Plane (weight: 0.10)
**What:** CMC Fear & Greed anomaly detection.  
**How:** Rolling z-score of F&G vs. 30-day mean. If |z| > 3σ → market is behaving unusually → W(t) = 0.0 → gate closes.  
**Hard zero:** Fear & Greed z-score > 3σ. Protects against regime-change trades.

### Gate Threshold
- General actions: Ψ ≥ Δ(t) (adaptive)
- **Trade gate**: Ψ ≥ 1.25·Δ(t) — 25% higher bar required for any swap

---

## Execution — Trust Wallet Agent Kit

1. **Pre-trade checks** (all must pass):
   - Symbol in 149-token competition allowlist
   - Drawdown < 30% (hard disqualification guard)
   - Daily P&L > -6% (daily loss pause)
   - Position size ≤ 2% of vault (Bayesian Kelly cap)
   - Ψ ≥ 1.25·Δ (gate open)

2. **Sizing** — Bayesian Kelly with 25% fractional reduction:
   ```
   p_win = 0.5 + Ψ_excess × 0.3      (confidence → win probability)
   f*    = (p_win × R:R - p_loss) / R:R × 0.25
   f*    = min(f*, 0.02)               (2% hard cap)
   ```

3. **Signing** — `TWAK_AGENT_PRIVATE_KEY` env var. Key never leaves the process. No custodial hand-off. No bridge.

4. **Swap** — PancakeSwap V2 Router:
   - Buy: `swapExactETHForTokens` (BNB → token)
   - Sell: `swapExactTokensForETH` (token → BNB)
   - Slippage: 0.5% max, hardcoded

5. **x402 payment** — CMC premium data paid per-request in BNB during the trade evaluation loop.

6. **On-chain recording** — Ψ score + timestamp written to BSC with each trade, creating a permanent coherence audit trail.

---

## Risk Guards Summary

| Guard | Value | Action |
|---|---|---|
| Max drawdown | 30% | TWAK signing disabled entirely |
| Daily loss limit | 6% | Trading paused until UTC 00:00 |
| Max position | 2% of vault | Kelly hard cap pre-sign |
| Non-eligible token | Allowlist check | SILENCE (not error) |
| Slippage | 0.5% max | Hardcoded in swap call |
| F&G anomaly (>3σ) | W(t) = 0.0 | Gate closes |
| I-plane contradiction | I(t) = 0.0 | Gate closes absolutely |
| Emergency stop | Manual | `POST /api/v1/competition/emergency-stop` |

---

## Competition Week Plan (June 22–28, 2026)

**Scheduler:** Runs every 4 hours. If daily quota (1 trade minimum) not met by 20:00 UTC → switches to 30-minute polling (urgency mode).

**Target symbols (by priority):**  
BNB, ETH, BTC, CAKE, XRP, SOL, ADA, DOGE, LINK, UNI, AVAX, MATIC, ATOM, DOT, NEAR

**Strategy per regime:**
| CMC Regime | Bias | Action |
|---|---|---|
| F&G > 60 + 7d > 5% | BULL | Ψ-gate evaluates LONG |
| F&G < 35 + 7d < -5% | BEAR | Ψ-gate evaluates SHORT |
| F&G z-score > 3σ | VOLATILE | Gate closed, no trade |
| SIDEWAYS | NEUTRAL | Ψ-gate evaluates, usually SILENCE |

**Capital plan:** Start with $200–500 BNB. Max exposure at any time: $10 per trade (2% of $500).

---

## On-Chain Audit Trail

Every trade produces:
- BSCScan-verifiable tx hash
- Ψ score at time of trade (in calldata or emitted event)
- Timestamp
- Symbol + direction + size

**Competition dashboard:** `GET /api/v1/competition/dashboard`  
**Emergency stop:** `POST /api/v1/competition/emergency-stop`  
**Force demo trade:** `POST /api/v1/strategy/scheduler/force-trade`

---

## Compounding Moat (Λ)

```
Λ(n+1) = Λ(n) + log(1 + Ψ_n · IQ_n · Δt_n)
```

Λ grows log-additively with every coherent cycle. It is mathematically monotonic — it never decreases. A competitor can fork the code; they start at Λ=0.01. RUMA's advantage compounds forever.

---

## Post-Hackathon Roadmap

### Months 1–2: Live Trading Vault
- Open to external capital via BSC smart contract vault
- Investors deposit BNB; agent trades with 2% max risk per trade
- Performance fee: 20% of profits, claimable on-chain
- All trades publicly verifiable via Ψ scores on BSC

### Months 3–6: Cross-Chain Expansion
- Deploy adapters for Ethereum, Base, Arbitrum
- Single TRION instance manages multi-chain portfolios
- Λ (moat) is chain-agnostic — reputation follows the agent

### Months 6–12: Agent Economy
- Other AI agents call RUMA's reasoning via x402 (0.001 BNB/call)
- Federation network: agents with Ψ ≥ threshold gain federated peer access
- RUMA becomes infrastructure, not just a trader

### Long-term: Decentralised TRION
- TRION Ψ evaluation runs in a verifiable compute environment (FHE/TEE)
- Any agent can prove cognitive alignment without revealing reasoning
- The silence protocol becomes a cross-ecosystem standard

---

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · June 2026*  
*GitHub: https://github.com/dev-analyshd/Ruma*
