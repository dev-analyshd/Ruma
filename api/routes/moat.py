from fastapi import APIRouter
from core.moat_accumulator import MoatAccumulator
from learning.intelligence_score import IntelligenceScorer
import math

router = APIRouter()


@router.get("/moat")
async def get_moat():
    moat = MoatAccumulator()
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
        "formula": "log(Λ(t)) = log(Λ₀) + Σ log(1 + ηᵢ·ρᵢ)",
        "monotonic": True,
    }
