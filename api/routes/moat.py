"""
Moat routes — RUMA ADAPT-Ω
============================
Exposes Λ(t) — the agent's accumulated moat — including the new
calibration-adjusted growth history introduced in ADAPT-Ω.

GET /moat           — current Λ, projections, calibration history
GET /moat/history   — last N calibration-adjusted cycles
GET /moat/calibrate — record a completed trade outcome (updates κ)
"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from core.moat_accumulator import MoatAccumulator, get_moat
from learning.intelligence_score import IntelligenceScorer
import math

router = APIRouter()


@router.get("/moat")
async def get_moat_state():
    moat = get_moat()
    scorer = IntelligenceScorer()
    iq_data = await scorer.get_breakdown()
    lambda_val = moat.get_current_lambda()
    t_norm = moat.get_t_normalized()

    _MAX_EXP = 700.0
    projections = {}
    for days in [1, 7, 30, 90, 365]:
        t_future = t_norm + days / 30.0
        exp_arg = min(lambda_val * t_future, _MAX_EXP)
        try:
            proj = lambda_val * math.exp(exp_arg)
            projections[f"{days}d"] = proj if math.isfinite(proj) else "∞"
        except OverflowError:
            projections[f"{days}d"] = "∞"

    return {
        "lambda": lambda_val,
        "log_lambda": moat.log_lambda,
        "n_cycles": moat.n_cycles,
        "t_normalized": t_norm,
        "iq_score": iq_data["iq_score"],
        "iq_interpretation": iq_data["interpretation"],
        "projections": projections,
        "lambda_0": MoatAccumulator.LAMBDA_0,
        "growth_since_start": lambda_val / MoatAccumulator.LAMBDA_0,
        "formula": "log(Λ(t)) = log(Λ₀) + Σ log(1 + ηᵢ · ρᵢ · Aᵢ)",
        "adapt_omega_note": "Aᵢ = A(t) calibration score — calibrated actions compound faster",
        "monotonic": True,
        "calibration": {
            "avg_calibration": round(moat.avg_calibration(), 4),
            "calibration_trend": moat.calibration_trend(),
        },
        "recent_cycles": moat.history_tail(5),
    }


@router.get("/moat/history")
async def get_moat_history(n: int = Query(default=20, le=100)):
    moat = get_moat()
    return {
        "ok": True,
        "n_cycles": moat.n_cycles,
        "lambda": moat.get_current_lambda(),
        "avg_calibration": round(moat.avg_calibration(), 4),
        "calibration_trend": moat.calibration_trend(),
        "history": moat.history_tail(n),
        "formula": "Each cycle: Δlog(Λ) = log(1 + η · ρ · A)",
    }


class TradeOutcomeRequest(BaseModel):
    predicted_return: float   # What the agent expected (e.g. 0.04 = 4%)
    actual_return: float      # What actually happened
    eta: float = 0.05         # Learning rate
    cycle_id: Optional[str] = None


@router.post("/moat/calibrate")
async def record_trade_outcome(req: TradeOutcomeRequest):
    """
    Record a completed trade outcome. Updates:
    1. AdaptationPlane calibration history (κ rolling window)
    2. MoatAccumulator with A(t)-adjusted growth
    """
    from core.adaptation_plane import get_adaptation_plane

    adaptation_plane = get_adaptation_plane()
    adaptation_plane.update_calibration(req.predicted_return, req.actual_return)

    moat = get_moat()
    a_components = adaptation_plane.compute()
    calibration_score = a_components.A

    rho = max(0.0, 1.0 + req.actual_return)  # rho=1 on breakeven, >1 on profit
    cycle = moat.accumulate(
        eta_i=req.eta,
        rho_i=rho,
        calibration_score=calibration_score,
        cycle_id=req.cycle_id or f"trade_{moat.n_cycles}",
    )

    return {
        "ok": True,
        "calibration_updated": True,
        "calibration_score_A": round(calibration_score, 4),
        "moat_cycle": {
            "cycle_id": cycle.cycle_id if cycle else None,
            "rho": round(rho, 4),
            "adjusted_rho": round(cycle.adjusted_rho, 4) if cycle else 0,
            "increment": round(cycle.increment, 8) if cycle else 0,
            "lambda_after": round(cycle.lambda_after, 6) if cycle else moat.get_current_lambda(),
        } if cycle else {"note": "No moat growth (rho or calibration ≤ 0)"},
        "calibration_trend": moat.calibration_trend(),
        "message": "Calibrated actions compound the moat faster than uncalibrated ones.",
    }
