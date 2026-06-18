"""
RUMA — Trust Wallet Agent Kit (TWAK) Routes
Self-custody local signing for BSC trades.
Keys never leave environment. TWAK is the sole execution layer.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class SwapRequest(BaseModel):
    symbol: str = "BNB/USDT"
    direction: str = "LONG"
    size_usd: float = 10.0
    slippage_pct: float = 0.5
    max_drawdown_check: bool = True


@router.get("/twak/status")
async def twak_status():
    """TWAK connection, wallet, BSC balance."""
    try:
        from bnb.twak_client import TWAKClient
        return await TWAKClient().get_status()
    except Exception as e:
        return {
            "connected": False,
            "mode": "simulation",
            "execution_layer": "Trust Wallet Agent Kit (TWAK)",
            "self_custody": True,
            "local_signing": True,
            "autonomous_mode": True,
            "note": f"TWAK not configured: {str(e)}. Set TWAK_AGENT_PRIVATE_KEY.",
            "twak_portal": "https://portal.trustwallet.com",
        }


@router.post("/twak/swap")
async def twak_swap(req: SwapRequest):
    """Execute BSC swap via TWAK (self-custody local signing)."""
    try:
        from bnb.twak_client import TWAKClient
        from trading.risk_manager import RiskManager
        if req.max_drawdown_check:
            risk = RiskManager()
            can_trade, reason = risk.can_trade()
            if not can_trade:
                return {"executed": False, "reason": f"Risk gate: {reason}", "self_custody": True}
        return await TWAKClient().execute_swap(
            symbol=req.symbol, direction=req.direction,
            size=req.size_usd, slippage_pct=req.slippage_pct,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twak/portfolio")
async def twak_portfolio():
    """Current BSC portfolio — self-custody agent wallet."""
    try:
        from bnb.twak_client import TWAKClient
        return await TWAKClient().get_portfolio()
    except Exception as e:
        return {
            "agent_address": os.getenv("AGENT_OPERATOR_ADDRESS", ""),
            "portfolio": [],
            "total_usd": 0.0,
            "self_custody": True,
            "execution_layer": "Trust Wallet Agent Kit (TWAK)",
            "note": f"Set TWAK_AGENT_PRIVATE_KEY. Error: {str(e)}",
        }
