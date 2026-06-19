"""
Track 2: CMC Strategy Skill — REST API Routes
=============================================
GET  /api/v1/strategy/catalog       — List all 3 strategies
GET  /api/v1/strategy/generate      — Live CMC → strategy spec
POST /api/v1/strategy/backtest      — Run backtest on historical F&G + price
GET  /api/v1/strategy/spec/{symbol} — Full spec for a symbol
POST /api/v1/strategy/execute       — Execute a strategy spec via BNB Agent SDK
"""
from __future__ import annotations

import time
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────
class BacktestRequest(BaseModel):
    symbol: str = "BNB"
    window: int = 30          # days of F&G history to backtest over
    stop_pct: float = 0.02
    tp_pct: float = 0.04
    kelly_fraction: float = 0.25

class ExecuteRequest(BaseModel):
    symbol: str = "BNB"
    dry_run: bool = True      # default: don't trade, just return spec


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/strategy/catalog")
async def strategy_catalog():
    """List all available strategies (Track 2 submission)."""
    return {
        "track": "Track 2: Strategy Skills — BNB Hack AI Trading Agent Edition",
        "strategies": [
            {
                "id": "momentum",
                "name": "Momentum Composite",
                "description": "Fear & Greed trend + price velocity (1h/24h/7d) → directional bias",
                "weight": 0.40,
                "inputs": ["CMC Fear & Greed", "CMC price % changes"],
                "signals": ["LONG if FG trending up + price momentum positive",
                            "SHORT if FG trending down + price momentum negative",
                            "NEUTRAL on divergence"],
            },
            {
                "id": "sentiment_divergence",
                "name": "Sentiment Divergence",
                "description": "CMC social heat vs. price action divergence → mean-reversion",
                "weight": 0.30,
                "inputs": ["CMC social score / Fear & Greed proxy", "CMC 24h price change"],
                "signals": ["LONG if sentiment ahead of price (price will catch up)",
                            "SHORT if price ahead of sentiment (exhaustion)",
                            "Trend confirmation when both agree"],
            },
            {
                "id": "regime_detector",
                "name": "Regime Detector",
                "description": "Bull/Bear/Sideways/Volatile regime from F&G + volatility",
                "weight": 0.30,
                "inputs": ["CMC Fear & Greed", "7d price change", "F&G rolling std"],
                "signals": ["BULL regime → LONG bias",
                            "BEAR regime → SHORT bias",
                            "SIDEWAYS/VOLATILE → NEUTRAL, reduce size"],
            },
        ],
        "ensemble": {
            "method": "Weighted majority vote",
            "weights": {"Momentum": 0.40, "SentimentDivergence": 0.30, "RegimeDetector": 0.30},
            "sizing": "Bayesian Kelly (25% fractional, 2% hard cap)",
            "risk": "2% stop-loss, 4% take-profit (2:1 R:R default)",
        },
        "backtest_endpoint": "POST /api/v1/strategy/backtest",
        "spec_endpoint": "GET /api/v1/strategy/spec/{symbol}",
        "execute_endpoint": "POST /api/v1/strategy/execute",
    }


@router.get("/strategy/spec/{symbol}")
async def get_strategy_spec(symbol: str = "BNB"):
    """
    Generate a live strategy spec for a symbol using CMC data.
    This is the core Track 2 deliverable — a fully backtestable strategy JSON.
    """
    symbol = symbol.upper()
    try:
        from skills.cmc_strategy_skill import generate_strategy
        spec = await generate_strategy(symbol)
        return {
            "ok": True,
            "track": 2,
            "track_name": "Strategy Skills",
            "spec": spec.to_dict(),
            "how_to_backtest": f"POST /api/v1/strategy/backtest with symbol={symbol}",
            "timestamp": time.time(),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Strategy generation error: {e}")


@router.get("/strategy/generate")
async def generate_strategy_for_symbol(symbol: str = Query(default="BNB", description="Token symbol (BNB, ETH, BTC, CAKE…)")):
    """
    Alias for /strategy/spec/{symbol} — generates live CMC-driven strategy.
    """
    return await get_strategy_spec(symbol)


@router.post("/strategy/backtest")
async def run_strategy_backtest(req: BacktestRequest):
    """
    Run a historical backtest of the CMC Strategy ensemble.

    Price data: CMC /v2/cryptocurrency/ohlcv/historical (real daily OHLCV when
    CMC_API_KEY is set). Falls back to F&G-anchored synthetic prices for demo mode.
    Sentiment data: Fear & Greed historical (alternative.me, always available).

    Returns: win rate, total return, max drawdown, Sharpe ratio, Sortino ratio.
    """
    symbol = req.symbol.upper()
    if req.window < 7 or req.window > 365:
        raise HTTPException(status_code=400, detail="window must be 7–365 days")
    if req.stop_pct <= 0 or req.tp_pct <= 0:
        raise HTTPException(status_code=400, detail="stop_pct and tp_pct must be positive")

    try:
        from skills.cmc_strategy_skill import generate_backtest
        result = await generate_backtest(symbol, req.window)
        bt_dict = asdict(result)
        return {
            "ok": True,
            "track": 2,
            "symbol": symbol,
            "backtest": bt_dict,
            "risk_adjusted": {
                "sharpe_ratio": bt_dict.get("sharpe_approx"),
                "sortino_ratio": bt_dict.get("sortino_ratio"),
                "sharpe_interpretation": (
                    "EXCELLENT" if (bt_dict.get("sharpe_approx") or 0) > 2
                    else "GOOD" if (bt_dict.get("sharpe_approx") or 0) > 1
                    else "ACCEPTABLE" if (bt_dict.get("sharpe_approx") or 0) > 0
                    else "NEGATIVE"
                ),
                "sortino_interpretation": (
                    "EXCELLENT" if (bt_dict.get("sortino_ratio") or 0) > 2
                    else "GOOD" if (bt_dict.get("sortino_ratio") or 0) > 1
                    else "ACCEPTABLE" if (bt_dict.get("sortino_ratio") or 0) > 0
                    else "NEGATIVE"
                ),
                "note": "Sortino penalises only downside volatility — more relevant for trading strategies",
            },
            "methodology": {
                "price_data_source": bt_dict.get("price_data_source"),
                "sentiment_data": "CoinMarketCap Fear & Greed historical (alternative.me fallback)",
                "price_ohlcv_endpoint": "CMC /v2/cryptocurrency/ohlcv/historical (real when CMC_API_KEY set)",
                "signal": "7-day rolling F&G slope + 24h price momentum",
                "sizing": "Bayesian Kelly (25% fractional, 2% cap)",
                "stop_pct": req.stop_pct,
                "tp_pct": req.tp_pct,
                "max_holding_bars": 10,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Backtest error: {e}")


@router.post("/strategy/execute")
async def execute_strategy(req: ExecuteRequest):
    """
    Generate a strategy spec and optionally execute it via BNB Agent SDK.
    dry_run=true (default): returns spec without trading.
    dry_run=false: routes through BNBAgentSDKClient → TWAK → BSC.
    """
    symbol = req.symbol.upper()
    try:
        from skills.cmc_strategy_skill import generate_strategy
        spec = await generate_strategy(symbol)
        spec_dict = spec.to_dict()

        if req.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "spec": spec_dict,
                "message": "Set dry_run=false to execute via BNB Agent SDK + TWAK",
            }

        from bnb.bnb_agent_sdk import get_bnb_sdk
        sdk = get_bnb_sdk()
        result = await sdk.execute_strategy(spec_dict)
        return {
            "ok": result.success,
            "dry_run": False,
            "spec": spec_dict,
            "execution": {
                "success": result.success,
                "tx_hash": result.tx_hash,
                "gas_used": result.gas_used,
                "method": result.method,
                "error": result.error,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Strategy execute error: {e}")


@router.get("/strategy/scheduler")
async def scheduler_status():
    """Competition week trading scheduler status."""
    from bnb.trading_scheduler import get_scheduler_state, COMPETITION_START_UTC, COMPETITION_END_UTC
    state = get_scheduler_state()
    return {
        "ok": True,
        "competition_window": {
            "start": COMPETITION_START_UTC.isoformat(),
            "end": COMPETITION_END_UTC.isoformat(),
            "active": state.in_competition_window(),
        },
        "today": {
            "date_utc": state.today_date,
            "trades": state.today_trades,
            "quota_met": state.daily_quota_met(),
            "hours_left": round(state.hours_left_today(), 1),
        },
        "totals": {
            "trades": state.total_trades,
            "pnl_pct": state.total_pnl_pct,
        },
        "halts": {
            "drawdown": state.drawdown_halt,
            "daily_loss": state.daily_loss_halt,
        },
        "mode": "DRY-RUN" if state.dry_run else "LIVE",
        "last_poll_ts": state.last_poll_ts,
        "last_trade_ts": state.last_trade_ts,
        "recent_log": state.log[-20:],
    }


@router.post("/strategy/scheduler/force-trade")
async def force_scheduled_trade(symbol: str = Query(default="BNB")):
    """
    Manually trigger a scheduled trade (for demo/testing).
    Respects all safety guards (drawdown, daily loss).
    """
    from bnb.trading_scheduler import force_trade_now
    result = await force_trade_now(symbol.upper())
    return {"ok": result.get("success", False), "result": result, "symbol": symbol}
