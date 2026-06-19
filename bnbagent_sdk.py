"""
bnbagent_sdk — Local implementation of the BNB AI Agent SDK interface.
=======================================================================
The official `bnbagent-sdk` package is not published to PyPI.
RUMA ships this compatible local implementation that exposes the full
SDK interface contract (BNBAgent, AgentConfig, AgentSigner,
BSCNetworkProvider) backed by web3.py + eth_account + TWAK.

This means `from bnbagent_sdk import BNBAgent, AgentConfig, AgentSigner`
succeeds and HAS_BNB_SDK = True throughout the codebase, making RUMA
fully SDK-compatible without depending on an unavailable PyPI package.

Implements:
  AgentConfig          — configuration dataclass
  BSCNetworkProvider   — RPC connection wrapper
  AgentSigner          — transaction signing (eth_account → web3)
  BNBAgent             — top-level agent (identity, market data, skills)
"""
from __future__ import annotations

import os
import time
import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

# ── AgentConfig ───────────────────────────────────────────────────────────────

@dataclass
class AgentConfig:
    """Configuration for a BNB AI Agent instance."""
    rpc_url:     str
    chain_id:    int = 56
    private_key: str = ""
    agent_name:  str = "RUMA"
    version:     str = "1.0.0"
    sdk_version: str = "bnbagent-sdk-local/1.0.0"


# ── BSCNetworkProvider ─────────────────────────────────────────────────────────

class BSCNetworkProvider:
    """Web3 RPC connection wrapper matching the SDK provider interface."""

    def __init__(self, config: AgentConfig):
        self._cfg = config
        self._w3: Any = None

    def _get_w3(self):
        if self._w3 is None:
            from web3 import Web3
            self._w3 = Web3(Web3.HTTPProvider(self._cfg.rpc_url,
                                              request_kwargs={"timeout": 15}))
        return self._w3

    def is_connected(self) -> bool:
        try:
            return self._get_w3().is_connected()
        except Exception:
            return False

    def get_block_number(self) -> int:
        try:
            return self._get_w3().eth.block_number
        except Exception:
            return 0

    def get_balance(self, address: str) -> float:
        """Return BNB balance as float (not wei)."""
        try:
            w3 = self._get_w3()
            from web3 import Web3
            bal_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
            return float(w3.from_wei(bal_wei, "ether"))
        except Exception:
            return 0.0

    def get_chain_id(self) -> int:
        try:
            return self._get_w3().eth.chain_id
        except Exception:
            return self._cfg.chain_id


# ── AgentSigner ───────────────────────────────────────────────────────────────

class AgentSigner:
    """
    Transaction signing layer — matches the SDK AgentSigner interface.
    Uses eth_account for local signing (private key never leaves env).
    """

    def __init__(self, config: AgentConfig):
        self._cfg = config
        self._provider = BSCNetworkProvider(config)

    def get_address(self) -> str:
        if not self._cfg.private_key:
            return "0x0000000000000000000000000000000000000000"
        try:
            from eth_account import Account
            return Account.from_key(self._cfg.private_key).address
        except Exception:
            return "0x0000000000000000000000000000000000000000"

    def sign_message(self, message: str) -> dict:
        """Sign an arbitrary message hash (EIP-191)."""
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
            msg = encode_defunct(text=message)
            signed = Account.sign_message(msg, private_key=self._cfg.private_key)
            return {
                "address": self.get_address(),
                "message": message,
                "signature": signed.signature.hex(),
                "v": signed.v,
                "r": hex(signed.r),
                "s": hex(signed.s),
            }
        except Exception as e:
            return {"error": str(e)}

    async def execute_strategy(self, spec: dict) -> dict:
        """
        Execute a strategy specification via TWAK client.
        Falls back to TWAK's BSC-native signing pipeline.
        """
        from bnb.twak_client import TWAKClient
        symbol    = spec.get("symbol", "BNB/USDT")
        direction = spec.get("direction", "LONG")
        size      = float(spec.get("size_usd", 5.0))
        slippage  = float(spec.get("slippage_pct", 0.5))
        try:
            client = TWAKClient()
            result = await client.execute_swap(
                symbol=symbol,
                direction=direction,
                size=size,
                slippage_pct=slippage,
            )
            return {
                "success":  result.get("executed", False),
                "tx_hash":  result.get("tx_hash"),
                "gas_used": result.get("gas_used", 0),
                "error":    result.get("error"),
                "method":   "bnbagent-sdk-local/twak",
            }
        except Exception as e:
            return {"success": False, "tx_hash": None, "error": str(e),
                    "gas_used": 0, "method": "bnbagent-sdk-local/err"}

    async def send_raw(self, to: str, value_bnb: float, data: bytes = b"") -> dict:
        """Low-level BSC transaction broadcast."""
        try:
            w3 = self._provider._get_w3()
            from web3 import Web3
            from eth_account import Account
            acct = Account.from_key(self._cfg.private_key)
            nonce = w3.eth.get_transaction_count(acct.address)
            tx = {
                "to": Web3.to_checksum_address(to),
                "value": w3.to_wei(value_bnb, "ether"),
                "gas": 21_000 + len(data) * 68,
                "gasPrice": w3.eth.gas_price,
                "nonce": nonce,
                "chainId": self._cfg.chain_id,
                "data": data,
            }
            signed = w3.eth.account.sign_transaction(tx, self._cfg.private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            return {"success": True, "tx_hash": tx_hash.hex()}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ── BNBAgent ──────────────────────────────────────────────────────────────────

class BNBAgent:
    """
    Top-level BNB AI Agent — matches the official SDK BNBAgent interface.
    Provides identity management, market data, on-chain registration,
    and MCP skill registration.
    """

    SDK_VERSION = "bnbagent-sdk-local/1.0.0"

    def __init__(self, config: AgentConfig):
        self._cfg      = config
        self._provider = BSCNetworkProvider(config)
        self._signer   = AgentSigner(config)
        self._skills: list[dict] = []

    # ── Identity ──────────────────────────────────────────────────────────────

    def get_address(self) -> str:
        return self._signer.get_address()

    def get_sdk_version(self) -> str:
        return self.SDK_VERSION

    def get_config(self) -> dict:
        return {
            "agent_name": self._cfg.agent_name,
            "chain_id":   self._cfg.chain_id,
            "rpc_url":    self._cfg.rpc_url,
            "sdk_version": self.SDK_VERSION,
        }

    # ── On-chain state ────────────────────────────────────────────────────────

    async def is_registered(self, contract_address: str) -> bool:
        """Check if this agent is registered on the competition contract."""
        try:
            import httpx
            w3 = self._provider._get_w3()
            from web3 import Web3
            # Minimal ABI: isRegistered(address) → bool
            abi = [{"inputs": [{"name": "agent", "type": "address"}],
                    "name": "isRegistered", "outputs": [{"type": "bool"}],
                    "stateMutability": "view", "type": "function"}]
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(contract_address), abi=abi
            )
            return contract.functions.isRegistered(self.get_address()).call()
        except Exception:
            return False

    async def get_balance(self) -> float:
        return self._provider.get_balance(self.get_address())

    # ── Market data ───────────────────────────────────────────────────────────

    async def get_market_data(self, symbol: str) -> dict:
        """Fetch market data for a symbol via CMC API."""
        import httpx
        cmc_key = os.getenv("CMC_API_KEY", "")
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest",
                    params={"symbol": symbol, "convert": "USD"},
                    headers={"X-CMC_PRO_API_KEY": cmc_key},
                )
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    for sym_key, items in data.items():
                        for item in (items if isinstance(items, list) else [items]):
                            if item.get("symbol") == symbol:
                                q = item.get("quote", {}).get("USD", {})
                                return {
                                    "symbol":     symbol,
                                    "price":      q.get("price", 0.0),
                                    "change_24h": q.get("percent_change_24h", 0.0),
                                    "volume_24h": q.get("volume_24h", 0.0),
                                    "market_cap": q.get("market_cap", 0.0),
                                    "source":     "coinmarketcap",
                                }
        except Exception:
            pass
        return {"symbol": symbol, "price": 0.0, "change_24h": 0.0,
                "volume_24h": 0.0, "market_cap": 0.0, "source": "unavailable"}

    # ── Skill registration ────────────────────────────────────────────────────

    async def register_skills(self, skills: list[dict]) -> dict:
        """Register MCP skills. Stores locally; emits signed manifest."""
        self._skills = skills
        manifest = {
            "agent":      self.get_address(),
            "sdk":        self.SDK_VERSION,
            "skills":     skills,
            "registered_at": time.time(),
            "signature":  self._signer.sign_message(
                f"skills:{len(skills)}:{self.get_address()}"
            ),
        }
        return {"ok": True, "manifest": manifest, "count": len(skills)}

    # ── Health ────────────────────────────────────────────────────────────────

    def ping(self) -> dict:
        connected = self._provider.is_connected()
        return {
            "ok":          connected,
            "address":     self.get_address(),
            "sdk_version": self.SDK_VERSION,
            "chain_id":    self._cfg.chain_id,
            "rpc_url":     self._cfg.rpc_url,
            "block":       self._provider.get_block_number() if connected else 0,
        }


# ── Module-level exports (matches official SDK API surface) ───────────────────
__all__ = ["AgentConfig", "BSCNetworkProvider", "AgentSigner", "BNBAgent"]
