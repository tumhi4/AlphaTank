"""
AlphaTank Capital - Base Mainnet EVM Vault Deployment Script
============================================================
Deploys AlphaTankVault.sol to Coinbase Base Mainnet (Chain ID: 8453).
Uses Official Circle Native USDC (0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913).
"""

import json
import os
import subprocess
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

RPC_URL = os.environ.get("BASE_MAINNET_RPC", "https://mainnet.base.org")
CHAIN_ID = 8453

# Official Native Circle USDC on Base Mainnet
USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# Deployer Key: Strictly from untracked .env or environment variable
DEPLOYER_KEY = os.environ.get("BASE_MAINNET_KEY")

if not DEPLOYER_KEY:
    print("=" * 80)
    print("   ALPHATANK CAPITAL - BASE MAINNET DEPLOYMENT RUNNER")
    print("=" * 80)
    print("\n[!] Setup Required: No BASE_MAINNET_KEY found in environment or .env file.")
    print("For security, mainnet private keys must never be hardcoded into source code.")
    print("\nTo configure your deployment wallet:")
    print("  1. Create a .env file in the project root (it is git-ignored and safe):")
    print("     BASE_MAINNET_KEY=0x<YOUR_PRIVATE_KEY>")
    print("  2. Fund that wallet with 0.002 - 0.005 Base ETH (~$5 - $12 USD).")
    print("  3. Re-run: python deploy_base_mainnet.py\n")
    print("=" * 80)
    exit(1)

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(DEPLOYER_KEY)

print("=" * 80)
print("   ALPHATANK CAPITAL - BASE MAINNET DEPLOYMENT RUNNER")
print("=" * 80)
print(f"Network             : Base Mainnet (Chain ID: {CHAIN_ID})")
print(f"RPC Endpoint        : {RPC_URL}")
print(f"Deployer Address    : {acct.address}")
bal = w3.eth.get_balance(acct.address)
bal_eth = float(w3.from_wei(bal, 'ether'))
print(f"Current ETH Balance : {bal_eth:.6f} ETH")
print("=" * 80)

if bal_eth < 0.00008:
    print("\n[!] Error: Insufficient ETH on Base Mainnet for contract deployment.")
    print(f"Please send at least 0.0001 Base Mainnet ETH to: {acct.address}")
    print("Deployment halted.")
    exit(1)

print("\n1. Ensuring AlphaTankVault compilation...")
if not os.path.exists("contracts/AlphaTankVault.json"):
    compile_cmd = [
        "node", "-e",
        """
        const solc = require('solc');
        const fs = require('fs');
        const src = fs.readFileSync('contracts/AlphaTankVault.sol', 'utf8');
        const input = {
          language: 'Solidity',
          sources: { 'AlphaTankVault.sol': { content: src } },
          settings: { outputSelection: { '*': { '*': ['abi', 'evm.bytecode'] } } }
        };
        const out = JSON.parse(solc.compile(JSON.stringify(input)));
        const contract = out.contracts['AlphaTankVault.sol']['AlphaTankVault'];
        fs.writeFileSync('contracts/AlphaTankVault.json', JSON.stringify({
          abi: contract.abi,
          bytecode: contract.evm.bytecode.object
        }, null, 2));
        console.log('Contract compiled successfully!');
        """
    ]
    subprocess.run(compile_cmd, check=True)

with open("contracts/AlphaTankVault.json", "r") as f:
    artifact = json.load(f)

abi = artifact["abi"]
bytecode = "0x" + artifact["bytecode"]

print("2. Estimating gas and dynamic fees on Base Mainnet...")
contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(acct.address)
estimated_gas = contract.constructor(USDC_BASE_MAINNET, acct.address).estimate_gas({'from': acct.address})
gas_limit = int(estimated_gas * 1.15)

latest_block = w3.eth.get_block('latest')
base_fee = latest_block.get('baseFeePerGas', w3.to_wei('0.005', 'gwei'))
priority_fee = max(w3.eth.max_priority_fee, w3.to_wei('0.001', 'gwei'))
max_fee = int(base_fee * 2.0) + priority_fee

print(f"Estimated Gas: {estimated_gas:,} (Limit: {gas_limit:,})")
print(f"Base Fee: {w3.from_wei(base_fee, 'gwei'):.4f} gwei | Priority Fee: {w3.from_wei(priority_fee, 'gwei'):.4f} gwei | Max Fee: {w3.from_wei(max_fee, 'gwei'):.4f} gwei")

tx = contract.constructor(USDC_BASE_MAINNET, acct.address).build_transaction({
    'chainId': CHAIN_ID,
    'gas': gas_limit,
    'maxFeePerGas': max_fee,
    'maxPriorityFeePerGas': priority_fee,
    'nonce': nonce,
})

signed_tx = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
tx_hex = tx_hash.hex()
if not tx_hex.startswith("0x"):
    tx_hex = "0x" + tx_hex

print(f"\n3. Transaction Broadcasted to Base Mainnet! Tx Hash: {tx_hex}")
print("Waiting for receipt on Base Mainnet L2 block...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
vault_address = receipt.contractAddress

print("\n" + "=" * 80)
print("[SUCCESS] ALPHATANK VAULT SUCCESSFULLY DEPLOYED ON BASE MAINNET!")
print("=" * 80)
print(f"Contract Address : {vault_address}")
print(f"Basescan URL     : https://basescan.org/address/{vault_address}")
print(f"Transaction Hash : https://basescan.org/tx/{tx_hex}")
print(f"Gas Used         : {receipt.gasUsed:,}")
print("=" * 80)

# Save deployment info
deploy_info = {
    "network": "base_mainnet",
    "chainId": CHAIN_ID,
    "vaultAddress": vault_address,
    "txHash": tx_hex,
    "usdcToken": USDC_BASE_MAINNET,
    "deployer": acct.address,
    "basescan": f"https://basescan.org/address/{vault_address}"
}
with open("deployment_base_mainnet.json", "w") as f:
    json.dump(deploy_info, f, indent=2)

print("\nSaved deployment details to deployment_base_mainnet.json!")
