"""
SOVEREIGN-Ω Live Streaming (SSE)
Real-time intelligence feed via Server-Sent Events.
Other agents subscribe to receive live Ψ scores, Λ growth, and intelligence updates.
This is how SOVEREIGN-Ω attracts agents — visibility into its cognitive state.

GET /api/v1/stream/intelligence   — continuous Ψ + Λ + IQ stream
GET /api/v1/stream/moat           — moat growth stream (every accumulation)
GET /api/v1/stream/heartbeat      — 1Hz on-chain heartbeat stream
GET /api/v1/stream/actions        — live action gate decisions
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter()

_action_stream_queue: list = []
_MAX_QUEUE = 1000


def push_action_event(event: dict):
    """Push a gate decision into the live stream queue."""
    _action_stream_queue.append({
        **event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(_action_stream_queue) > _MAX_QUEUE:
        _action_stream_queue.pop(0)


@router.get("/stream/intelligence")
async def stream_intelligence(request: Request):
    """
    SSE: Live TRION intelligence stream.
    Broadcasts Ψ, Λ, IQ every 3 seconds — the agent's cognitive heartbeat.
    Perfect for other agents to monitor SOVEREIGN-Ω's intelligence quality before invoking skills.
    """
    async def generate():
        yield f"data: {json.dumps({'event': 'hello', 'agent': 'SOVEREIGN-Ω', 'framework': 'TRION', 'note': 'Subscribe to live intelligence. Λ never decreases.'})}\n\n"

        i = 0
        while True:
            try:
                if await request.is_disconnected():
                    break

                from core.moat_accumulator import MoatAccumulator
                from learning.intelligence_score import IntelligenceScorer
                from learning.domain_mastery import DomainMasteryEngine

                moat = MoatAccumulator()
                scorer = IntelligenceScorer()
                iq = await scorer.compute()
                domains = DomainMasteryEngine().get_all()

                payload = {
                    "event": "intelligence",
                    "seq": i,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trion": {
                        "lambda": round(moat.get_current_lambda(), 10),
                        "log_lambda": round(moat.log_lambda, 6),
                        "iq_score": round(iq, 8),
                        "n_cycles": moat.n_cycles,
                        "t_normalized": round(moat.get_t_normalized(), 6),
                        "n_domains": len(domains),
                    },
                    "use_me": {
                        "free_skills": ["coherence_evaluate", "moat_status", "silence_check", "intelligence_score"],
                        "invoke_url": "/api/v1/skills/invoke/{skill_id}",
                        "mcp": "/api/v1/mcp",
                        "x402_config": "/api/v1/x402/config",
                    },
                }
                yield f"data: {json.dumps(payload)}\n\n"
                i += 1
                await asyncio.sleep(3)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(3)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/moat")
async def stream_moat(request: Request):
    """
    SSE: Moat growth stream.
    Emits whenever Λ accumulates — every coherent action.
    """
    async def generate():
        from core.moat_accumulator import MoatAccumulator
        moat = MoatAccumulator()
        last_cycles = moat.n_cycles
        last_lambda = moat.get_current_lambda()

        yield f"data: {json.dumps({'event': 'moat_init', 'lambda_0': last_lambda, 'cycles': last_cycles})}\n\n"

        while True:
            try:
                if await request.is_disconnected():
                    break

                await asyncio.sleep(1)
                moat = MoatAccumulator()
                current_cycles = moat.n_cycles
                current_lambda = moat.get_current_lambda()

                if current_cycles != last_cycles:
                    growth = current_lambda / last_lambda if last_lambda > 0 else 1.0
                    yield f"data: {json.dumps({'event': 'moat_growth', 'timestamp': datetime.now(timezone.utc).isoformat(), 'lambda': round(current_lambda, 10), 'lambda_delta': round(current_lambda - last_lambda, 12), 'growth_factor': round(growth, 8), 'cycles': current_cycles, 'new_cycles': current_cycles - last_cycles, 'note': 'Λ never decreases. Every coherent cycle compounds the moat.'})}\n\n"
                    last_cycles = current_cycles
                    last_lambda = current_lambda

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/heartbeat")
async def stream_heartbeat(request: Request):
    """
    SSE: 1Hz on-chain heartbeat.
    SOVEREIGN-Ω's living pulse — proves it's alive on Pharos chain.
    """
    async def generate():
        beat = 0
        while True:
            try:
                if await request.is_disconnected():
                    break

                from core.moat_accumulator import MoatAccumulator
                from core.on_chain_heartbeat import get_sync_stats

                moat = MoatAccumulator()
                stats = get_sync_stats()

                payload = {
                    "event": "heartbeat",
                    "beat": beat,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "alive": True,
                    "lambda": round(moat.get_current_lambda(), 8),
                    "cycles": moat.n_cycles,
                    "chain_syncs": stats["total_chain_syncs"],
                    "next_sync_in": max(0, stats["sync_interval_cycles"] - (moat.n_cycles - stats["last_synced_at_cycle"])),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                beat += 1
                await asyncio.sleep(1)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/dashboard")
async def stream_dashboard(request: Request):
    """
    SSE: Full dashboard state frame every second.
    Replaces the WebSocket feed — works through all proxies including Replit.
    Emits: psi, delta, gate, planes, lambda, log_lambda, cycles, iq, peers, chain_syncs.
    """
    async def generate():
        import uuid as _uuid
        from core.moat_accumulator import MoatAccumulator
        from core.coherence_engine import CoherenceEngine
        from core.action_gate import ActionGate
        from core.on_chain_heartbeat import get_sync_stats
        from learning.intelligence_score import IntelligenceScorer
        from api.routes.federation import _peers

        yield f"data: {json.dumps({'type': 'hello', 'agent': 'SOVEREIGN-Ω', 'transport': 'SSE'})}\n\n"

        seq = 0
        while True:
            try:
                if await request.is_disconnected():
                    break

                moat   = MoatAccumulator()
                scorer = IntelligenceScorer()
                engine = CoherenceEngine()
                gate   = ActionGate()
                iq     = await scorer.compute()

                ctx = {
                    "input_channels": {"dashboard": [float(seq % 10) / 10.0]},
                    "reasoning_chains": [],
                    "environmental_signals": {},
                    "volatility": 0.1,
                    "novelty": 0.2,
                }
                try:
                    scores = await engine.compute_all_planes(
                        "live dashboard pulse", ctx, str(_uuid.uuid4())
                    )
                    planes = {k: round(scores.get(k, 0.0), 6) for k in ("p","i","c","s","w")}
                    psi    = round(scores.get("psi_total", 0.0), 6)
                except Exception:
                    planes = {"p": 0.0, "i": 0.0, "c": 0.0, "s": 0.0, "w": 0.0}
                    psi    = 0.0

                delta      = round(gate.compute_threshold(0.1, 0.2), 4)
                gate_open  = gate.is_open(psi, delta)
                stats      = get_sync_stats()
                lam        = moat.get_current_lambda()
                peer_list  = [
                    {
                        "id": p.get("peer_id", "?"),
                        "name": p.get("name", "unknown"),
                        "status": p.get("status", "active"),
                        "psi": p.get("psi_at_announce") or p.get("their_psi"),
                    }
                    for p in list(_peers.values())[:20]
                ]

                frame = {
                    "type": "state",
                    "seq": seq,
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "psi": psi,
                    "delta": delta,
                    "gate": "OPEN" if gate_open else "SILENCE",
                    "planes": planes,
                    "lambda": lam,
                    "log_lambda": round(moat.log_lambda, 4),
                    "cycles": moat.n_cycles,
                    "iq": round(iq, 4),
                    "chain_syncs": stats["total_chain_syncs"],
                    "next_sync_in": max(
                        0,
                        stats["sync_interval_cycles"]
                        - (moat.n_cycles - stats["last_synced_at_cycle"]),
                    ),
                    "peers": peer_list,
                    "peer_count": len(peer_list),
                }
                yield f"data: {json.dumps(frame)}\n\n"
                seq += 1
                await asyncio.sleep(1)

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/stream/actions")
async def stream_actions(request: Request):
    """
    SSE: Live action gate decisions.
    Every time SOVEREIGN-Ω evaluates an action (ACT or SILENCE), it appears here.
    Agents can watch in real-time to learn when to use SOVEREIGN-Ω's intelligence.
    """
    async def generate():
        last_idx = len(_action_stream_queue)
        yield f"data: {json.dumps({'event': 'connected', 'message': 'Streaming SOVEREIGN-Ω action gate decisions. Every ACT and SILENCE visible here.'})}\n\n"

        while True:
            try:
                if await request.is_disconnected():
                    break

                current_len = len(_action_stream_queue)
                if current_len > last_idx:
                    for event in _action_stream_queue[last_idx:current_len]:
                        yield f"data: {json.dumps(event)}\n\n"
                    last_idx = current_len

                await asyncio.sleep(0.5)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
