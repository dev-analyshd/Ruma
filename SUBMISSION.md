# RUMA — DoraHacks Submission (Both Tracks)
## BNB Hack: AI Trading Agent Edition · June 2026

---

## Project Links

| | |
|---|---|
| **Replit (live)** | https://ruma.replit.app |
| **GitHub** | https://github.com/dev-analyshd/Ruma |
| **Swagger Docs** | `GET /docs` |
| **Agent Card** | `GET /.well-known/agent.json` |
| **MCP Skills** | `GET /.well-known/skills.json` |

---

## Track 1: Autonomous Trading Agents

### One-Line Summary

RUMA is a self-custody autonomous trading agent on BNB Chain that reads markets via 12 CoinMarketCap AI Agent Hub data tools (MCP + x402), gates every trade on TRION 6-plane coherence mathematics (~87% silence rate), and executes self-custodial BSC swaps via the Trust Wallet Agent Kit — with a compounding on-chain reputation that grows irreversibly.

### Technical Architecture

```
CoinMarketCap AI Agent Hub (12 MCP Tools + x402 payments)
  │  1.FearGreed · 2.Prices · 3.GlobalMetrics · 4.Trending
  │  5.TechnicalIndicators · 6.OnChain · 7.SocialSentiment
  │  8.Derivatives · 9.MarketPairs · 10.Categories · 11.News · 12.OHLCV
  ▼
TRION Ψ-Gate  [Ψ(t) = 0.22P + 0.25I + 0.18C + 0.13S + 0.10W + 0.12A]
  │  6 cognitive planes fed by CMC data
  │  Gate: Ψ ≥ Δ(t) → ACT  |  Ψ < Δ(t) → SILENCE (~87%)
  ├─ Bayesian Kelly sizing → f* (2% vault cap)
  └─ Trust Wallet Agent Kit (TWAK)
      x402 payment audit → Local signing → PancakeSwap V2 → BSC
      Competition contract: 0x212c61b9b72c95d95bf29cf032f5e5635629aed5
```

### Judge Evidence — One Call Shows Everything

```bash
# Full autonomous pipeline (CMC→Ψ→TWAK) in one endpoint:
curl https://ruma.replit.app/api/v1/autonomous/demo?symbol=BNB

# Scoring proof package (tx hashes, Sharpe, Sortino, silence rate):
curl https://ruma.replit.app/api/v1/competition/proof

# x402 payment audit trail (every CMC call in trade loop):
curl https://ruma.replit.app/api/v1/x402/audit

# Live risk-adjusted performance (Sharpe, Sortino, Calmar):
curl https://ruma.replit.app/api/v1/competition/risk-metrics

# Architecture diagram JSON:
curl https://ruma.replit.app/api/v1/autonomous/flow
```

### TWAK Integration Depth (30 pts)

| Surface | Implementation |
|---|---|
| Sole execution layer | All BSC swaps via TWAK signing. No custodial fallback. |
| Local signing | `TWAK_AGENT_PRIVATE_KEY` env var — key never leaves process |
| Competition registration | `POST /api/v1/bnb/competition/register` → on-chain tx |
| MCP action | `competition_register` tool in MCP server |
| x402 native | CMC premium data paid per-request in trade loop — audit at `/api/v1/x402/audit` |
| Autonomous swaps | `POST /api/v1/twak/swap` → PancakeSwap V2 |
| Drawdown guard | ≥30% drawdown → TWAK signing disabled before sign call |
| Portfolio | `GET /api/v1/twak/portfolio` — BNB + BEP-20 balances |
| Autonomous demo | `GET /api/v1/autonomous/demo` — full CMC→Ψ→TWAK in one call |

### CMC AI Agent Hub Integration — 12 Data Tools (20 pts)

| # | CMC Tool | TRION Plane | Endpoint |
|---|---|---|---|
| 1 | Fear & Greed Index | W-plane (world model) | `/api/v1/cmc/fear-greed` |
| 2 | Spot Prices (BEP-20) | P-plane (perceptual entropy) | `/api/v1/cmc/prices` |
| 3 | Global Market Metrics | W-plane (macro context) | `/api/v1/cmc/global-metrics` |
| 4 | Trending / Gainers+Losers | C-plane (consensus signal) | `/api/v1/cmc/trending` |
| 5 | Technical Indicators (RSI, MACD, BB) | I-plane (inferential) | `/api/v1/cmc/technical-indicators` |
| 6 | On-Chain Metrics (BSC tx vol) | C-plane (on-chain consensus) | `/api/v1/cmc/on-chain` |
| 7 | Social Sentiment | S-plane (self-reflection) | `/api/v1/cmc/social-sentiment` |
| 8 | Derivatives / Funding Rate | I-plane (arb signal) | `/api/v1/cmc/derivatives` |
| 9 | Market Pairs / Liquidity | TWAK slippage confidence | `/api/v1/cmc/market-pairs` |
| 10 | Category Performance (DeFi/L1/AI) | W-plane (sector rotation) | `/api/v1/cmc/categories` |
| 11 | News Sentiment | W-plane (narrative) | `/api/v1/cmc/news` |
| 12 | Historical OHLCV | Track 2 backtesting | `/api/v1/cmc/ohlcv` |

All 12 tools fire an x402 payment event before fetching data (see `/api/v1/x402/audit`).

Composite signals endpoint: `GET /api/v1/cmc/signals`
Full parallel analysis: `POST /api/v1/cmc/analyze?symbol=BNB`

### Self-Custody Integrity (25 pts)

- `TWAK_AGENT_PRIVATE_KEY` loaded once at startup into `eth_account.Account`
- All BSC signing done locally via `eth_account.sign_transaction()`
- Key is never serialised, logged, or sent to any external service
- Simulation mode (no key): all logic runs, only signing is skipped — agent correctly reports `simulation_mode: true`
- Emergency stop: `POST /api/v1/competition/emergency-stop` disables TWAK signing immediately

### Autonomy & Rule Adherence (25 pts)

- Competition scheduler polls CMC → runs Ψ-gate → executes TWAK swap every 4h
- Urgency mode: 30-min polling when <4h left in trading day with no trade
- Daily trade minimum: 1 trade/day (scheduler forces execution at day end)
- Kill switch: `POST /api/v1/competition/emergency-stop` — disables all signing
- Drawdown guard: 30% max drawdown — checked before every swap sign call
- Daily loss limit: 6% — auto-pause with UTC reset
- Token allowlist: 149 eligible BEP-20 tokens (`bnb/allowlist.py`)
- Silence rate: ~87% of Ψ evaluations result in no trade (gate working correctly)

### Risk-Adjusted Performance Metrics

```bash
curl https://ruma.replit.app/api/v1/competition/risk-metrics
```

Returns: **Sharpe ratio, Sortino ratio, Calmar ratio**, win rate, expectancy, profit factor.

- **Sharpe**: Mean trade return / StdDev(returns) × √252
- **Sortino**: Mean trade return / DownsideStdDev(returns) × √252 — penalises only losses
- **Calmar**: Annualised return (7-day window) / Max Drawdown

### Risk Management

| Rule | Value | Enforcement |
|---|---|---|
| Max position | 2% of vault | Bayesian Kelly hard cap |
| Daily loss limit | 6% | Auto-pause, UTC reset |
| Max drawdown | 30% | TWAK signing disabled |
| Slippage | 0.5% max | Hardcoded in swap |
| Min trades | 1/day | Competition scheduler |
| Scheduler | Every 4h (30 min if urgent) | Background asyncio task |

### Track 1 API Quick Reference

```bash
# Health
curl https://ruma.replit.app/api/v1/health

# Autonomous demo (full CMC→Ψ→TWAK pipeline)
curl https://ruma.replit.app/api/v1/autonomous/demo?symbol=BNB

# CMC feeds (12 tools)
curl https://ruma.replit.app/api/v1/cmc/fear-greed
curl https://ruma.replit.app/api/v1/cmc/signals
curl https://ruma.replit.app/api/v1/cmc/technical-indicators?symbol=BNB
curl https://ruma.replit.app/api/v1/cmc/on-chain?symbol=BNB
curl https://ruma.replit.app/api/v1/cmc/trending
curl https://ruma.replit.app/api/v1/cmc/derivatives?symbol=BNB

# x402 audit (payment trail)
curl https://ruma.replit.app/api/v1/x402/audit

# TWAK
curl https://ruma.replit.app/api/v1/twak/status
curl https://ruma.replit.app/api/v1/twak/portfolio

# Competition
curl https://ruma.replit.app/api/v1/competition/dashboard
curl https://ruma.replit.app/api/v1/competition/proof
curl https://ruma.replit.app/api/v1/competition/risk-metrics

# MCP skill invocation
curl -X POST https://ruma.replit.app/api/v1/skills/invoke/coherence_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"coherence_evaluate","input":{"query":"BNB LONG now?"}}'

# Live SSE streams
curl https://ruma.replit.app/api/v1/stream/intelligence
```

---

## Track 2: Strategy Skills

### One-Line Summary

RUMA's CMC Strategy Skill is a three-strategy ensemble that transforms 12 CoinMarketCap data types into a fully backtestable trading strategy specification — with real CMC OHLCV price history, Sharpe ratio, Sortino ratio, and Bayesian Kelly position sizing.

### Three Sub-Strategies

**1. Momentum Composite (40% weight)**
- Inputs: CMC Fear & Greed (current + 14-day rolling slope), CMC price % changes (1h/24h/7d)
- Signal: FG trending up + positive multi-timeframe momentum → LONG; inverse → SHORT
- Novel: Uses linear regression slope of F&G as a leading indicator for price action

**2. Sentiment Divergence (30% weight)**
- Inputs: CMC social sentiment score (Tool 7), CMC 24h price trend (Tool 2)
- Signal: Sentiment ahead of price → LONG (mean-reversion); price ahead of sentiment → SHORT
- Novel: Treats CMC social heat as an independent leading indicator vs. price action

**3. Regime Detector (30% weight)**
- Inputs: CMC F&G level + volatility, CMC 7d price change, CMC on-chain activity
- Regimes: BULL (FG≥60 + 7d>5%) | BEAR (FG≤35 + 7d<-5%) | VOLATILE | SIDEWAYS
- Novel: Regime classification gates position sizing — VOLATILE/SIDEWAYS → NEUTRAL, reduce exposure

### Ensemble → Strategy Spec

The three votes combine with weighted confidence → single direction with:
- Risk levels: 2% stop-loss, 4% take-profit (2:1 R:R default)
- Bayesian Kelly sizing: p_win(confidence) × R:R → f* (25% fractional, 2% cap)
- Full backtestable JSON spec (all params reproducible)

### Backtest Engine

- **Price data**: CMC `/v2/cryptocurrency/ohlcv/historical` (real daily closes when `CMC_API_KEY` set)
- **Sentiment data**: CMC Fear & Greed historical (alternative.me, always available)
- **Risk metrics**: Sharpe ratio + **Sortino ratio** (downside risk only) + max drawdown
- **Method**: Rolling-window signal → Kelly sizing → stop/TP exit simulation
- **Reproducible**: All parameters captured in `backtest_params` field

### Track 2 API Quick Reference

```bash
# Catalog of all 3 strategies + ensemble method
curl https://ruma.replit.app/api/v1/strategy/catalog

# Live strategy spec for BNB (Track 2 deliverable)
curl https://ruma.replit.app/api/v1/strategy/spec/BNB

# Backtest — uses real CMC OHLCV data + returns Sharpe AND Sortino
curl -X POST https://ruma.replit.app/api/v1/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BNB","window":30,"stop_pct":0.02,"tp_pct":0.04}'

# Historical OHLCV data (CMC Tool 12)
curl https://ruma.replit.app/api/v1/cmc/ohlcv?symbol=BNB&count=30

# Dry-run execute (generates spec, no actual trade)
curl -X POST https://ruma.replit.app/api/v1/strategy/execute \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BNB","dry_run":true}'
```

### Sample Backtest Output

```json
{
  "backtest": {
    "symbol": "BNB",
    "periods": 30,
    "trades": 9,
    "win_rate": 0.78,
    "total_return_pct": 4.21,
    "max_drawdown_pct": 0.83,
    "sharpe_approx": 2.14,
    "sortino_ratio": 3.87,
    "price_data_source": "CoinMarketCap OHLCV (real daily closes)"
  },
  "risk_adjusted": {
    "sharpe_ratio": 2.14,
    "sortino_ratio": 3.87,
    "sortino_interpretation": "EXCELLENT"
  }
}
```

---

## BNB AI Agent SDK (Special Prize)

```bash
curl https://ruma.replit.app/api/v1/bnb-sdk/status       # SDK health + identity
curl https://ruma.replit.app/api/v1/bnb-sdk/features     # SDK vs. native capability map
curl https://ruma.replit.app/api/v1/bnb-sdk/market/BNB   # Live price via SDK
curl -X POST https://ruma.replit.app/api/v1/bnb-sdk/skills  # Register skills with Agent Hub
curl -X POST https://ruma.replit.app/api/v1/bnb-sdk/execute \
  -d '{"symbol":"BNB","direction":"LONG","dry_run":true}'
```

---

## 5-Minute Quick Start

```bash
git clone https://github.com/dev-analyshd/Ruma && cd Ruma

# Set secrets (env vars):
# CMC_API_KEY=...                 (coinmarketcap.com/api/agent — enables all 12 CMC tools)
# TWAK_AGENT_PRIVATE_KEY=0x...   (your BSC agent wallet — enables live signing)
# ANTHROPIC_API_KEY=sk-ant-...   (enables full LLM reasoning chain skill)

pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Track 1: run autonomous demo
curl http://localhost:8000/api/v1/autonomous/demo?symbol=BNB

# Track 1: register on-chain for competition
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" -d '{"agent_address":"YOUR_WALLET"}'

# Track 2: get live strategy spec + backtest
curl http://localhost:8000/api/v1/strategy/spec/BNB
curl -X POST http://localhost:8000/api/v1/strategy/backtest \
  -H "Content-Type: application/json" -d '{"symbol":"BNB","window":30}'

# View judge evidence
curl http://localhost:8000/api/v1/competition/proof
curl http://localhost:8000/api/v1/competition/risk-metrics
curl http://localhost:8000/api/v1/x402/audit
```

---

## Scoring Self-Assessment

| Track 1 Criterion | Max | RUMA |
|---|---|---|
| TWAK Integration Depth | 30 | 28 — 9 surfaces (register, swap, portfolio, x402, autonomous, drawdown guard, local signing, MCP action, SDK) |
| Self-Custody Integrity | 25 | 25 — local signing only, never serialised, simulation mode correct |
| Autonomy & Rule Adherence | 25 | 23 — scheduler, kill switch, daily min, 30%/6% guards, 149-token allowlist |
| CMC Signal Quality | 20 | 19 — 12 data tools, MCP endpoint, x402 audit, all 6 Ψ planes fed |
| **Total** | **100** | **95** |

| Special Prize | Evidence |
|---|---|
| Best CMC AI Agent Hub | 12 tool types, x402 audit trail, MCP endpoint, all TRION planes fed |
| Best TWAK Use | Sole execution layer, autonomous mode, local signing, x402, drawdown guard |
| Best BNB AI Agent SDK | SDK wrapper with native fallback, skill registration, strategy execution |

---

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · Track 1 + Track 2 · June 2026*
*Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)*
*Truth or silence. The silence is information.*
