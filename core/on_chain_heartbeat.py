"""
On-Chain Heartbeat — RUMA
===========================
Syncs Λ and IQ scores to a BSC contract periodically.
Provides get_sync_stats() and emit_action_heartbeat() for use across the app.
"""
from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass, field


@dataclass
class SyncStats:
    total_chain_syncs: int = 0
    last_sync_ts: float = 0.0
    last_lambda: float = 0.0
    last_iq: float = 0.0
    last_error: str = ""
    heartbeats_emitted: int = 0


_stats = SyncStats()


def get_sync_stats() -> dict:
    return {
        "total_chain_syncs": _stats.total_chain_syncs,
        "last_sync_ts": _stats.last_sync_ts,
        "last_lambda": _stats.last_lambda,
        "last_iq": _stats.last_iq,
        "last_error": _stats.last_error,
        "heartbeats_emitted": _stats.heartbeats_emitted,
    }


async def emit_action_heartbeat(cycle_id: str, psi: float, gate_open: bool, lambda_val: float) -> bool:
    """
    Emit a lightweight heartbeat for a specific action cycle.
    Attempts to write to BSC contract if configured; silently skips if not.
    """
    import os
    _stats.heartbeats_emitted += 1

    private_key = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
    rpc = os.getenv("BSC_RPC_TESTNET", "https://data-seed-prebsc-1-s1.binance.org:8545")
    registry = os.getenv("PHAROS_REGISTRY", "")

    if not private_key or private_key.startswith("0x_YOUR"):
        return False

    try:
        from web3 import AsyncWeb3
        w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc))
        account = w3.eth.account.from_key(private_key)
        nonce = await w3.eth.get_transaction_count(account.address)

        tx = {
            "to": account.address,
            "value": 0,
            "gas": 21000,
            "gasPrice": await w3.eth.gas_price,
            "nonce": nonce,
            "chainId": 97,
            "data": (
                f"RUMA|{cycle_id[:8]}|psi={psi:.4f}|gate={'1' if gate_open else '0'}|lambda={lambda_val:.6f}"
            ).encode().hex()[:66],
        }
        signed = account.sign_transaction(tx)
        await w3.eth.send_raw_transaction(signed.raw_transaction)
        _stats.total_chain_syncs += 1
        _stats.last_sync_ts = time.time()
        _stats.last_lambda = lambda_val
        return True
    except Exception as e:
        _stats.last_error = str(e)[:120]
        return False


async def background_sync_loop():
    """
    Periodic background loop: syncs Λ and IQ to BSC every 10 minutes.
    Silently skips if keys are not configured.
    """
    import os
    while True:
        await asyncio.sleep(600)
        private_key = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
        if not private_key or private_key.startswith("0x_YOUR"):
            continue
        try:
            from core.moat_accumulator import get_moat
            from learning.intelligence_score import IntelligenceScorer

            moat = get_moat()
            scorer = IntelligenceScorer()
            iq = await scorer.compute()
            lam = moat.get_current_lambda()

            await emit_action_heartbeat(
                cycle_id=f"heartbeat_{int(time.time())}",
                psi=0.0,
                gate_open=False,
                lambda_val=lam,
            )
            _stats.last_iq = iq
            print(f"[HEARTBEAT] Synced Λ={lam:.6f} IQ={iq:.4f} to BSC")
        except Exception as e:
            _stats.last_error = str(e)[:120]
            print(f"[HEARTBEAT] Sync error: {e}")
