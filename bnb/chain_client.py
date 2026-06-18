"""
RUMA — BSC Chain Client
BNB Smart Chain connectivity, balance queries, and on-chain state sync.
All signing via TWAK — self-custody only.
"""
import os
from typing import Optional

BSC_RPC = {
    "mainnet": os.getenv("BSC_RPC_MAINNET", "https://bsc-dataseed.binance.org"),
    "testnet": os.getenv("BSC_RPC_TESTNET", "https://data-seed-prebsc-1-s1.binance.org:8545"),
}
BSC_CHAIN_ID = {"mainnet": 56, "testnet": 97}


class BSCClient:
    def __init__(self):
        self.network = os.getenv("BSC_NETWORK", "testnet")
        self.rpc_url = BSC_RPC.get(self.network, BSC_RPC["testnet"])
        self.chain_id = BSC_CHAIN_ID.get(self.network, 97)
        self._private_key = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
        self.simulation_mode = not bool(self._private_key)
        self.address = self._derive_address()
        self.w3 = None
        self._init_web3()

    def _derive_address(self) -> str:
        if self.simulation_mode:
            return os.getenv("AGENT_OPERATOR_ADDRESS", "0x0000000000000000000000000000000000000000")
        try:
            from eth_account import Account
            return Account.from_key(self._private_key).address
        except Exception:
            return os.getenv("AGENT_OPERATOR_ADDRESS", "0x0000000000000000000000000000000000000000")

    def _init_web3(self):
        try:
            from web3 import Web3
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        except Exception:
            self.w3 = None

    async def is_connected(self) -> bool:
        if self.w3 is None:
            return False
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    async def get_bnb_balance(self) -> float:
        if self.w3 is None or self.simulation_mode:
            return 0.0
        try:
            from web3 import Web3
            return float(Web3.from_wei(self.w3.eth.get_balance(self.address), "ether"))
        except Exception:
            return 0.0

    async def sync_state(self, lambda_val: float, n_cycles: int, iq: float) -> Optional[str]:
        if self.simulation_mode:
            return "0x" + "0" * 64 + "_simulated"
        from bnb.twak_client import TWAKClient
        return await TWAKClient().push_state(lambda_val, n_cycles, iq)
