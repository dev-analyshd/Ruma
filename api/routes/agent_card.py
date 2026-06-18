"""
SOVEREIGN-Ω Agent Discovery Card
Implements the A2A (Agent-to-Agent) discovery protocol.
Exposes /.well-known/agent.json and /.well-known/skills.json for Anvita Flow registry.
"""
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _base_url(request: Request = None) -> str:
    """
    Resolve the public base URL with proper priority:
    1. SOVEREIGN_URL  — manual override (set in Render dashboard)
    2. RENDER_EXTERNAL_URL — auto-set by Render for every web service
    3. REPLIT_DEV_DOMAIN — auto-set in Replit dev environment
    4. Host header from incoming request (works behind any proxy)
    5. localhost fallback
    """
    # Manual override wins
    override = os.getenv("SOVEREIGN_URL", "").rstrip("/")
    if override:
        return override

    # Render sets this automatically
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        return render_url

    # Replit dev domain
    replit = os.getenv("REPLIT_DEV_DOMAIN", "")
    if replit:
        return f"https://{replit}"

    # Fall back to request host header (works behind nginx, Render, etc.)
    if request:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host   = request.headers.get("x-forwarded-host", request.url.netloc)
        if host and not host.startswith("localhost"):
            return f"{scheme}://{host}"

    port = os.getenv("PORT", "8000")
    return f"http://localhost:{port}"


def _agent_card(base_url: str) -> dict:
    """Build the agent card. Always uses the resolved public base URL."""
    return {
        "schema_version": "1.0",
        "name": "SOVEREIGN-Ω",
        "description": (
            "Autonomous intelligence agent governed by TRION mathematics. "
            "Ω(a,t) = [Ψ(t) ≥ Δ(t)] · R(a,t) · e^(Λ·t). "
            "Truth or silence — the silence is information. "
            "Native Pharos chain agent with compounding moat, silence protocol, "
            "multi-plane cognitive reasoning, and x402 payment-gated premium skills."
        ),
        "version": "2.0.0",
        "url": base_url,
        "dashboard_url": f"{base_url}/dashboard",
        "capabilities": {
            "skills": True,
            "mcp": True,
            "x402": True,
            "a2a": True,
            "streaming": True,
            "sse": True,
            "federation": True,
            "push_notifications": False,
        },
        "streaming_urls": {
            "intelligence": f"{base_url}/api/v1/stream/intelligence",
            "heartbeat":    f"{base_url}/api/v1/stream/heartbeat",
            "moat":         f"{base_url}/api/v1/stream/moat",
            "actions":      f"{base_url}/api/v1/stream/actions",
            "dashboard":    f"{base_url}/api/v1/stream/dashboard",
        },
        "federation_urls": {
            "announce":  f"{base_url}/api/v1/federation/announce",
            "invite":    f"{base_url}/api/v1/federation/invite",
            "handshake": f"{base_url}/api/v1/federation/handshake",
            "peers":     f"{base_url}/api/v1/federation/peers",
            "broadcast": f"{base_url}/api/v1/federation/broadcast",
        },
        "skills_url":  f"{base_url}/api/v1/skills",
        "invoke_url":  f"{base_url}/api/v1/skills/invoke/{{skill_id}}",
        "health_url":  f"{base_url}/api/v1/health",
        "mcp_url":     f"{base_url}/api/v1/mcp",
        "chain": {
            "name": "Pharos",
            "network": os.getenv("PHAROS_NETWORK", "testnet"),
            "chain_id_testnet": 688689,
            "chain_id_mainnet": 1672,
            "contracts": {
                "registry": os.getenv("PHAROS_REGISTRY", ""),
                "vault":    os.getenv("PHAROS_VAULT", ""),
                "learner":  os.getenv("PHAROS_LEARNER", ""),
            },
        },
        "x402": {
            "enabled": True,
            "accepted_tokens": ["PROS", "USDC"],
            "facilitator": "https://facilitator.pharos.xyz",
            "network": os.getenv("PHAROS_NETWORK", "testnet"),
        },
        "security": {
            "certik_scan_compliant": True,
            "certik_scan_submitted": False,
            "silence_protocol": True,
            "coherence_gated": True,
            "private_key_env_only": True,
        },
        "cognitive_model": {
            "framework": "TRION",
            "planes": ["Perceptual", "Inferential", "Consensus", "Self-Reflection", "World-Model"],
            "weights": {"P": 0.25, "I": 0.30, "C": 0.20, "S": 0.15, "W": 0.10},
            "formula": "Psi(t) = 0.25*P + 0.30*I + 0.20*C + 0.15*S + 0.10*W",
        },
        "moat": {
            "formula": "log(Lambda(t)) = log(Lambda_0) + Sum log(1 + eta_i * rho_i)",
            "lambda_0": 1.0,
            "monotonic": True,
        },
        "provider": {
            "organization": "SOVEREIGN-Ω",
            "contact":      "",
        },
    }


@router.get("/.well-known/agent.json", include_in_schema=False)
async def agent_card(request: Request):
    """A2A agent discovery card. Used by Anvita Flow and agent registries."""
    return JSONResponse(content=_agent_card(_base_url(request)))


@router.get("/.well-known/skills.json", include_in_schema=False)
async def skills_manifest(request: Request):
    """Skills manifest for MCP/Anvita Flow skill registry."""
    from api.routes.skills import SKILLS_MANIFEST
    base = _base_url(request)
    manifest = dict(SKILLS_MANIFEST)
    manifest["base_url"]       = base
    manifest["agent_card_url"] = f"{base}/.well-known/agent.json"
    return JSONResponse(content=manifest)


@router.get("/api/v1/agent/discover")
async def discover_agent(request: Request):
    """Agent self-discovery endpoint for Anvita Flow registration."""
    base = _base_url(request)
    card = _agent_card(base)
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer
    moat   = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq     = await scorer.compute()
    return {
        **card,
        "runtime": {
            "lambda":   moat.get_current_lambda(),
            "n_cycles": moat.n_cycles,
            "iq_score": iq,
            "status":   "ONLINE",
        },
    }


@router.get("/api/v1/agent/peers")
async def list_peers():
    """A2A peer listing. Returns known peer agents in the SOVEREIGN-Ω network."""
    return {
        "agent_id": "sovereign-omega",
        "peers": [],
        "peer_discovery": "chain-events",
        "registry": os.getenv("PHAROS_REGISTRY", "not-deployed"),
        "note": "Peer agents discovered via Pharos Registry on-chain events",
    }
