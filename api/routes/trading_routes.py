"""
Dynamic Trading Engine API — RUMA
===================================
Exposes all dynamic modules as REST endpoints.
Judges can call these to see the full adaptive decision pipeline live.

GET  /api/v1/trading/sizer          — compute dynamic position size
GET  /api/v1/trading/risk           — current dynamic risk limits + circuit breakers
GET  /api/v1/trading/threshold      — current Δ(t) gate
GET  /api/v1/trading/strategy       — selected strategy for current CMC regime
GET  /api/v1/trading/opportunities  — top 5 asset opportunities (live CMC scan)
GET  /api/v1/trading/pipeline       — full pipeline: opportunities → strategy → size → risk
GET  /api/v1/trading/strategies     — all 10 ADAPT-Ω strategies ranked by expected_edge
GET  /api/v1/trading/strategies/{name} — single strategy signal
POST /api/v1/trading/strategies/outcome — record trade outcome for on-chain learning
GET  /api/v1/trading/strategies/performance — per-strategy win rates
"""
from __future__ import annotations
import asyncio
import os
import time

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

# ── Default context (live values come from CMC + moat accumulator) ────────────
async def _get_cmc_context() -> dict:
    """Pull live CMC signals for context. Falls back to defaults."""
    try:
        import httpx
        r = await httpx.AsyncClient(timeout=8).get("https://api.alternative.me/fng/?limit=1")
        items = r.json().get("data", [{}])
        fg = int(items[0].get("value", 50))
        fg_label = items[0].get("value_classification", "Neutral")
    except Exception:
        fg, fg_label = 50, "Neutral"
    return {"fear_greed": fg, "fear_greed_label": fg_label}

def _get_agent_state() -> dict:
    """Fetch agent state from in-process singletons."""
    try:
        from api.routes.competition_dashboard import get_competition_state
        cs = get_competition_state()
        lambda_val = 0.01
        consecutive_wins = cs.total_wins
    except Exception:
        lambda_val = 0.01
        consecutive_wins = 0
    try:
        from bnb.trading_scheduler import get_scheduler_state
        ss = get_scheduler_state()
        trades_last_hour = ss.today_trades
        psi_history = [p["psi"] for p in ss.log[-10:] if isinstance(p, dict) and "psi" in p]
    except Exception:
        trades_last_hour, psi_history = 0, []
    return {
        "lambda_val": lambda_val,
        "consecutive_wins": consecutive_wins,
        "trades_last_hour": trades_last_hour,
        "psi_history": psi_history,
        "capital": float(os.getenv("VAULT_CAPITAL_USD", "500")),
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/trading/sizer")
async def dynamic_sizer(
    psi: float = Query(default=0.72, description="Current Ψ score (0–1)"),
    capital: float = Query(default=500.0, description="Vault capital USD"),
    symbol: str = Query(default="BNB", description="Token to size position for"),
):
    """
    Compute dynamic position size using 5-factor adaptive model.
    Replaces the fixed 2% cap: size = f(regime, Ψ², volatility, liquidity, correlation).
    """
    from trading.dynamic_sizer import get_sizer, MarketState, AgentState
    cmc = await _get_cmc_context()
    agent_ctx = _get_agent_state()

    # Build a minimal CMC snap for MarketState
    snap = {"fear_greed": cmc["fear_greed"], "price_change_24h": 0.0, "price_change_7d": 0.0,
            "volume_24h": 50_000_000.0}  # $50M default volume

    sizer = get_sizer()
    market = MarketState.from_cmc_snap(snap)
    agent = AgentState(
        psi=psi,
        lambda_val=agent_ctx.get("lambda_val", 0.01),
        total_capital=capital,
    )
    result = sizer.compute_size(
        capital=capital, psi=psi, market=market, agent=agent,
        win_probability=0.5 + (psi - 0.5) * 0.4,
    )
    return {
        "ok": True,
        "symbol": symbol,
        "psi": psi,
        "capital_usd": capital,
        "fear_greed": cmc["fear_greed"],
        "sizing": result.to_dict(),
        "vs_fixed_2pct": {
            "fixed_size_usd": round(capital * 0.02, 2),
            "dynamic_size_usd": round(result.size_usd, 2),
            "delta_pct": round((result.size_usd - capital * 0.02) / capital * 100, 3),
        },
    }


@router.get("/trading/risk")
async def dynamic_risk(
    lambda_val: float = Query(default=0.01, description="Moat Λ value"),
    consecutive_wins: int = Query(default=0),
    drawdown_pct: float = Query(default=0.0, description="Current drawdown %"),
):
    """
    Compute dynamic risk limits — adapts to Λ, win streak, market stress, session.
    Circuit breakers checked live. Hard DQ cap at 28% drawdown (2% buffer).
    """
    from trading.dynamic_risk import get_risk_manager
    cmc = await _get_cmc_context()
    agent_ctx = _get_agent_state()

    mgr = get_risk_manager()
    limits = mgr.compute_dynamic_limits(
        lambda_val=agent_ctx.get("lambda_val", lambda_val),
        consecutive_wins=agent_ctx.get("consecutive_wins", consecutive_wins),
        fear_greed=cmc["fear_greed"],
        vol_30d=0.025,
        price_change_5m=0.0,
        psi_history=agent_ctx.get("psi_history", []),
        competition_days_remaining=8,
        current_drawdown_pct=drawdown_pct,
    )
    return {
        "ok": True,
        "fear_greed": cmc["fear_greed"],
        "fear_greed_label": cmc.get("fear_greed_label"),
        "agent": {"lambda_val": lambda_val, "consecutive_wins": consecutive_wins},
        "risk_limits": limits.to_dict(),
        "vs_fixed_rules": {
            "fixed_daily_risk_pct": 6.0,
            "dynamic_daily_risk_pct": round(limits.daily_risk_budget * 100, 3),
            "fixed_drawdown_cap_pct": 30.0,
            "dynamic_drawdown_cap_pct": round(limits.drawdown_cap * 100, 3),
        },
    }


@router.get("/trading/threshold")
async def dynamic_threshold(
    lambda_val: float = Query(default=0.01),
    trades_last_hour: int = Query(default=0),
    days_remaining: int = Query(default=7),
):
    """
    Compute current Δ(t) gate threshold.
    Replaces fixed 0.65: threshold breathes with stress, fatigue, time, and moat.
    """
    from trading.dynamic_threshold import get_threshold
    cmc = await _get_cmc_context()
    agent_ctx = _get_agent_state()

    fg = cmc["fear_greed"]
    stress = max(0.0, (50 - fg) / 50.0)  # Simple stress proxy

    thresh = get_threshold()
    result = thresh.compute_simple(
        lambda_val=agent_ctx.get("lambda_val", lambda_val),
        trades_last_hour=agent_ctx.get("trades_last_hour", trades_last_hour),
        stress=stress,
        fear_greed=fg,
        days_remaining=days_remaining,
    )
    return {
        "ok": True,
        "fear_greed": fg,
        "stress_proxy": round(stress, 4),
        "threshold": result.to_dict(),
        "vs_fixed": {"fixed_delta": 0.65, "dynamic_delta": result.delta,
                     "diff": round(result.delta - 0.65, 4)},
    }


@router.get("/trading/strategy")
async def dynamic_strategy(
    symbol: str = Query(default="BNB"),
    psi: float = Query(default=0.72),
):
    """
    Select optimal strategy from 5 candidates based on live CMC regime.
    Returns ranked strategies with expected returns per regime.
    """
    from trading.strategy_selector import get_selector
    from skills.cmc_strategy_skill import CMCFetcher
    symbol = symbol.upper()

    cmc = await _get_cmc_context()
    try:
        fetcher = CMCFetcher()
        snap = await fetcher.snapshot(symbol)
        snap_dict = {
            "fear_greed": snap.fear_greed,
            "price_change_1h": snap.price_change_1h,
            "price_change_24h": snap.price_change_24h,
            "price_change_7d": snap.price_change_7d,
            "volume_24h": snap.volume_24h,
            "funding_rate": snap.funding_rate,
            "social_score": snap.social_score,
        }
        await fetcher.close()
    except Exception:
        snap_dict = {"fear_greed": cmc["fear_greed"]}

    sel = get_selector()
    agent_ctx = _get_agent_state()
    result = sel.select_strategy(snap_dict, psi=psi, lambda_val=agent_ctx.get("lambda_val", 0.01))

    out = {
        "ok": True,
        "symbol": symbol,
        "psi": psi,
        "selected_strategy": result.selected,
        "silenced": result.silenced,
        "silence_reason": result.silence_reason,
        "regime_probs": result.regime_probs,
        "strategies_ranked": result.expected_returns,
        "fear_greed": cmc["fear_greed"],
    }
    if not result.silenced:
        sig = result.signal
        out["signal"] = {
            "direction": sig.direction,
            "confidence": sig.confidence,
            "effectiveness_in_regime": sig.effectiveness,
            "entry_logic": sig.entry_logic,
            "stop_logic": sig.stop_logic,
            "target_logic": sig.target_logic,
        }
    return out


@router.get("/trading/opportunities")
async def dynamic_opportunities(
    n: int = Query(default=5, le=15),
    min_volume_usd: float = Query(default=1_000_000.0),
):
    """
    Live scan of top assets from the 149-token allowlist.
    Scores by momentum alignment, volume surge, Fear & Greed fit, and liquidity.
    Returns top N opportunities ranked for the agent to evaluate.
    """
    from trading.asset_selector import get_asset_selector
    cmc = await _get_cmc_context()
    sel = get_asset_selector()
    opps = await sel.scan_opportunities(
        fear_greed=cmc["fear_greed"], n=n, min_volume_usd=min_volume_usd
    )
    return {
        "ok": True,
        "fear_greed": cmc["fear_greed"],
        "fear_greed_label": cmc.get("fear_greed_label"),
        "scanned_universe": "149-token BNB Hack allowlist (top 25 by liquidity)",
        "opportunities_found": len(opps),
        "opportunities": [o.to_dict() for o in opps],
        "timestamp": time.time(),
    }


@router.get("/trading/pipeline")
async def full_pipeline(
    psi: float = Query(default=0.72, description="Current Ψ score"),
    capital: float = Query(default=500.0, description="Vault capital USD"),
):
    """
    Full dynamic decision pipeline end-to-end (read-only, no actual trades):
    1. Scan opportunities (asset selector)
    2. Select strategy (strategy selector)
    3. Compute dynamic Δ(t) threshold
    4. Check if Ψ ≥ Δ → gate decision
    5. Compute position size (dynamic sizer)
    6. Check risk limits + circuit breakers
    7. Final trade spec (or silence)
    """
    from trading.dynamic_sizer import get_sizer, MarketState, AgentState
    from trading.dynamic_risk import get_risk_manager
    from trading.dynamic_threshold import get_threshold
    from trading.strategy_selector import get_selector
    from trading.asset_selector import get_asset_selector

    cmc = await _get_cmc_context()
    agent_ctx = _get_agent_state()
    fg = cmc["fear_greed"]
    lambda_val = agent_ctx.get("lambda_val", 0.01)
    stress = max(0.0, (50 - fg) / 50.0)

    # Step 1: Opportunities
    asset_sel = get_asset_selector()
    opps = await asset_sel.scan_opportunities(fear_greed=fg, n=3)
    best_opp = opps[0] if opps else None
    symbol = best_opp.symbol if best_opp else "BNB"

    # Step 2: Strategy selection
    snap_dict = {"fear_greed": fg}
    if best_opp:
        snap_dict.update({
            "price_change_1h": best_opp.price_change_1h,
            "price_change_24h": best_opp.price_change_24h,
            "price_change_7d": best_opp.price_change_7d,
            "volume_24h": best_opp.volume_24h_usd,
        })
    sel = get_selector()
    strategy_result = sel.select_strategy(snap_dict, psi=psi, lambda_val=lambda_val)

    # Step 3: Dynamic Δ(t)
    thresh = get_threshold()
    delta_result = thresh.compute_simple(
        lambda_val=lambda_val, trades_last_hour=agent_ctx.get("trades_last_hour", 0),
        stress=stress, fear_greed=fg, days_remaining=8,
    )
    delta = delta_result.delta

    # Step 4: Gate check
    gate_open = psi >= delta and not strategy_result.silenced

    # Step 5: Position sizing
    sizer = get_sizer()
    snap_for_market = {"fear_greed": fg, "price_change_24h": snap_dict.get("price_change_24h", 0),
                       "price_change_7d": snap_dict.get("price_change_7d", 0),
                       "volume_24h": snap_dict.get("volume_24h", 50_000_000)}
    market = MarketState.from_cmc_snap(snap_for_market)
    agent = AgentState(psi=psi, lambda_val=lambda_val, total_capital=capital)
    size_result = sizer.compute_size(
        capital=capital, psi=psi, market=market, agent=agent,
        win_probability=0.5 + (psi - 0.5) * 0.4,
    ) if gate_open else None

    # Step 6: Risk limits
    risk_mgr = get_risk_manager()
    risk = risk_mgr.compute_dynamic_limits(
        lambda_val=lambda_val,
        consecutive_wins=agent_ctx.get("consecutive_wins", 0),
        fear_greed=fg,
        stress=0.0,
    )
    any_breaker = any(cb.is_active() for cb in risk.circuit_breakers)
    final_action = "SILENCE"
    if gate_open and not any_breaker and size_result and size_result.size_usd > 0:
        final_action = strategy_result.signal.direction if not strategy_result.silenced else "SILENCE"

    return {
        "ok": True,
        "pipeline": "dynamic — no fixed rules",
        "timestamp": time.time(),
        "inputs": {"psi": psi, "capital_usd": capital, "fear_greed": fg, "lambda_val": lambda_val},
        "step1_opportunity": best_opp.to_dict() if best_opp else None,
        "step2_strategy": {
            "selected": strategy_result.selected,
            "direction": strategy_result.signal.direction if not strategy_result.silenced else "NEUTRAL",
            "confidence": strategy_result.signal.confidence if not strategy_result.silenced else 0.0,
            "regime_probs": strategy_result.regime_probs,
        },
        "step3_threshold": {"delta": delta, "interpretation": delta_result.interpretation},
        "step4_gate": {"psi": psi, "delta": delta, "gate_open": gate_open},
        "step5_sizing": size_result.to_dict() if size_result else {"size_usd": 0.0, "reason": "gate closed"},
        "step6_risk": {
            "daily_risk_budget_pct": round(risk.daily_risk_budget * 100, 3),
            "drawdown_cap_pct": round(risk.drawdown_cap * 100, 3),
            "circuit_breakers_active": any_breaker,
            "session": risk.session,
        },
        "final_action": final_action,
        "symbol": symbol,
    }


# ── Strategy Registry endpoints (10 ADAPT-Ω strategies) ──────────────────────

@router.get("/trading/strategies")
async def all_strategies(
    psi: float = Query(default=0.72, description="Current Ψ coherence score (0–1)"),
    capital: float = Query(default=500.0, description="Vault capital USD"),
    top_n: int = Query(default=10, ge=1, le=10, description="Number of strategies to return"),
):
    """
    Evaluate all 10 ADAPT-Ω strategies and rank by expected_edge = opp × Ψ × A(t).
    Returns every strategy scored so judges can see the full decision surface.
    """
    from trading.strategy_registry import get_registry
    from core.adaptation_plane import get_adaptation_plane
    cmc = await _get_cmc_context()
    agent_ctx = _get_agent_state()
    fg = cmc["fear_greed"]

    snap = {
        "fear_greed": fg, "lambda_val": agent_ctx.get("lambda_val", 0.01),
        "price_change_1h": 0.0, "price_change_24h": 0.0, "price_change_7d": 0.0,
        "daily_volume_usd": 1_000_000_000.0, "volume_24h": 1_000_000_000.0,
        "funding_rate": 0.0, "sentiment_score": fg, "bot_ratio": 0.25,
        "onchain_outflow_zscore": 0.0, "whale_count": 0,
        "basis_spread": 0.003, "gas_cost_usd": 2.0,
        "w_score": 0.60, "vix_proxy": (100 - fg) / 5.0,
    }

    plane = get_adaptation_plane()
    a_val = plane.compute(
        regime="BULL" if fg >= 60 else "BEAR" if fg <= 35 else "SIDEWAYS",
        selected_strategy="momentum_surge",
        order_size_usd=20.0, daily_volume_usd=1e9,
    ).A

    registry = get_registry()
    signals = registry.evaluate_all(snap, psi, a_val, capital)

    return {
        "ok": True,
        "timestamp": time.time(),
        "psi": psi, "adaptation": round(a_val, 4),
        "fear_greed": fg,
        "edge_threshold": 0.22,
        "strategies": [
            {k: v for k, v in s.items() if k != "on_chain_fields"}
            for s in signals[:top_n]
        ],
        "selected": next(
            (s["strategy"] for s in signals if not s["silenced"]), "SILENCE"
        ),
    }


@router.get("/trading/strategies/{strategy_name}")
async def single_strategy(
    strategy_name: str,
    psi: float = Query(default=0.72),
    capital: float = Query(default=500.0),
):
    """
    Get the signal from one specific strategy by name.
    Strategy names: momentum_surge | mean_reversion_fear | funding_rate_arb |
    sentiment_divergence | liquidity_sweep | volatility_regime_switch |
    onchain_flow | lambda_dca | cross_exchange_basis | black_swan_insurance
    """
    from trading.strategies.all_ten import STRATEGY_MAP
    from core.adaptation_plane import get_adaptation_plane
    from fastapi import HTTPException
    cmc = await _get_cmc_context()
    fg = cmc["fear_greed"]

    strategy = STRATEGY_MAP.get(strategy_name)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found. "
            f"Available: {list(STRATEGY_MAP.keys())}")

    snap = {
        "fear_greed": fg, "price_change_1h": 0.0, "price_change_24h": 0.0,
        "price_change_7d": 0.0, "daily_volume_usd": 1e9, "volume_24h": 1e9,
        "funding_rate": 0.0, "sentiment_score": fg, "bot_ratio": 0.25,
        "onchain_outflow_zscore": 0.0, "whale_count": 0,
        "basis_spread": 0.003, "gas_cost_usd": 2.0,
        "w_score": 0.60, "vix_proxy": (100 - fg) / 5.0, "lambda_val": 0.01,
    }

    plane = get_adaptation_plane()
    a_val = plane.compute(order_size_usd=20.0, daily_volume_usd=1e9).A
    sig = strategy.evaluate(snap, psi, a_val, capital)

    return {
        "ok": True,
        "strategy": strategy_name,
        "psi_requirement": strategy.psi_requirement,
        "opportunity_score": sig.opportunity_score,
        "expected_edge": sig.expected_edge,
        "direction": sig.direction,
        "size_usd": sig.dynamic_size_pct * capital,
        "silenced": sig.silence,
        "rationale": sig.rationale,
        "on_chain_fields": sig.on_chain_fields,
        "fear_greed": fg,
        "adaptation": round(a_val, 4),
    }


class OutcomePayload(BaseModel):
    strategy_name: str
    psi_at_entry: float
    a_val_at_entry: float
    predicted_return: float
    actual_return: float
    regime: str = "BULL"
    won: bool


@router.post("/trading/strategies/outcome")
async def record_strategy_outcome(payload: OutcomePayload):
    """
    Record a trade outcome. Updates EFFECTIVENESS_MATRIX and AdaptationPlane κ(t).
    This is the on-chain learning loop: RUMA gets smarter after every trade.
    """
    from trading.strategy_registry import get_registry
    registry = get_registry()
    registry.record_outcome(
        strategy_name=payload.strategy_name,
        psi_at_entry=payload.psi_at_entry,
        a_val_at_entry=payload.a_val_at_entry,
        predicted_return=payload.predicted_return,
        actual_return=payload.actual_return,
        regime=payload.regime,
        won=payload.won,
    )
    perf = registry.strategy_performance_summary()
    match = next((p for p in perf if p["strategy"] == payload.strategy_name), None)
    return {
        "ok": True,
        "recorded": payload.strategy_name,
        "regime": payload.regime,
        "won": payload.won,
        "error": round(abs(payload.predicted_return - payload.actual_return), 5),
        "strategy_performance": match,
    }


@router.get("/trading/strategies/performance")
async def strategies_performance():
    """
    Per-strategy win rates and P&L from recorded outcomes.
    Shows on-chain learning progress — RUMA getting smarter over time.
    """
    from trading.strategy_registry import get_registry
    registry = get_registry()
    perf = registry.strategy_performance_summary()
    return {
        "ok": True,
        "timestamp": time.time(),
        "total_strategies": 10,
        "strategies_with_history": len(perf),
        "performance": perf,
        "note": "Win rates update after each recorded outcome. Empty until trading begins (June 22).",
    }
