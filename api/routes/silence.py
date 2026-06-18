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


@router.post("/silence/query")
async def query_silence(req: SilenceQueryRequest):
    """
    Core Silence Protocol query — evaluates whether a specific action should be silenced.
    Powers the silence_check skill. Returns TRION gate decision + full plane breakdown.
    """
    from core.coherence_engine import CoherenceEngine
    from core.action_gate import ActionGate
    from reasoning.chain_manager import ChainManager
    import hashlib

    coherence_engine = CoherenceEngine()
    action_gate = ActionGate()
    chain_manager = ChainManager()
    cycle_id = str(uuid.uuid4())

    ctx = req.context or {}
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
        "volatility": req.volatility,
        "novelty": req.novelty,
    }

    plane_scores = await coherence_engine.compute_all_planes(req.query, context, cycle_id)
    psi = plane_scores["psi_total"]
    delta = action_gate.compute_threshold(req.volatility, req.novelty)
    gate_open = action_gate.is_open(psi, delta)

    if not gate_open:
        _silence_log.append({
            "cycle_id": cycle_id,
            "query": req.query[:100],
            "psi": psi,
            "delta": delta,
        })

    return {
        "cycle_id": cycle_id,
        "gate_open": gate_open,
        "action": "PROCEED" if gate_open else "SILENCE",
        "psi_score": psi,
        "delta_threshold": delta,
        "silence_reason": None if gate_open else f"Ψ={psi:.4f} < Δ={delta:.4f}",
        "plane_breakdown": {
            "p": plane_scores["p"],
            "i": plane_scores["i"],
            "c": plane_scores["c"],
            "s": plane_scores["s"],
            "w": plane_scores["w"],
        },
    }


@router.get("/silence/log")
async def get_silence_log(limit: int = 50):
    return {"silence_log": _silence_log[-limit:], "total": len(_silence_log)}


@router.get("/silence/stats")
async def get_silence_stats():
    from core.moat_accumulator import MoatAccumulator
    moat = MoatAccumulator()
    total_cycles = moat.n_cycles + len(_silence_log)
    silence_rate = len(_silence_log) / max(total_cycles, 1)
    return {
        "total_silences": len(_silence_log),
        "total_cycles": total_cycles,
        "silence_rate": silence_rate,
        "interpretation": "Silence is information. Higher rate = more discriminating.",
    }
