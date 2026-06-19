"""
RUMA Contract Deployment Script
================================
Deploys RUMAHeartbeat and RUMAAgentRegistry to BSC mainnet or testnet,
then immediately registers the agent and its 6 skills on-chain.

Usage:
    python3 scripts/deploy_contracts.py --network mainnet
    python3 scripts/deploy_contracts.py --network testnet

Requires:
    TWAK_AGENT_PRIVATE_KEY   (in Replit Secrets or .env)
    CMC_API_KEY              (optional, for price fetch)

Outputs deployed addresses — set these as env vars:
    RUMA_HEARTBEAT_CONTRACT
    RUMA_REGISTRY_CONTRACT
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

# ── Minimal Solidity bytecode compiled via solc (hardcoded from contracts/) ───
# To recompile: solc --bin --abi contracts/RUMAHeartbeat.sol
# These are placeholders; fill in with actual compiled bytecode.
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
        "name": "emitHeartbeat", "outputs": [], "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "id", "type": "uint256"}],
        "name": "getRecord",
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
        "stateMutability": "view", "type": "function",
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
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getAgentRecordCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [], "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view", "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "internalType": "address", "name": "agent",      "type": "address"},
            {"indexed": True,  "internalType": "uint256", "name": "recordId",   "type": "uint256"},
            {"indexed": False, "internalType": "uint32",  "name": "psi_x10000", "type": "uint32"},
            {"indexed": False, "internalType": "uint32",  "name": "lambda_x1e6","type": "uint32"},
            {"indexed": False, "internalType": "uint16",  "name": "iq",         "type": "uint16"},
            {"indexed": False, "internalType": "bool",    "name": "gate_open",  "type": "bool"},
        ],
        "name": "HeartbeatEmitted", "type": "event",
    },
]

REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "name",     "type": "string"},
            {"internalType": "string", "name": "version",  "type": "string"},
            {"internalType": "string", "name": "strategy", "type": "string"},
        ],
        "name": "registerAgent", "outputs": [], "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string",  "name": "skillId",   "type": "string"},
            {"internalType": "string",  "name": "name",      "type": "string"},
            {"internalType": "string",  "name": "tier",      "type": "string"},
            {"internalType": "uint256", "name": "price_wei", "type": "uint256"},
        ],
        "name": "registerSkill", "outputs": [], "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint32", "name": "moat_x1e6",    "type": "uint32"},
            {"internalType": "uint16", "name": "iq",           "type": "uint16"},
            {"internalType": "uint16", "name": "silence_rate", "type": "uint16"},
        ],
        "name": "updateMoat", "outputs": [], "stateMutability": "nonpayable", "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "isRegistered",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "agent", "type": "address"}],
        "name": "getSkillCount",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view", "type": "function",
    },
    {
        "inputs": [], "name": "totalAgents",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view", "type": "function",
    },
]

# ── Compiled bytecode (compile with: solc --bin contracts/RUMAHeartbeat.sol) ──
# Run: pip install py-solc-x; python -c "import solcx; solcx.install_solc('0.8.19')"
# then: solcx.compile_files(['contracts/RUMAHeartbeat.sol'], output_values=['abi','bin'])
HEARTBEAT_BYTECODE = ""   # filled by compile() below if solcx available
REGISTRY_BYTECODE  = ""   # filled by compile() below if solcx available


def _compile() -> tuple[str, str]:
    """Compile Solidity contracts using py-solc-x if available."""
    try:
        from solcx import compile_files, install_solc, get_installed_solc_versions
        versions = get_installed_solc_versions()
        if not versions:
            print("[COMPILE] Installing solc 0.8.19 ...")
            install_solc("0.8.19")
        compiled = compile_files(
            ["contracts/RUMAHeartbeat.sol", "contracts/RUMAAgentRegistry.sol"],
            output_values=["bin"],
            solc_version="0.8.19",
        )
        hb_key = [k for k in compiled if "RUMAHeartbeat" in k][0]
        rg_key = [k for k in compiled if "RUMAAgentRegistry" in k][0]
        hb_bin = compiled[hb_key]["bin"]
        rg_bin = compiled[rg_key]["bin"]
        print(f"[COMPILE] RUMAHeartbeat bytecode: {len(hb_bin)//2} bytes")
        print(f"[COMPILE] RUMAAgentRegistry bytecode: {len(rg_bin)//2} bytes")
        return hb_bin, rg_bin
    except ImportError:
        print("[COMPILE] py-solc-x not installed. Install: pip install py-solc-x")
        print("[COMPILE] Or set HEARTBEAT_BYTECODE / REGISTRY_BYTECODE manually.")
        sys.exit(1)
    except Exception as e:
        print(f"[COMPILE] Error: {e}")
        sys.exit(1)


def _deploy_contract(w3, account, bytecode: str, abi: list, name: str) -> str:
    """Deploy a contract and return its address."""
    print(f"\n[DEPLOY] Deploying {name} ...")
    contract = w3.eth.contract(abi=abi, bytecode="0x" + bytecode)
    nonce = w3.eth.get_transaction_count(account.address)
    tx = contract.constructor().build_transaction({
        "from":     account.address,
        "nonce":    nonce,
        "gasPrice": w3.eth.gas_price,
        "gas":      2_000_000,
        "chainId":  w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"[DEPLOY] Tx sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    addr = receipt.contractAddress
    if receipt.status != 1:
        print(f"[DEPLOY] {name} FAILED — tx reverted")
        sys.exit(1)
    print(f"[DEPLOY] {name} deployed at: {addr}")
    print(f"[DEPLOY] BscScan: https://bscscan.com/address/{addr}")
    return addr


def _register_agent_and_skills(w3, account, registry_addr: str) -> None:
    """Register RUMA agent profile + 6 skills in the registry."""
    from web3 import Web3
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(registry_addr),
        abi=REGISTRY_ABI,
    )

    print("\n[REGISTER] Registering RUMA agent profile ...")
    nonce = w3.eth.get_transaction_count(account.address)
    tx = registry.functions.registerAgent(
        "RUMA",
        "1.0.0",
        "TRION-Psi-6-Plane-Coherence-ADAPT-Omega",
    ).build_transaction({
        "from": account.address, "nonce": nonce,
        "gasPrice": w3.eth.gas_price, "gas": 300_000,
        "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, account.key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    print(f"[REGISTER] Agent registered — tx: {tx_hash.hex()}")

    skills = [
        ("coherence_evaluate", "TRION Coherence Evaluate", "free",    0),
        ("trade_evaluate",     "Trade Evaluate (TWAK)",    "premium", int(0.001 * 1e18)),
        ("strategy_generate",  "CMC Strategy Skill",       "free",    0),
        ("moat_status",        "Moat Status",              "free",    0),
        ("silence_check",      "Silence Check",            "free",    0),
        ("reasoning_chain",    "Reasoning Chain",          "premium", int(0.0005 * 1e18)),
    ]

    for skill_id, skill_name, tier, price in skills:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = registry.functions.registerSkill(
            skill_id, skill_name, tier, price
        ).build_transaction({
            "from": account.address, "nonce": nonce,
            "gasPrice": w3.eth.gas_price, "gas": 200_000,
            "chainId": w3.eth.chain_id,
        })
        signed = w3.eth.account.sign_transaction(tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        print(f"[REGISTER] Skill '{skill_id}' ({tier}) registered — tx: {tx_hash.hex()}")
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Deploy RUMA contracts to BSC")
    parser.add_argument("--network", choices=["mainnet", "testnet"], default="testnet")
    args = parser.parse_args()

    pk = os.getenv("TWAK_AGENT_PRIVATE_KEY", "")
    if not pk:
        print("ERROR: TWAK_AGENT_PRIVATE_KEY not set")
        sys.exit(1)

    from web3 import Web3
    from eth_account import Account

    rpc = (
        "https://bsc-dataseed.binance.org"
        if args.network == "mainnet"
        else "https://data-seed-prebsc-1-s1.binance.org:8545"
    )
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 30}))
    if not w3.is_connected():
        print(f"ERROR: Cannot connect to {rpc}")
        sys.exit(1)

    acct = Account.from_key(pk)
    bal  = w3.from_wei(w3.eth.get_balance(acct.address), "ether")
    print(f"\n[DEPLOY] Network:  BSC {args.network}")
    print(f"[DEPLOY] Deployer: {acct.address}")
    print(f"[DEPLOY] Balance:  {bal:.6f} BNB")

    if bal < 0.01:
        print("ERROR: Insufficient BNB — need at least 0.01 BNB for deployment gas")
        sys.exit(1)

    # Compile contracts
    hb_bytecode, rg_bytecode = _compile()

    # Deploy
    hb_addr = _deploy_contract(w3, acct, hb_bytecode, HEARTBEAT_ABI, "RUMAHeartbeat")
    rg_addr = _deploy_contract(w3, acct, rg_bytecode, REGISTRY_ABI,  "RUMAAgentRegistry")

    # Register agent and skills
    _register_agent_and_skills(w3, acct, rg_addr)

    # Save to deployment manifest
    manifest = {
        "network":                   args.network,
        "deployer":                  acct.address,
        "deployed_at":               int(time.time()),
        "RUMA_HEARTBEAT_CONTRACT":   hb_addr,
        "RUMA_REGISTRY_CONTRACT":    rg_addr,
        "COMPETITION_CONTRACT":      "0x212c61b9b72c95d95bf29cf032f5e5635629aed5",
        "PANCAKE_ROUTER":            "0x10ED43C718714eb63d5aA57B78B54704E256024E",
        "bscscan_heartbeat":         f"https://bscscan.com/address/{hb_addr}",
        "bscscan_registry":          f"https://bscscan.com/address/{rg_addr}",
    }
    with open("deployment_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE")
    print("="*60)
    print(f"RUMAHeartbeat:    {hb_addr}")
    print(f"RUMAAgentRegistry:{rg_addr}")
    print("\nSet these in Replit Secrets / Render env vars:")
    print(f"  RUMA_HEARTBEAT_CONTRACT={hb_addr}")
    print(f"  RUMA_REGISTRY_CONTRACT={rg_addr}")
    print("\nManifest saved to: deployment_manifest.json")


if __name__ == "__main__":
    main()
