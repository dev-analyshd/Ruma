"""
RUMA x402 Payment Protocol
HTTP 402 Payment Required for machine-to-machine commerce on BSC.
Supports BNB (native) and USDT payments.
Also used natively for CMC AI Agent Hub premium data in the trade loop.
"""
import os
import time
import hashlib
from typing import Optional
from fastapi import APIRouter, Response
from pydantic import BaseModel

router = APIRouter()

BSC_NETWORK = os.getenv("BSC_NETWORK", "testnet")

PAYMENT_TARGETS = {
    "testnet": {
        "chain_id": 97,
        "rpc": "https://data-seed-prebsc-1-s1.binance.org:8545",
        "bnb_address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "usdt_address": "0x337610d27c682E347C9cD60BD4b3b107C9d34dDd",
    },
    "mainnet": {
        "chain_id": 56,
        "rpc": "https://bsc-dataseed.binance.org",
        "bnb_address": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
        "usdt_address": "0x55d398326f99059fF775485246999027B3197955",
    },
}

_verified_payments: dict = {}


class PaymentVerifyRequest(BaseModel):
    tx_hash: str
    skill_id: str
    caller_address: Optional[str] = None
    token: Optional[str] = "BNB"


class PaymentVerifyResponse(BaseModel):
    verified: bool
    tx_hash: str
    skill_id: str
    token: str
    nonce: Optional[str] = None
    expires_at: Optional[int] = None
    message: str


@router.get("/x402/config")
async def x402_config():
    """x402 payment configuration — BNB and USDT on BSC."""
    net = PAYMENT_TARGETS.get(BSC_NETWORK, PAYMENT_TARGETS["testnet"])
    agent_address = _get_agent_address()
    return {
        "version": "1",
        "network": BSC_NETWORK,
        "chain_id": net["chain_id"],
        "chain": "BNB Smart Chain (BSC)",
        "agent_address": agent_address,
        "accepted_tokens": [
            {"symbol": "BNB", "type": "native", "address": net["bnb_address"], "decimals": 18, "network": BSC_NETWORK},
            {"symbol": "USDT", "type": "bep20", "address": net["usdt_address"], "decimals": 18, "network": BSC_NETWORK},
        ],
        "skill_prices": _get_all_skill_prices(),
        "cmc_x402_hub": "https://mcp.coinmarketcap.com",
        "note": "x402 also used natively for CMC AI Agent Hub premium data in RUMA trade loop.",
    }


@router.post("/x402/verify", response_model=PaymentVerifyResponse)
async def verify_payment(req: PaymentVerifyRequest):
    if not req.tx_hash or len(req.tx_hash) < 10:
        return PaymentVerifyResponse(
            verified=False, tx_hash=req.tx_hash, skill_id=req.skill_id,
            token=req.token or "BNB", message="Invalid transaction hash",
        )
    network = os.getenv("BSC_NETWORK", "testnet")
    verified = False
    if network != "mainnet":
        verified = True
        message = "[TESTNET] Payment accepted on BSC testnet."
    else:
        try:
            from bnb.chain_client import BSCClient
            client = BSCClient()
            if client.w3 is None:
                verified = True
                message = "Payment accepted (web3 unavailable)"
            else:
                receipt = client.w3.eth.get_transaction_receipt(req.tx_hash)
                verified = receipt is not None and receipt.status == 1
                message = "Payment verified on BSC mainnet" if verified else "Transaction not found or failed"
        except Exception as e:
            message = f"Verification error: {str(e)}"
    if verified:
        nonce = hashlib.sha256(f"{req.tx_hash}:{req.skill_id}:{time.time()}".encode()).hexdigest()[:32]
        expires_at = int(time.time()) + 300
        _verified_payments[nonce] = {"tx_hash": req.tx_hash, "skill_id": req.skill_id, "expires_at": expires_at}
        return PaymentVerifyResponse(
            verified=True, tx_hash=req.tx_hash, skill_id=req.skill_id,
            token=req.token or "BNB", nonce=nonce, expires_at=expires_at, message=message,
        )
    return PaymentVerifyResponse(
        verified=False, tx_hash=req.tx_hash, skill_id=req.skill_id,
        token=req.token or "BNB", message=message,
    )


@router.get("/x402/status")
async def x402_status():
    active = sum(1 for p in _verified_payments.values() if p["expires_at"] > time.time())
    return {
        "protocol": "x402", "version": "1", "status": "active",
        "network": BSC_NETWORK, "chain": "BNB Smart Chain (BSC)",
        "active_payment_windows": active,
        "supported_tokens": ["BNB", "USDT"],
        "cmc_x402_hub": "https://mcp.coinmarketcap.com",
    }


def _get_agent_address() -> str:
    try:
        from bnb.chain_client import BSCClient
        return BSCClient().address
    except Exception:
        return os.getenv("AGENT_OPERATOR_ADDRESS", "0x0000000000000000000000000000000000000000")


def _get_all_skill_prices() -> dict:
    from api.routes.skills import SKILLS_MANIFEST
    prices = {}
    for skill in SKILLS_MANIFEST["skills"]:
        if skill.get("tier") == "premium":
            prices[skill["id"]] = {
                "BNB": skill.get("x402_price_bnb", "0.001"),
                "USDT": skill.get("x402_price_usdt", "0.10"),
            }
    return prices


def validate_nonce(nonce: str, skill_id: str) -> bool:
    if nonce not in _verified_payments:
        return False
    entry = _verified_payments[nonce]
    if entry["expires_at"] < time.time():
        del _verified_payments[nonce]
        return False
    if entry["skill_id"] != skill_id:
        return False
    return True
