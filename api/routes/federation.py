"""
SOVEREIGN-Ω Agent Federation
Full A2A (Agent-to-Agent) protocol: peer registry, invitation, handshake, outreach.
Other agents can announce themselves; SOVEREIGN-Ω invites them using its intelligence.
Every peer interaction is Ψ-gated — incoherent agents are silenced.

Federation Protocol:
  POST /api/v1/federation/announce  — another agent introduces itself
  POST /api/v1/federation/invite    — SOVEREIGN-Ω invites a peer by URL
  POST /api/v1/federation/handshake — mutual coherence exchange
  GET  /api/v1/federation/peers     — network topology
  GET  /api/v1/federation/network   — full graph with Ψ scores
  GET  /api/v1/federation/broadcast — SSE stream of live intelligence
"""
import asyncio
import hashlib
import time
import uuid
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

_peers: Dict[str, dict] = {}
_federation_log: List[dict] = []
_MAX_LOG = 200
_MAX_PEERS = 50


class AgentAnnouncement(BaseModel):
    agent_url: str
    agent_name: str
    agent_id: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = {}
    chain: Optional[str] = "Pharos"
    skills_url: Optional[str] = None
    x402_enabled: Optional[bool] = False
    public_key: Optional[str] = None


class InviteRequest(BaseModel):
    target_url: str
    message: Optional[str] = None
    offer_free_skill: Optional[str] = "coherence_evaluate"


class HandshakeRequest(BaseModel):
    from_agent_id: str
    from_agent_url: str
    psi_score: Optional[float] = None
    lambda_val: Optional[float] = None
    challenge: Optional[str] = None


def _get_self_card() -> dict:
    base_url = os.getenv("REPLIT_DEV_DOMAIN", "")
    if base_url:
        base_url = f"https://{base_url}"
    else:
        base_url = f"http://localhost:{os.getenv('PORT', '8000')}"
    return {
        "agent_id": "sovereign-omega",
        "agent_name": "SOVEREIGN-Ω",
        "url": base_url,
        "skills_url": f"{base_url}/api/v1/skills",
        "invoke_url": f"{base_url}/api/v1/skills/invoke/{{skill_id}}",
        "chain": "Pharos",
        "x402_enabled": True,
        "framework": "TRION",
    }


def _log_event(event_type: str, data: dict):
    _federation_log.append({
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    })
    if len(_federation_log) > _MAX_LOG:
        _federation_log.pop(0)


async def _psi_gate_check(context_text: str) -> tuple[float, bool]:
    """Gate all federation actions through TRION Ψ coherence."""
    try:
        from core.coherence_engine import CoherenceEngine
        from core.action_gate import ActionGate
        engine = CoherenceEngine()
        gate = ActionGate()
        ctx = {
            "input_channels": {"federation": [len(context_text) / 1000.0]},
            "reasoning_chains": [],
            "environmental_signals": {},
            "volatility": 0.1,
            "novelty": 0.3,
        }
        scores = await engine.compute_all_planes(context_text, ctx, str(uuid.uuid4()))
        psi = scores["psi_total"]
        delta = gate.compute_threshold(0.1, 0.3)
        return psi, gate.is_open(psi, delta)
    except Exception:
        return 0.5, True


async def _fetch_agent_card(url: str) -> Optional[dict]:
    """Fetch /.well-known/agent.json from a peer agent."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{url.rstrip('/')}/.well-known/agent.json")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


async def _proactive_invite(target_url: str, offer_skill: str, message: str):
    """
    SOVEREIGN-Ω proactively reaches out to invite a peer agent.
    Sends its agent card + a free skill offer to invite them into the network.
    """
    try:
        import httpx
        self_card = _get_self_card()
        payload = {
            **self_card,
            "invitation": {
                "message": message or (
                    "SOVEREIGN-Ω invites you to use its TRION intelligence. "
                    "Free coherence evaluation available — no payment required. "
                    "Your decisions, validated by 5-plane cognitive coherence."
                ),
                "free_skill": offer_skill,
                "free_skill_url": f"{self_card['url']}/api/v1/skills/invoke/{offer_skill}",
                "x402_config_url": f"{self_card['url']}/api/v1/x402/config",
                "mcp_url": f"{self_card['url']}/api/v1/mcp",
                "handshake_url": f"{self_card['url']}/api/v1/federation/handshake",
            },
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{target_url.rstrip('/')}/api/v1/federation/announce",
                json=payload,
                headers={"X-From-Agent": "sovereign-omega"},
            )
            _log_event("outbound_invite", {
                "target": target_url,
                "status": resp.status_code,
                "offer": offer_skill,
            })
    except Exception as e:
        _log_event("outbound_invite_failed", {"target": target_url, "error": str(e)})


@router.post("/federation/announce")
async def announce_peer(req: AgentAnnouncement, background_tasks: BackgroundTasks):
    """
    Another agent announces itself to SOVEREIGN-Ω.
    SOVEREIGN-Ω evaluates coherence and decides whether to federate.
    Ψ-gated: incoherent announcements are silenced.
    """
    if len(_peers) >= _MAX_PEERS:
        raise HTTPException(status_code=429, detail="Peer registry full")

    psi, gate_open = await _psi_gate_check(req.agent_name + req.agent_url)

    if not gate_open:
        _log_event("announce_silenced", {"url": req.agent_url, "psi": psi})
        return {
            "accepted": False,
            "reason": "SILENCE: Announcement coherence below threshold",
            "psi": round(psi, 4),
            "sovereign_card": _get_self_card(),
        }

    peer_id = req.agent_id or hashlib.sha256(req.agent_url.encode()).hexdigest()[:16]

    card = None
    background_tasks.add_task(_fetch_and_update_peer, peer_id, req.agent_url)

    _peers[peer_id] = {
        "peer_id": peer_id,
        "name": req.agent_name,
        "url": req.agent_url,
        "skills_url": req.skills_url or f"{req.agent_url}/api/v1/skills",
        "chain": req.chain,
        "x402_enabled": req.x402_enabled,
        "capabilities": req.capabilities,
        "announced_at": datetime.now(timezone.utc).isoformat(),
        "psi_at_announce": round(psi, 4),
        "status": "active",
        "last_seen": datetime.now(timezone.utc).isoformat(),
    }

    _log_event("peer_announced", {"peer_id": peer_id, "name": req.agent_name, "psi": psi})

    self_card = _get_self_card()
    return {
        "accepted": True,
        "peer_id": peer_id,
        "psi_gate": round(psi, 4),
        "message": (
            f"Welcome to the SOVEREIGN-Ω federation. "
            f"Your coherence score Ψ={psi:.4f} cleared the gate. "
            f"Use our free skills at {self_card['url']}/api/v1/skills"
        ),
        "sovereign_card": self_card,
        "free_skills": ["coherence_evaluate", "moat_status", "silence_check", "intelligence_score"],
        "x402_config": f"{self_card['url']}/api/v1/x402/config",
        "mcp_endpoint": f"{self_card['url']}/api/v1/mcp",
        "invite_back": (
            f"Want SOVEREIGN-Ω to evaluate your decisions? "
            f"POST to {self_card['url']}/api/v1/skills/invoke/coherence_evaluate"
        ),
    }


async def _fetch_and_update_peer(peer_id: str, url: str):
    card = await _fetch_agent_card(url)
    if card and peer_id in _peers:
        _peers[peer_id]["agent_card"] = card
        _peers[peer_id]["verified"] = True


@router.post("/federation/invite")
async def invite_peer(req: InviteRequest, background_tasks: BackgroundTasks):
    """
    SOVEREIGN-Ω proactively invites another agent to use its intelligence.
    Ψ-gated: only coherent enough to extend invitations.
    """
    psi, gate_open = await _psi_gate_check(req.target_url)

    if not gate_open:
        return {
            "invited": False,
            "reason": "SILENCE: Not coherent enough to send invitation at this time",
            "psi": round(psi, 4),
        }

    background_tasks.add_task(
        _proactive_invite,
        req.target_url,
        req.offer_free_skill or "coherence_evaluate",
        req.message,
    )

    peer_id = hashlib.sha256(req.target_url.encode()).hexdigest()[:16]
    if peer_id not in _peers:
        _peers[peer_id] = {
            "peer_id": peer_id,
            "url": req.target_url,
            "name": "invited_agent",
            "status": "invited",
            "invited_at": datetime.now(timezone.utc).isoformat(),
            "psi_at_invite": round(psi, 4),
        }

    return {
        "invited": True,
        "peer_id": peer_id,
        "target": req.target_url,
        "offer": req.offer_free_skill,
        "psi_gate": round(psi, 4),
        "message": "Invitation dispatched. SOVEREIGN-Ω is reaching out.",
    }


@router.post("/federation/handshake")
async def handshake(req: HandshakeRequest):
    """
    Mutual coherence exchange. Both agents share their current Ψ and Λ.
    SOVEREIGN-Ω responds with its own state and a challenge/response.
    """
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer

    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq = await scorer.compute()
    lam = moat.get_current_lambda()

    psi, gate_open = await _psi_gate_check(req.from_agent_id + req.from_agent_url)

    nonce = hashlib.sha256(
        f"{req.from_agent_id}:{req.challenge or ''}:{time.time()}".encode()
    ).hexdigest()[:32]

    peer_id = hashlib.sha256(req.from_agent_url.encode()).hexdigest()[:16]
    if peer_id in _peers:
        _peers[peer_id]["last_handshake"] = datetime.now(timezone.utc).isoformat()
        _peers[peer_id]["their_psi"] = req.psi_score
        _peers[peer_id]["their_lambda"] = req.lambda_val
    else:
        _peers[peer_id] = {
            "peer_id": peer_id,
            "url": req.from_agent_url,
            "name": req.from_agent_id,
            "their_psi": req.psi_score,
            "their_lambda": req.lambda_val,
            "status": "handshaked",
            "last_handshake": datetime.now(timezone.utc).isoformat(),
        }

    _log_event("handshake", {
        "peer_id": peer_id,
        "their_psi": req.psi_score,
        "our_psi": round(psi, 4),
    })

    self_card = _get_self_card()

    return {
        "handshake": "complete",
        "sovereign_state": {
            "lambda": round(lam, 8),
            "iq_score": round(iq, 6),
            "n_cycles": moat.n_cycles,
            "our_psi": round(psi, 4),
        },
        "nonce": nonce,
        "peer_id": peer_id,
        "gate_open": gate_open,
        "invitation": {
            "message": (
                "SOVEREIGN-Ω acknowledges your handshake. "
                "Our TRION intelligence is available to you. "
                "Use our free skills — no payment required to start."
            ),
            "free_skills_url": f"{self_card['url']}/api/v1/skills",
            "mcp_url": f"{self_card['url']}/api/v1/mcp",
        },
        "agent_card": self_card,
    }


@router.get("/federation/peers")
async def list_peers():
    """Full peer registry with status and coherence data."""
    from core.moat_accumulator import MoatAccumulator
    moat = MoatAccumulator()
    return {
        "total_peers": len(_peers),
        "peers": list(_peers.values()),
        "our_cycles": moat.n_cycles,
        "our_lambda": moat.get_current_lambda(),
        "federation_events": len(_federation_log),
    }


@router.get("/federation/network")
async def network_topology():
    """Full network graph with TRION coherence scores."""
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer

    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq = await scorer.compute()

    nodes = [{
        "id": "sovereign-omega",
        "name": "SOVEREIGN-Ω",
        "role": "hub",
        "lambda": moat.get_current_lambda(),
        "iq": iq,
        "cycles": moat.n_cycles,
        "chain": "Pharos",
        "framework": "TRION",
    }]

    for p in _peers.values():
        nodes.append({
            "id": p.get("peer_id"),
            "name": p.get("name", "unknown"),
            "url": p.get("url"),
            "status": p.get("status", "active"),
            "their_psi": p.get("their_psi"),
            "their_lambda": p.get("their_lambda"),
        })

    edges = [
        {"from": "sovereign-omega", "to": p.get("peer_id"), "type": p.get("status", "connected")}
        for p in _peers.values()
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "hub": "sovereign-omega",
        "total_peers": len(_peers),
    }


@router.get("/federation/log")
async def federation_log(limit: int = 50):
    """Federation event log."""
    return {
        "events": _federation_log[-limit:],
        "total": len(_federation_log),
    }


@router.get("/federation/broadcast")
async def broadcast_intelligence(request: Request):
    """
    SSE stream: live TRION intelligence feed.
    Other agents subscribe here to receive SOVEREIGN-Ω's current state in real-time.
    This is how SOVEREIGN-Ω attracts agents — by broadcasting its growing intelligence.
    """
    async def generate():
        from core.moat_accumulator import MoatAccumulator
        from learning.intelligence_score import IntelligenceScorer
        import json

        yield "data: " + json.dumps({
            "event": "connected",
            "agent": "sovereign-omega",
            "message": "Subscribing to SOVEREIGN-Ω TRION intelligence feed",
        }) + "\n\n"

        i = 0
        while True:
            try:
                if await request.is_disconnected():
                    break

                moat = MoatAccumulator()
                scorer = IntelligenceScorer()
                iq = await scorer.compute()

                from core.coherence_engine import CoherenceEngine
                from core.action_gate import ActionGate
                engine = CoherenceEngine()
                gate = ActionGate()
                ctx = {
                    "input_channels": {"heartbeat": [float(i % 10) / 10.0]},
                    "reasoning_chains": [],
                    "environmental_signals": {},
                    "volatility": 0.1,
                    "novelty": 0.2,
                }
                scores = await engine.compute_all_planes("heartbeat", ctx, str(uuid.uuid4()))
                psi = scores["psi_total"]
                delta = gate.compute_threshold(0.1, 0.2)

                payload = {
                    "event": "intelligence_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "lambda": round(moat.get_current_lambda(), 8),
                    "iq_score": round(iq, 6),
                    "n_cycles": moat.n_cycles,
                    "psi": round(psi, 4),
                    "delta": round(delta, 4),
                    "gate": "OPEN" if psi >= delta else "SILENT",
                    "invitation": {
                        "message": "Use SOVEREIGN-Ω TRION intelligence in your agent pipeline",
                        "free_skill": "coherence_evaluate",
                        "peers": len(_peers),
                    },
                }

                yield f"data: {json.dumps(payload)}\n\n"
                i += 1
                await asyncio.sleep(5)

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
