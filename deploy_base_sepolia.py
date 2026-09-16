"""
AlphaTank Capital - Base Sepolia EVM Vault Deployment Script
============================================================
Compiles AlphaTankVault.sol and deploys it to Base Sepolia testnet (Chain ID: 84532).
"""

import json
import os
import subprocess
from web3 import Web3

RPC_URL = "https://sepolia.base.org"
CHAIN_ID = 84532

# Official Circle USDC on Base Sepolia
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

# Burner Deployer Key
DEPLOYER_KEY = os.environ.get("BASE_SEPOLIA_KEY", "0xbb0615235d8f801897cb89940e8fddd65e246a911678de41635af65e383c57af")

w3 = Web3(Web3.HTTPProvider(RPC_URL))
acct = w3.eth.account.from_key(DEPLOYER_KEY)

print("=" * 80)
print("   ALPHATANK CAPITAL - BASE SEPOLIA DEPLOYMENT RUNNER")
print("=" * 80)
print(f"Network             : Base Sepolia (Chain ID: {CHAIN_ID})")
print(f"RPC Endpoint        : {RPC_URL}")
print(f"Deployer Address    : {acct.address}")
bal = w3.eth.get_balance(acct.address)
bal_eth = w3.from_wei(bal, 'ether')
print(f"Current ETH Balance : {bal_eth:.6f} ETH")
print("=" * 80)

if bal == 0:
    print("\n❌ Error: Deployer account has 0 ETH on Base Sepolia.")
    print(f"Please send at least 0.005 Base Sepolia ETH to: {acct.address}")
    exit(1)

print("\n1. Compiling AlphaTankVault.sol...")
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

print("2. Broadcasting Deployment Transaction...")
contract = w3.eth.contract(abi=abi, bytecode=bytecode)
nonce = w3.eth.get_transaction_count(acct.address)
estimated_gas = contract.constructor(USDC_BASE_SEPOLIA, acct.address).estimate_gas({'from': acct.address})
gas_limit = int(estimated_gas * 1.25)
print(f"Estimated Gas: {estimated_gas:,} (Limit: {gas_limit:,})")

tx = contract.constructor(USDC_BASE_SEPOLIA, acct.address).build_transaction({
    'chainId': CHAIN_ID,
    'gas': gas_limit,
    'maxFeePerGas': w3.to_wei('0.1', 'gwei'),
    'maxPriorityFeePerGas': w3.to_wei('0.01', 'gwei'),
    'nonce': nonce,
})

signed_tx = acct.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Transaction Broadcasted! Tx Hash: {tx_hash.hex()}")
print("Waiting for receipt on Base Sepolia...")

receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
vault_address = receipt.contractAddress

print("\n" + "=" * 80)
print("🎉 ALPHATANK VAULT DEPLOYED ON BASE SEPOLIA!")
print("=" * 80)
print(f"Contract Address : {vault_address}")
print(f"Basescan URL     : https://sepolia.basescan.org/address/{vault_address}")
print(f"Transaction Hash : https://sepolia.basescan.org/tx/{tx_hash.hex()}")
print("=" * 80)

# Save deployment info
deploy_info = {
    "network": "base_sepolia",
    "chainId": CHAIN_ID,
    "vaultAddress": vault_address,
    "txHash": tx_hash.hex(),
    "usdcToken": USDC_BASE_SEPOLIA,
    "deployer": acct.address,
    "basescan": f"https://sepolia.basescan.org/address/{vault_address}"
}
with open("deployment_base_sepolia.json", "w") as f:
    json.dump(deploy_info, f, indent=2)

print("\nSaved deployment details to deployment_base_sepolia.json!")
