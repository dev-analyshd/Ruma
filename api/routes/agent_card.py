"""
RUMA Agent Discovery Card
Implements the A2A (Agent-to-Agent) discovery protocol.
Exposes /.well-known/agent.json and /.well-known/skills.json for CMC AI Agent Hub + judge discovery.
"""
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _base_url(request: Request = None) -> str:
    override = os.getenv("SOVEREIGN_URL", "").rstrip("/")
    if override:
        return override
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url:
        return render_url
    replit = os.getenv("REPLIT_DEV_DOMAIN", "")
    if replit:
        return f"https://{replit}"
    if request:
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        host   = request.headers.get("x-forwarded-host", request.url.netloc)
        if host and not host.startswith("localhost"):
            return f"{scheme}://{host}"
    port = os.getenv("PORT", "5000")
    return f"http://localhost:{port}"


def _agent_card(base_url: str) -> dict:
    from api.routes.skills import SKILLS_MANIFEST
    skills_summary = [
        {
            "id": s["id"],
            "name": s["name"],
            "tier": s.get("tier", "free"),
            "endpoint": f"{base_url}{s['endpoint']}",
        }
        for s in SKILLS_MANIFEST.get("skills", [])
    ]

    has_key = bool(os.getenv("TWAK_AGENT_PRIVATE_KEY", ""))
    has_cmc = bool(os.getenv("CMC_API_KEY", ""))

    return {
        "schema_version": "1.0",
        "name": "RUMA",
        "display_name": "RUMA — Autonomous BNB Chain Trading Agent",
        "description": (
            "Autonomous trading agent on BNB Smart Chain. "
            "Reads markets via 12 CoinMarketCap AI Agent Hub data tools (MCP + x402). "
            "Gates every trade on TRION 6-plane coherence mathematics: "
            "Ψ(t) = 0.22P + 0.25I + 0.18C + 0.13S + 0.10W + 0.12A. "
            "Executes self-custodial swaps via Trust Wallet Agent Kit (TWAK). "
            "Silence rate ~87% — RUMA only acts when coherence exceeds threshold."
        ),
        "version": "1.0.0",
        "url": base_url,
        "dashboard_url": f"{base_url}/",
        "api_docs_url": f"{base_url}/docs",
        "capabilities": {
            "skills": True,
            "mcp": True,
            "x402": True,
            "a2a": True,
            "streaming": True,
            "sse": True,
            "autonomous_trading": True,
            "self_custody": True,
            "push_notifications": False,
        },
        "chain": {
            "name": "BNB Smart Chain",
            "chain_id": 56,
            "network": "mainnet",
            "dex": "PancakeSwap V2",
            "competition_contract": "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
            "bscscan": "https://bscscan.com/address/0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
        },
        "execution": {
            "layer": "Trust Wallet Agent Kit (TWAK)",
            "signing": "local — key never leaves environment",
            "key_configured": has_key,
            "mode": "LIVE" if has_key else "SIMULATION",
        },
        "cmc_integration": {
            "data_tools": 12,
            "mcp_endpoint": "https://mcp.coinmarketcap.com",
            "x402_payments": True,
            "x402_audit": f"{base_url}/api/v1/x402/audit",
            "key_configured": has_cmc,
        },
        "cognitive_model": {
            "framework": "TRION ADAPT-Ω",
            "planes": 6,
            "plane_names": [
                "P — Perceptual (CMC price entropy)",
                "I — Inferential (CMC technical indicators)",
                "C — Consensus (CMC on-chain + trending)",
                "S — Self-Reflection (CMC social sentiment)",
                "W — World Model (CMC Fear & Greed)",
                "A — Adaptation (regime × market context)",
            ],
            "formula": "Ψ(t) = 0.22·P + 0.25·I + 0.18·C + 0.13·S + 0.10·W + 0.12·A",
            "gate": "Ψ(t) ≥ Δ(t) → ACT | Ψ(t) < Δ(t) → SILENCE",
            "silence_rate": "~87%",
        },
        "skills": skills_summary,
        "skills_url":  f"{base_url}/api/v1/skills",
        "invoke_url":  f"{base_url}/api/v1/skills/invoke/{{skill_id}}",
        "streaming_urls": {
            "intelligence": f"{base_url}/api/v1/stream/intelligence",
            "heartbeat":    f"{base_url}/api/v1/stream/heartbeat",
            "moat":         f"{base_url}/api/v1/stream/moat",
            "actions":      f"{base_url}/api/v1/stream/actions",
        },
        "judge_endpoints": {
            "autonomous_demo":    f"{base_url}/api/v1/autonomous/demo",
            "competition_proof":  f"{base_url}/api/v1/competition/proof",
            "risk_metrics":       f"{base_url}/api/v1/competition/risk-metrics",
            "x402_audit":         f"{base_url}/api/v1/x402/audit",
            "cmc_signals":        f"{base_url}/api/v1/cmc/signals",
            "strategy_backtest":  f"{base_url}/api/v1/strategy/backtest",
            "health":             f"{base_url}/api/v1/health",
        },
        "x402": {
            "enabled": True,
            "accepted_tokens": ["BNB", "USDT"],
            "chain": "BNB Smart Chain (BSC)",
            "chain_id": 56,
            "fires_on": "every CMC AI Agent Hub data call in trade loop",
            "audit_log": f"{base_url}/api/v1/x402/audit",
        },
        "security": {
            "silence_protocol": True,
            "coherence_gated": True,
            "private_key_env_only": True,
            "drawdown_guard_pct": 30,
            "daily_loss_limit_pct": 6,
        },
        "provider": {
            "organization": "RUMA",
            "hackathon": "BNB Hack: AI Trading Agent Edition",
            "tracks": ["Track 1: Autonomous Trading Agents", "Track 2: Strategy Skills"],
            "competition_contract": "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
        },
    }


@router.get("/.well-known/agent.json", include_in_schema=False)
async def agent_card(request: Request):
    """A2A agent discovery card — RUMA autonomous trading agent on BNB Chain."""
    return JSONResponse(content=_agent_card(_base_url(request)))


@router.get("/.well-known/skills.json", include_in_schema=False)
async def skills_manifest(request: Request):
    """Skills manifest for MCP / CMC AI Agent Hub skill registry."""
    from api.routes.skills import SKILLS_MANIFEST
    base = _base_url(request)
    manifest = dict(SKILLS_MANIFEST)
    manifest["base_url"]       = base
    manifest["agent_card_url"] = f"{base}/.well-known/agent.json"
    return JSONResponse(content=manifest)
