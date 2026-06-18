"""
RUMA — BNB Chain Routes
BSC connection status, competition registration, and on-chain sync.
All signing via Trust Wallet Agent Kit (TWAK) — self-custody only.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

BSC_COMPETITION_CONTRACT = os.getenv(
    "BNB_COMPETITION_CONTRACT", "0x212c61b9b72c95d95bf29cf032f5e5635629aed5"
)


class CompetitionRegisterRequest(BaseModel):
    agent_address: Optional[str] = None


@router.get("/bnb/status")
async def bnb_status():
    """BSC connection status, wallet balance, TWAK connectivity."""
    try:
        from bnb.chain_client import BSCClient
        client = BSCClient()
        connected = await client.is_connected()
        balance = await client.get_bnb_balance()
        return {
            "connected": connected,
            "network": os.getenv("BSC_NETWORK", "testnet"),
            "chain_id": client.chain_id,
            "agent_address": client.address,
            "bnb_balance": balance,
            "competition_contract": BSC_COMPETITION_CONTRACT,
            "twak_mode": "self_custody_local_signing",
            "execution_layer": "Trust Wallet Agent Kit (TWAK)",
        }
    except Exception as e:
        return {
            "connected": False,
            "mode": "simulation",
            "note": f"BSC client not configured: {str(e)}. Set TWAK_AGENT_PRIVATE_KEY.",
            "competition_contract": BSC_COMPETITION_CONTRACT,
        }


@router.post("/bnb/competition/register")
async def competition_register(req: CompetitionRegisterRequest):
    """
    Register RUMA's agent wallet in the BNB Hack competition contract.
    Equivalent to: twak compete register (CLI) / competition_register (MCP)
    Must be called before June 22, 2026.
    """
    try:
        from bnb.chain_client import BSCClient
        from bnb.competition import CompetitionManager
        client = BSCClient()
        comp = CompetitionManager(client)
        agent_addr = req.agent_address or client.address
        result = await comp.register(agent_addr)
        return {
            "registered": result.get("success", False),
            "agent_address": agent_addr,
            "competition_contract": BSC_COMPETITION_CONTRACT,
            "tx_hash": result.get("tx_hash"),
            "bscscan": result.get("bscscan"),
            "network": os.getenv("BSC_NETWORK", "testnet"),
            "note": "Registration confirmed. Trading window: June 22-28, 2026.",
        }
    except Exception as e:
        agent_addr = req.agent_address or os.getenv("AGENT_OPERATOR_ADDRESS", "")
        return {
            "registered": False,
            "agent_address": agent_addr,
            "competition_contract": BSC_COMPETITION_CONTRACT,
            "note": (
                f"Simulation mode: {str(e)}. "
                "Set TWAK_AGENT_PRIVATE_KEY + BSC_NETWORK=mainnet for real on-chain registration. "
                "CLI: twak compete register | MCP: competition_register"
            ),
        }


@router.get("/bnb/competition/status")
async def competition_status():
    """Check if this agent is registered in the competition contract."""
    try:
        from bnb.chain_client import BSCClient
        from bnb.competition import CompetitionManager
        client = BSCClient()
        comp = CompetitionManager(client)
        return await comp.get_status(client.address)
    except Exception as e:
        return {
            "registered": False,
            "agent_address": os.getenv("AGENT_OPERATOR_ADDRESS", ""),
            "competition_contract": BSC_COMPETITION_CONTRACT,
            "error": str(e),
        }


@router.post("/bnb/sync")
async def sync_to_bsc():
    """Push RUMA Λ + IQ state on-chain to BSC."""
    try:
        from bnb.chain_client import BSCClient
        from core.moat_accumulator import MoatAccumulator
        from learning.intelligence_score import IntelligenceScorer
        client = BSCClient()
        moat = MoatAccumulator()
        scorer = IntelligenceScorer()
        iq = await scorer.compute()
        lambda_val = moat.get_current_lambda()
        tx = await client.sync_state(lambda_val, moat.n_cycles, iq)
        return {
            "status": "synced",
            "tx_hash": tx,
            "lambda": lambda_val,
            "n_cycles": moat.n_cycles,
            "iq": iq,
            "chain": "BSC",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bnb/trade/execute")
async def execute_bnb_trade(
    symbol: str = "BNB/USDT",
    direction: str = "LONG",
    size_usd: float = 10.0,
):
    """Execute BSC trade via TWAK (self-custody local signing)."""
    try:
        from bnb.twak_client import TWAKClient
        twak = TWAKClient()
        return await twak.execute_swap(symbol=symbol, direction=direction, size=size_usd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
