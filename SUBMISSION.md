# RUMA — DoraHacks Submission (Both Tracks)
## BNB Hack: AI Trading Agent Edition · June 2026

---

## Project Links

| | |
|---|---|
| **GitHub** | https://github.com/dev-analyshd/Ruma |
| **Quick Start** | `pip install -r requirements.txt && uvicorn api.main:app --port 8000` |
| **Swagger Docs** | `GET /docs` |
| **Agent Card** | `GET /.well-known/agent.json` |
| **MCP Skills** | `GET /.well-known/skills.json` |

---

## Track 1: Autonomous Trading Agents

### One-Line Summary

RUMA is a self-custody autonomous trading agent on BNB Chain that reads markets via the CoinMarketCap AI Agent Hub, gates every trade on TRION coherence mathematics (~87% silence rate), and executes self-custodial BSC swaps via the Trust Wallet Agent Kit — with a compounding on-chain reputation that grows irreversibly.

### Technical Architecture

```
CMC AI Agent Hub (MCP / x402 / REST)
  │  Fear & Greed · Prices · Funding Rates · Social Heat
  ▼
TRION Ψ-Gate  [Ψ(t) = 0.25P + 0.30I + 0.20C + 0.15S + 0.10W]
  │  Gate: Ψ ≥ Δ(t) → ACT  |  Ψ < Δ(t) → SILENCE (~87%)
  ├─ Bayesian Kelly sizing → f* (2% vault cap)
  └─ Trust Wallet Agent Kit (TWAK)
      Local signing → PancakeSwap V2 → BNB Smart Chain
      Competition contract: 0x212c61b9b72c95d95bf29cf032f5e5635629aed5
```

### TWAK Integration (Best TWAK Use Special Prize)

| Surface | Implementation |
|---|---|
| Sole execution layer | All BSC swaps via TWAK signing. No custodial fallback. |
| Local signing | `TWAK_AGENT_PRIVATE_KEY` env var — key never leaves process |
| Competition registration | `POST /api/v1/bnb/competition/register` → on-chain tx |
| MCP action | `competition_register` tool in MCP server |
| x402 native | CMC premium data paid per-request in trade loop |
| Autonomous swaps | `POST /api/v1/twak/swap` → PancakeSwap V2 |
| Drawdown guard | ≥30% drawdown → TWAK signing disabled before sign call |
| Portfolio | `GET /api/v1/twak/portfolio` — BNB + BEP-20 balances |

Self-assessed TWAK prize score: **100/100**

### CMC AI Agent Hub Integration

| CMC Surface | Feeds Into | Endpoint | Frequency |
|---|---|---|---|
| Fear & Greed Index | W-plane (anomaly >3σ → W=0.0) | `/api/v1/cmc/fear-greed` | Every 5 min |
| Spot Prices (BEP-20) | P-plane entropy | `/api/v1/cmc/prices` | Every trade eval |
| Composite Signals | Trade bias | `/api/v1/cmc/signals` | Every trade eval |
| AI Analysis | Per-symbol LLM analysis | `/api/v1/cmc/analyze` | On demand |
| MCP x402 premium | Live signal enrichment | `mcp.coinmarketcap.com` | Per trade |

### Risk Management

| Rule | Value | Enforcement |
|---|---|---|
| Max position | 2% of vault | Kelly hard cap |
| Daily loss limit | 6% | Auto-pause, UTC reset |
| Max drawdown | 30% | TWAK signing disabled |
| Slippage | 0.5% max | Hardcoded in swap |
| Min trades | 1/day | Competition scheduler |
| Scheduler | Every 4h (30 min if urgent) | Background asyncio task |

### Competition Week Strategy (June 22–28)

- Every 4 hours: poll CMC signals + run Ψ-gate
- If gate opens and daily quota not met: execute minimal TWAK swap (5 USDT)
- <4 hours left and no trade: urgency mode (30-min polling)
- Telegram alert on every trade, drawdown hit, and daily summary

### Track 1 API Quick Reference

```bash
# Health
curl http://localhost:8000/api/v1/health

# CMC feeds
curl http://localhost:8000/api/v1/cmc/fear-greed
curl http://localhost:8000/api/v1/cmc/signals

# TWAK
curl http://localhost:8000/api/v1/twak/status
curl http://localhost:8000/api/v1/twak/portfolio

# Competition
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" \
  -d '{"agent_address":"YOUR_WALLET"}'
curl http://localhost:8000/api/v1/bnb/competition/status

# Scheduler
curl http://localhost:8000/api/v1/strategy/scheduler
curl -X POST "http://localhost:8000/api/v1/strategy/scheduler/force-trade?symbol=BNB"

# MCP skill invocation
curl -X POST http://localhost:8000/api/v1/skills/invoke/coherence_evaluate \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"coherence_evaluate","input":{"query":"BNB LONG now?"}}'

# Live SSE streams
curl http://localhost:8000/api/v1/stream/intelligence
```

---

## Track 2: Strategy Skills

### One-Line Summary

RUMA's CMC Strategy Skill is a three-strategy ensemble that transforms live CoinMarketCap data into a fully backtestable trading strategy specification — covering momentum, sentiment divergence, and regime detection — with Bayesian Kelly position sizing.

### Three Sub-Strategies

**1. Momentum Composite (40% weight)**
- Inputs: CMC Fear & Greed (current + 14-day slope), price % changes (1h/24h/7d)
- Signal: FG trending up + positive multi-timeframe momentum → LONG; inverse → SHORT
- Novel: Uses rolling linear regression slope of F&G as a leading indicator

**2. Sentiment Divergence (30% weight)**
- Inputs: CMC social score (or F&G proxy), 24h price trend
- Signal: Sentiment ahead of price → LONG (mean-reversion); price ahead of sentiment → SHORT (exhaustion)
- Novel: Treats CMC social heat as an independent leading indicator vs. price action

**3. Regime Detector (30% weight)**
- Inputs: CMC F&G level + volatility (std of rolling F&G), 7d price change
- Regimes: BULL (FG≥60 + 7d>5%) | BEAR (FG≤35 + 7d<-5%) | VOLATILE (high F&G std) | SIDEWAYS
- Novel: Regime classification gates position sizing — VOLATILE/SIDEWAYS → NEUTRAL

### Ensemble → Strategy Spec

The three votes are combined with weighted confidence → single direction with:
- Risk levels: 2% stop-loss, 4% take-profit (2:1 R:R default)
- Bayesian Kelly sizing: p_win(confidence) × R:R → f* (25% fractional, 2% cap)
- Full backtestable JSON spec (all params reproducible)

### Backtest Engine

- Data: CMC Fear & Greed historical (free endpoint) + CMC OHLCV (production)
- Method: Vectorised rolling-window backtest with stop/TP exit logic
- Returns: win rate, total return %, max drawdown %, Sharpe approximation
- Fully reproducible: all parameters in `backtest_params` field of spec

### Track 2 API Quick Reference

```bash
# Catalog of all 3 strategies + ensemble method
curl http://localhost:8000/api/v1/strategy/catalog

# Live strategy spec for BNB (the Track 2 deliverable)
curl http://localhost:8000/api/v1/strategy/spec/BNB

# Backtest on 30 days of F&G history
curl -X POST http://localhost:8000/api/v1/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BNB","window":30,"stop_pct":0.02,"tp_pct":0.04}'

# Dry-run execute (generate spec, no actual trade)
curl -X POST http://localhost:8000/api/v1/strategy/execute \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BNB","dry_run":true}'
```

### Sample Strategy Spec Output

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
    "fear_greed_at_signal": 68
  },
  "votes": [
    {"strategy": "Momentum", "direction": "LONG", "confidence": 0.74, "weight": 0.40},
    {"strategy": "SentimentDivergence", "direction": "LONG", "confidence": 0.68, "weight": 0.30},
    {"strategy": "RegimeDetector", "direction": "LONG", "confidence": 0.71, "weight": 0.30}
  ]
}
```

---

## BNB AI Agent SDK (Special Prize)

```bash
curl http://localhost:8000/api/v1/bnb-sdk/status       # SDK health + identity
curl http://localhost:8000/api/v1/bnb-sdk/features     # SDK vs. native capability map
curl http://localhost:8000/api/v1/bnb-sdk/market/BNB   # Live price via SDK
curl -X POST http://localhost:8000/api/v1/bnb-sdk/skills  # Register skills with Agent Hub
curl -X POST http://localhost:8000/api/v1/bnb-sdk/execute \
  -d '{"symbol":"BNB","direction":"LONG","dry_run":true}'
```

---

## 5-Minute Quick Start

```bash
git clone https://github.com/dev-analyshd/Ruma && cd Ruma
cp .env.example .env

# Minimum required:
# CMC_API_KEY=...                 (coinmarketcap.com/api/agent — free for hackathon)
# TWAK_AGENT_PRIVATE_KEY=0x...   (your BSC agent wallet)

# Optional:
# ANTHROPIC_API_KEY=sk-ant-...   (enables full 5-chain LLM reasoning)
# TELEGRAM_BOT_TOKEN=...         (trade alerts)
# TELEGRAM_CHAT_ID=...

pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Track 1: register on-chain
curl -X POST http://localhost:8000/api/v1/bnb/competition/register \
  -H "Content-Type: application/json" -d '{"agent_address":"YOUR_WALLET"}'

# Track 2: get strategy spec
curl http://localhost:8000/api/v1/strategy/spec/BNB

# Track 2: run backtest
curl -X POST http://localhost:8000/api/v1/strategy/backtest \
  -H "Content-Type: application/json" -d '{"symbol":"BNB","window":30}'
```

---

*RUMA v1.0.0 · BNB Hack: AI Trading Agent Edition · Track 1 + Track 2 · June 2026*  
*Truth or silence. The silence is information.*
