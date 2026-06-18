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
        "execution_layer": "Trust Wallet Agent Kit (TWAK)",
        "market_data": "CoinMarketCap AI Agent Hub",
        "competition_contract": "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
    }
