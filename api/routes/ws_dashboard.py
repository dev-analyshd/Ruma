"""
SOVEREIGN-Ω WebSocket Dashboard Feed
Pushes live state frames every second to the dashboard.
Each frame contains: Ψ score, all 5 planes, Λ, gate decision,
federation peers, on-chain sync stats — everything the visual
dashboard needs rendered in one payload.
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

_connected_dashboards: list[WebSocket] = []


async def _build_frame(seq: int) -> dict:
    """Compute a full live-state frame for the dashboard."""
    from core.moat_accumulator import MoatAccumulator
    from core.coherence_engine import CoherenceEngine
    from core.action_gate import ActionGate
    from core.on_chain_heartbeat import get_sync_stats
    from learning.intelligence_score import IntelligenceScorer
    from api.routes.federation import _peers

    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    engine = CoherenceEngine()
    gate = ActionGate()

    iq = await scorer.compute()

    ctx = {
        "input_channels": {"dashboard": [float(seq % 10) / 10.0]},
        "reasoning_chains": [],
        "environmental_signals": {},
        "volatility": 0.1,
        "novelty": 0.2,
    }

    try:
        scores = await engine.compute_all_planes("live dashboard pulse", ctx, str(uuid.uuid4()))
        planes = {k: round(scores.get(k, 0.0), 6) for k in ("p", "i", "c", "s", "w")}
        psi = round(scores.get("psi_total", 0.0), 6)
    except Exception:
        planes = {"p": 0.0, "i": 0.0, "c": 0.0, "s": 0.0, "w": 0.0}
        psi = 0.0

    delta = round(gate.compute_threshold(0.1, 0.2), 4)
    gate_open = gate.is_open(psi, delta)
    stats = get_sync_stats()
    lam = moat.get_current_lambda()

    peer_list = [
        {
            "id": p.get("peer_id", "?"),
            "name": p.get("name", "unknown"),
            "status": p.get("status", "active"),
            "psi": p.get("psi_at_announce") or p.get("their_psi"),
        }
        for p in list(_peers.values())[:20]
    ]

    return {
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


@router.websocket("/ws/dashboard")
async def dashboard_ws(ws: WebSocket):
    """
    WebSocket: live dashboard feed.
    Streams one state frame per second with the full TRION cognitive snapshot.
    Used exclusively by the /dashboard visual frontend.
    """
    await ws.accept()
    _connected_dashboards.append(ws)
    seq = 0
    try:
        await ws.send_text(json.dumps({
            "type": "hello",
            "agent": "SOVEREIGN-Ω",
            "formula": "Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t)",
            "note": "Streaming live TRION state. Frames arrive every 1 second.",
        }))

        while True:
            frame = await _build_frame(seq)
            await ws.send_text(json.dumps(frame))
            seq += 1
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in _connected_dashboards:
            _connected_dashboards.remove(ws)
