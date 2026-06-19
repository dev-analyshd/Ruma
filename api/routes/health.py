import os
from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health")
async def health():
    from core.moat_accumulator import MoatAccumulator
    from learning.intelligence_score import IntelligenceScorer
    moat = MoatAccumulator()
    scorer = IntelligenceScorer()
    iq = await scorer.compute()

    pk = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
    cmc = os.getenv("CMC_API_KEY", "")
    bsc_net = os.getenv("BSC_NETWORK", "mainnet")
    agent_addr = "0xdBbf66CAD621dA3Ec186D18b29a135d2A5d42d20"

    return {
        "status": "RUMA ONLINE",
        "agent": "RUMA",
        "hackathon": "BNB Hack: AI Trading Agent Edition",
        "track": "Track 1 — Autonomous Trading Agents",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lambda": moat.get_current_lambda(),
        "cycles": moat.n_cycles,
        "iq": iq,
        "version": "1.0.0",
        "chain": "BNB Smart Chain (BSC)",
        "chain_id": 56,
        "network": bsc_net,
        "execution_layer": "Trust Wallet Agent Kit (TWAK)",
        "market_data": "CoinMarketCap AI Agent Hub",
        "competition_contract": "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
        "agent_address": agent_addr,
        "bscscan": f"https://bscscan.com/address/{agent_addr}",
        "twak_key_loaded": bool(pk),
        "cmc_key_loaded": bool(cmc),
        "execution_mode": "LIVE" if bool(pk) else "SIMULATION",
        "bsc_network": bsc_net,
        "skills": 6,
        "cmc_tools": 12,
        "x402_enabled": True,
        "autonomous_demo": "/api/v1/autonomous/demo",
        "competition_checklist": "/api/v1/competition/checklist",
    }
