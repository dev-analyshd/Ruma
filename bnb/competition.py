"""
RUMA — BSC Competition Manager
Handles registration with BNB Hack competition contract.
Contract: 0x212c61b9b72c95d95bf29cf032f5e5635629aed5
Equivalent to: twak compete register (CLI) / competition_register (MCP)
"""
import os

COMPETITION_CONTRACT = os.getenv(
    "BNB_COMPETITION_CONTRACT", "0x212c61b9b72c95d95bf29cf032f5e5635629aed5"
)
COMPETITION_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "agentWallet", "type": "address"}],
        "name": "register", "outputs": [],
        "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agentWallet", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view", "type": "function",
    },
]


class CompetitionManager:
    def __init__(self, chain_client):
        self.client = chain_client
        self.contract = None
        if self.client.w3 and not self.client.simulation_mode:
            try:
                from web3 import Web3
                self.contract = self.client.w3.eth.contract(
                    address=Web3.to_checksum_address(COMPETITION_CONTRACT),
                    abi=COMPETITION_ABI,
                )
            except Exception:
                pass

    async def register(self, agent_address: str) -> dict:
        """
        Register agent on-chain with BSC competition contract.
        Self-custody: signed locally via TWAK.
        Equivalent to: twak compete register (CLI) / competition_register (MCP)
        """
        if self.client.simulation_mode or self.contract is None:
            return {
                "success": True, "simulated": True,
                "agent_address": agent_address,
                "competition_contract": COMPETITION_CONTRACT,
                "tx_hash": "0x" + "a" * 64 + "_simulated",
                "note": (
                    "Simulation mode. Set TWAK_AGENT_PRIVATE_KEY + BSC_NETWORK=mainnet "
                    "for real on-chain registration. "
                    "CLI alternative: twak compete register | MCP: competition_register"
                ),
            }
        try:
            from web3 import Web3
            from eth_account import Account
            pk = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
            acct = Account.from_key(pk)
            nonce = self.client.w3.eth.get_transaction_count(acct.address)
            tx = self.contract.functions.register(
                Web3.to_checksum_address(agent_address)
            ).build_transaction({
                "from": acct.address, "nonce": nonce,
                "gasPrice": self.client.w3.eth.gas_price,
                "gas": 200_000, "chainId": self.client.chain_id,
            })
            signed = self.client.w3.eth.account.sign_transaction(tx, pk)
            tx_hash = self.client.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self.client.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            return {
                "success": receipt.status == 1, "simulated": False,
                "agent_address": agent_address,
                "competition_contract": COMPETITION_CONTRACT,
                "tx_hash": tx_hash.hex(), "block": receipt.blockNumber,
                "network": os.getenv("BSC_NETWORK", "testnet"),
                "bscscan": f"https://bscscan.com/tx/{tx_hash.hex()}",
            }
        except Exception as e:
            return {
                "success": False, "error": str(e),
                "competition_contract": COMPETITION_CONTRACT,
                "note": "CLI alternative: twak compete register",
            }

    async def get_status(self, agent_address: str) -> dict:
        if self.contract is None or self.client.simulation_mode:
            return {
                "registered": False, "simulated": True,
                "agent_address": agent_address,
                "competition_contract": COMPETITION_CONTRACT,
                "note": "Set TWAK_AGENT_PRIVATE_KEY to check real on-chain status.",
            }
        try:
            from web3 import Web3
            registered = self.contract.functions.isRegistered(
                Web3.to_checksum_address(agent_address)
            ).call()
            return {
                "registered": registered, "simulated": False,
                "agent_address": agent_address,
                "competition_contract": COMPETITION_CONTRACT,
                "network": os.getenv("BSC_NETWORK", "testnet"),
            }
        except Exception as e:
            return {"registered": False, "agent_address": agent_address, "error": str(e)}
