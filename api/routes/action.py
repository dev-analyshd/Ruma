import asyncio
import math
import uuid
from fastapi import APIRouter
from api.schemas import ActionRequest, ActionResponse

router = APIRouter()


async def _emit_heartbeat(cycle_id: str, psi: float, gate_open: bool, lambda_val: float):
    try:
        from core.on_chain_heartbeat import emit_action_heartbeat
        await emit_action_heartbeat(cycle_id, psi, gate_open, lambda_val)
    except Exception:
        pass

_coherence_engine = None
_action_gate = None
_moat_acc = None
_silence_protocol = None
_chain_manager = None
_learner = None


def _get_components():
    global _coherence_engine, _action_gate, _moat_acc, _silence_protocol, _chain_manager, _learner
    if _coherence_engine is None:
        from core.coherence_engine import CoherenceEngine
        from core.action_gate import ActionGate
        from core.moat_accumulator import MoatAccumulator
        from core.silence_protocol import SilenceProtocol
        from reasoning.chain_manager import ChainManager
        from learning.continuous_learner import ContinuousLearner
        _coherence_engine = CoherenceEngine()
        _action_gate = ActionGate()
        _moat_acc = MoatAccumulator()
        _silence_protocol = SilenceProtocol()
        _chain_manager = ChainManager()
        _learner = ContinuousLearner()
    return _coherence_engine, _action_gate, _moat_acc, _silence_protocol, _chain_manager, _learner


@router.post("/action", response_model=ActionResponse)
async def evaluate_action(req: ActionRequest):
    coherence_engine, action_gate, moat_acc, silence_protocol, chain_manager, learner = _get_components()
    cycle_id = str(uuid.uuid4())

    reasoning_chains = await chain_manager.run_chains(req.query, req.context)

    if "input_channels" not in req.context:
        import hashlib
        qb = req.query.encode()
        h1 = hashlib.sha256(qb).digest()
        h2 = hashlib.sha256(qb + b"b").digest()
        query_entropy_channel = [b / 255.0 for b in h1]
        context_channel = [b / 255.0 for b in h2[:16]] + [
            req.context.get("volatility", 0.3),
            req.context.get("novelty", 0.5),
            len(req.query) / 500.0,
            len(reasoning_chains) / 10.0,
        ]
        default_channels = {
            "query_entropy": query_entropy_channel,
            "context_signals": context_channel,
        }
    else:
        default_channels = req.context["input_channels"]

    context = {
        **req.context,
        "reasoning_chains": reasoning_chains,
        "input_channels": default_channels,
        "environmental_signals": req.context.get("environmental_signals", {}),
        "volatility": req.context.get("volatility", 0.2),
        "novelty": req.context.get("novelty", 0.5),
    }

    plane_scores = await coherence_engine.compute_all_planes(req.query, context, cycle_id)
    psi = plane_scores["psi_total"]
    delta = action_gate.compute_threshold(plane_scores["volatility"], plane_scores["novelty"])
    gate_open = action_gate.is_open(psi, delta)

    lambda_val = moat_acc.get_current_lambda()
    t_norm = moat_acc.get_t_normalized()

    if not gate_open:
        reason = silence_protocol.log_silence(cycle_id, psi, delta, plane_scores)
        omega = 0.0
        action_output = None
    else:
        best_chain = max(reasoning_chains, key=lambda c: c.get("confidence", 0), default={"response": "No output"})
        action_output = best_chain.get("response", "")
        moat_acc.accumulate(eta_i=0.85, rho_i=psi, cycle_id=cycle_id)
        omega = psi * math.exp(lambda_val * t_norm)
        reason = None

    await learner.learn_from_cycle(
        cycle_id=cycle_id,
        query=req.query,
        action_output=action_output or "",
        gate_open=gate_open,
        domain=req.domain,
        plane_scores=plane_scores,
    )

    # Push to live SSE stream and on-chain heartbeat (fire-and-forget)
    try:
        from api.routes.stream import push_action_event
        push_action_event({
            "cycle_id": cycle_id,
            "gate": "OPEN" if gate_open else "SILENT",
            "psi": round(psi, 4),
            "delta": round(delta, 4),
            "lambda": round(lambda_val, 8),
            "omega": round(omega, 6),
            "domain": req.domain,
            "planes": {"p": round(plane_scores["p"], 4), "i": round(plane_scores["i"], 4),
                       "c": round(plane_scores["c"], 4), "s": round(plane_scores["s"], 4),
                       "w": round(plane_scores["w"], 4)},
        })
        asyncio.create_task(_emit_heartbeat(cycle_id, psi, gate_open, lambda_val))
    except Exception:
        pass

    return ActionResponse(
        cycle_id=cycle_id,
        gate_open=gate_open,
        action_output=action_output,
        silence_reason=reason,
        psi_score=psi,
        delta_threshold=delta,
        lambda_value=lambda_val,
        omega_value=omega,
        plane_breakdown={"p": plane_scores["p"], "i": plane_scores["i"], "c": plane_scores["c"], "s": plane_scores["s"], "w": plane_scores["w"]},
        message="ACTION" if gate_open else "SILENCE",
    )
