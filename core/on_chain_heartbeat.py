"""
On-Chain Heartbeat — RUMA
===========================
Syncs Ψ, Δ, Λ, and IQ scores to the RUMAHeartbeat BSC contract
every 10 minutes. Creates an immutable developmental record of
the agent's cognitive state on BNB Smart Chain.

Contract: RUMAHeartbeat.sol (deploy with scripts/deploy_contracts.py)
Env:      RUMA_HEARTBEAT_CONTRACT=<deployed_address>
"""
from __future__ import annotations
import asyncio
import hashlib
import os
import time
from dataclasses import dataclass, field


# ── RUMAHeartbeat contract ABI (matches contracts/RUMAHeartbeat.sol) ──────────
HEARTBEAT_ABI = [
    {
        "inputs": [
            {"internalType": "uint32",  "name": "psi_x10000",   "type": "uint32"},
            {"internalType": "uint32",  "name": "delta_x10000", "type": "uint32"},
            {"internalType": "uint32",  "name": "lambda_x1e6",  "type": "uint32"},
            {"internalType": "uint16",  "name": "iq",           "type": "uint16"},
            {"internalType": "bool",    "name": "gate_open",    "type": "bool"},
            {"internalType": "bytes32", "name": "cycle_id",     "type": "bytes32"},
        ],
        "name": "emitHeartbeat",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getLatestAgentRecord",
        "outputs": [{"components": [
            {"internalType": "uint256", "name": "timestamp",    "type": "uint256"},
            {"internalType": "address", "name": "agent",        "type": "address"},
            {"internalType": "uint32",  "name": "psi_x10000",   "type": "uint32"},
            {"internalType": "uint32",  "name": "delta_x10000", "type": "uint32"},
            {"internalType": "uint32",  "name": "lambda_x1e6",  "type": "uint32"},
            {"internalType": "uint16",  "name": "iq",           "type": "uint16"},
            {"internalType": "bool",    "name": "gate_open",    "type": "bool"},
            {"internalType": "bytes32", "name": "cycle_id",     "type": "bytes32"},
        ], "internalType": "struct RUMAHeartbeat.HeartbeatRecord", "name": "", "type": "tuple"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getAgentRecordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "address", "name": "agent",       "type": "address"},
            {"indexed": True,  "internalType": "uint256", "name": "recordId",    "type": "uint256"},
            {"indexed": False, "internalType": "uint32",  "name": "psi_x10000",  "type": "uint32"},
            {"indexed": False, "internalType": "uint32",  "name": "lambda_x1e6", "type": "uint32"},
            {"indexed": False, "internalType": "uint16",  "name": "iq",          "type": "uint16"},
            {"indexed": False, "internalType": "bool",    "name": "gate_open",   "type": "bool"},
        ],
        "name": "HeartbeatEmitted",
        "type": "event",
    },
]


# ── Stats tracker ─────────────────────────────────────────────────────────────

@dataclass
class SyncStats:
    total_chain_syncs: int   = 0
    last_sync_ts: float      = 0.0
    last_psi: float          = 0.0
    last_lambda: float       = 0.0
    last_iq: float           = 0.0
    last_tx: str             = ""
    last_error: str          = ""
    heartbeats_emitted: int  = 0
    contract_address: str    = ""
    fallback_used: int       = 0   # times fell back to self-transfer


_stats = SyncStats()


def get_sync_stats() -> dict:
    return {
        "total_chain_syncs":  _stats.total_chain_syncs,
        "last_sync_ts":       _stats.last_sync_ts,
        "last_psi":           _stats.last_psi,
        "last_lambda":        _stats.last_lambda,
        "last_iq":            _stats.last_iq,
        "last_tx":            _stats.last_tx,
        "last_error":         _stats.last_error,
        "heartbeats_emitted": _stats.heartbeats_emitted,
        "contract_address":   _stats.contract_address or "not deployed",
        "fallback_used":      _stats.fallback_used,
    }


# ── Core emit function ────────────────────────────────────────────────────────

async def emit_action_heartbeat(
    cycle_id: str,
    psi: float,
    gate_open: bool,
    lambda_val: float,
    delta: float = 0.0,
    iq: float = 50.0,
) -> bool:
    """
    Emit a cognitive heartbeat to BSC.

    Priority 1: Call emitHeartbeat() on RUMAHeartbeat contract
                (requires RUMA_HEARTBEAT_CONTRACT to be set after deployment)
    Priority 2: Self-transfer with encoded data in tx.data field
                (fallback when contract not yet deployed)

    Returns True on success, False on failure.
    """
    _stats.heartbeats_emitted += 1

    private_key = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
    if not private_key or private_key.startswith("0x_YOUR"):
        return False

    network       = os.getenv("BSC_NETWORK", "mainnet")
    rpc           = (
        os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org")
        if network == "mainnet"
        else os.getenv("BSC_TESTNET_RPC_URL", "https://data-seed-prebsc-1-s1.binance.org:8545")
    )
    chain_id      = 56 if network == "mainnet" else 97
    contract_addr = os.getenv("RUMA_HEARTBEAT_CONTRACT", "")

    try:
        from web3 import Web3
        from eth_account import Account

        w3   = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
        acct = Account.from_key(private_key)

        # Check balance — skip if unfunded (don't waste gas on failed txs)
        bal = w3.eth.get_balance(acct.address)
        if bal < w3.to_wei(0.0002, "ether"):
            _stats.last_error = "wallet unfunded — skipping heartbeat"
            return False

        nonce = w3.eth.get_transaction_count(acct.address)

        if contract_addr:
            # ── Path 1: Call RUMAHeartbeat contract ───────────────────────────
            _stats.contract_address = contract_addr
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_addr),
                abi=HEARTBEAT_ABI,
            )
            # Encode floats as integers (contract stores fixed-point)
            psi_x10000   = min(int(psi * 10_000),   65535)
            delta_x10000 = min(int(delta * 10_000),  65535)
            lambda_x1e6  = min(int(lambda_val * 1_000_000), 4_294_967_295)
            iq_int       = min(max(int(iq), 0), 200)
            cycle_bytes  = hashlib.keccak_256(cycle_id.encode()).digest()[:32]
            cycle_b32    = bytes(cycle_bytes).ljust(32, b"\x00")

            tx = contract.functions.emitHeartbeat(
                psi_x10000,
                delta_x10000,
                lambda_x1e6,
                iq_int,
                gate_open,
                cycle_b32,
            ).build_transaction({
                "from":     acct.address,
                "nonce":    nonce,
                "gasPrice": w3.eth.gas_price,
                "gas":      100_000,
                "chainId":  chain_id,
            })

        else:
            # ── Path 2: Self-transfer with encoded data (fallback) ────────────
            _stats.fallback_used += 1
            data_str  = (
                f"RUMA|{cycle_id[:8]}|psi={psi:.4f}|delta={delta:.4f}"
                f"|gate={'1' if gate_open else '0'}|lambda={lambda_val:.6f}|iq={iq:.0f}"
            )
            data_hex  = data_str.encode().hex()
            tx = {
                "to":       acct.address,
                "value":    0,
                "gas":      21_000 + len(data_hex) * 4,
                "gasPrice": w3.eth.gas_price,
                "nonce":    nonce,
                "chainId":  chain_id,
                "data":     bytes.fromhex(data_hex),
            }

        signed   = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)

        _stats.total_chain_syncs += 1
        _stats.last_sync_ts      = time.time()
        _stats.last_psi          = psi
        _stats.last_lambda       = lambda_val
        _stats.last_iq           = iq
        _stats.last_tx           = tx_hash.hex()
        return True

    except Exception as e:
        _stats.last_error = str(e)[:120]
        return False


# ── Background sync loop ──────────────────────────────────────────────────────

async def background_sync_loop():
    """
    Periodic background loop: syncs Ψ, Λ, and IQ to BSC every 10 minutes.
    Silently skips if wallet key not configured or balance too low.
    """
    while True:
        await asyncio.sleep(600)   # 10-minute interval
        try:
            from core.moat_accumulator import get_moat
            from learning.intelligence_score import IntelligenceScorer

            moat    = get_moat()
            lam     = moat.get_current_lambda()
            scorer  = IntelligenceScorer()
            iq      = await scorer.compute()

            success = await emit_action_heartbeat(
                cycle_id=f"bg_sync_{int(time.time())}",
                psi=0.0,
                gate_open=False,
                lambda_val=lam,
                delta=0.0,
                iq=iq,
            )
            if success:
                contract_addr = os.getenv("RUMA_HEARTBEAT_CONTRACT", "")
                mode = "contract" if contract_addr else "self-transfer"
                print(f"[HEARTBEAT] Synced Λ={lam:.6f} IQ={iq:.2f} to BSC ({mode}) — tx: {_stats.last_tx[:16]}...")
            else:
                if _stats.last_error:
                    print(f"[HEARTBEAT] Skipped: {_stats.last_error}")
        except Exception as e:
            _stats.last_error = str(e)[:120]
            print(f"[HEARTBEAT] Sync error: {e}")
