"""
Silence Protocol routes — RUMA ADAPT-Ω
========================================
Two-tier gate exposed via REST:
  HARD SILENCE  — Ψ < Δ   → blocked
  SOFT SILENCE  — A < 0.30 → 0.5% max size
  OPEN          — full Φ(a,t) dynamic calibration

POST /silence/query   — full ADAPT-Ω evaluation
GET  /silence/log     — history of silenced queries
GET  /silence/stats   — silence rates + tier breakdown
GET  /silence/adapt   — current A(t) breakdown
"""
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

_silence_log = []


class SilenceQueryRequest(BaseModel):
    query: str
    context: Optional[dict] = {}
    volatility: Optional[float] = 0.2
    novelty: Optional[float] = 0.5
    regime: Optional[str] = "SIDEWAYS"
    selected_strategy: Optional[str] = "MomentumBreakout"
    order_size_usd: Optional[float] = 10.0
    daily_volume_usd: Optional[float] = 50_000_000.0
    fear_greed: Optional[int] = 50
    lambda_val: Optional[float] = 0.01


@router.post("/silence/query")
async def query_silence(req: SilenceQueryRequest):
    """
    Full ADAPT-Ω gate evaluation.
    Returns: Ψ(t), Δ(t), A(t), silence tier, Ω(a,t), and all 6 plane scores.
    """
    from core.coherence_engine import CoherenceEngine
    from core.action_gate import ActionGate
    from core.moat_accumulator import get_moat
    from reasoning.chain_manager import ChainManager
    import hashlib

    coherence_engine = CoherenceEngine()
    action_gate = ActionGate()
    chain_manager = ChainManager()
    moat = get_moat()
    cycle_id = str(uuid.uuid4())

    ctx = req.context or {}
    ctx.update({
        "regime": req.regime,
        "selected_strategy": req.selected_strategy,
        "order_size_usd": req.order_size_usd,
        "daily_volume_usd": req.daily_volume_usd,
        "fear_greed": req.fear_greed,
        "price_change_24h": ctx.get("price_change_24h", 0.0),
        "price_change_7d": ctx.get("price_change_7d", 0.0),
        "volatility": req.volatility,
    })

    reasoning_chains = await chain_manager.run_chains(req.query, ctx)

    qb = req.query.encode()
    h1 = hashlib.sha256(qb).digest()
    h2 = hashlib.sha256(qb + b"b").digest()
    input_channels = {
        "query_entropy": [b / 255.0 for b in h1],
        "context_signals": [b / 255.0 for b in h2[:16]] + [req.volatility, req.novelty],
    }

    context = {
        **ctx,
        "reasoning_chains": reasoning_chains,
        "input_channels": input_channels,
        "environmental_signals": ctx.get("environmental_signals", {}),
    }

    plane_scores = await coherence_engine.compute_all_planes(req.query, context, cycle_id)
    psi = plane_scores["psi_total"]
    adaptation = plane_scores["a"]

    stress = max(0.0, (50 - req.fear_greed) / 50.0)
    delta = action_gate.compute_threshold(
        volatility=req.volatility,
        novelty=req.novelty,
        lambda_val=req.lambda_val,
        stress=stress,
        fear_greed=req.fear_greed,
    )

    gate = action_gate.evaluate(
        psi=psi,
        delta=delta,
        adaptation=adaptation,
        lambda_val=req.lambda_val,
        t_normalized=max(1.0, float(moat.n_cycles)),
    )

    if not gate.action_allowed:
        _silence_log.append({
            "cycle_id": cycle_id,
            "query": req.query[:100],
            "psi": psi,
            "delta": delta,
            "adaptation": adaptation,
            "gate_type": gate.gate_type,
        })

    return {
        "cycle_id": cycle_id,
        "gate_type": gate.gate_type,
        "action_allowed": gate.action_allowed,
        "omega": gate.omega,
        "psi_score": psi,
        "delta_threshold": delta,
        "adaptation_A": adaptation,
        "silence_reason": gate.reason if not gate.action_allowed or gate.gate_type == "SOFT_SILENCE" else None,
        "constraints": {
            "max_size_pct": gate.max_size_pct,
            "daily_risk_cap": gate.daily_risk_cap,
            "strategy_constraint": gate.strategy_constraint,
        } if gate.gate_type != "OPEN" else None,
        "plane_breakdown": {
            "P_perceptual":  round(plane_scores["p"], 4),
            "I_inferential": round(plane_scores["i"], 4),
            "C_consensus":   round(plane_scores["c"], 4),
            "S_self_ref":    round(plane_scores["s"], 4),
            "W_world_model": round(plane_scores["w"], 4),
            "A_adaptation":  round(plane_scores["a"], 4),
        },
        "adaptation_detail": plane_scores.get("adaptation_detail", {}),
        "reasoning_chains": [
            {"chain": c["chain"], "conclusion": c["conclusion"], "confidence": c["confidence"]}
            for c in reasoning_chains
        ],
        "formula": "Ω = [Ψ ≥ Δ] · [A ≥ 0.30] · R · e^(Λ·t) · Φ(a,t)",
    }


@router.get("/silence/adapt")
async def get_adaptation():
    """Current A(t) breakdown — all 4 components of the Adaptation Plane."""
    from core.adaptation_plane import get_adaptation_plane
    plane = get_adaptation_plane()
    result = plane.compute()
    return {
        "ok": True,
        "adaptation": result.to_dict(),
        "formula": "A(t) = σ(κ) · ρ · λ_liq · τ",
        "components": {
            "kappa": "Calibration: 1 - mean(|predicted - actual|)",
            "rho": "Regime fit: effectiveness[strategy][regime]",
            "lambda_liq": "Liquidity: min(1, daily_vol×1% / order_size)",
            "tau": "Temporal: session_liquidity[hour] / max_session_liq",
        },
    }


@router.get("/silence/log")
async def get_silence_log(limit: int = 50):
    return {"silence_log": _silence_log[-limit:], "total": len(_silence_log)}


@router.get("/silence/stats")
async def get_silence_stats():
    from core.moat_accumulator import get_moat
    from core.silence_protocol import get_silence_protocol
    moat = get_moat()
    sp = get_silence_protocol()
    total_cycles = moat.n_cycles + len(_silence_log)
    silence_rate = len(_silence_log) / max(total_cycles, 1)
    protocol_stats = sp.stats()
    return {
        "total_silences": len(_silence_log),
        "total_cycles": total_cycles,
        "silence_rate": round(silence_rate, 4),
        "tier_breakdown": protocol_stats,
        "interpretation": "Silence is information. Higher rate = more discriminating.",
        "tiers": {
            "HARD": "Ψ < Δ — coherence insufficient, no action",
            "SOFT": "A < 0.30 — coherent but miscalibrated, 0.5% max size",
            "OPEN": "Both gates clear — full dynamic Φ(a,t) applies",
        },
    }
