"""
AlphaTank Capital - Base Sepolia On-Chain Transaction Runner
============================================================
Handles automated execution of depositETH and withdrawETH on Base Sepolia.
"""

import sys
import json
import os
from web3 import Web3

RPC_URL = "https://sepolia.base.org"
DEPLOYER_KEY = os.environ.get("BASE_SEPOLIA_KEY", "0xbb0615235d8f801897cb89940e8fddd65e246a911678de41635af65e383c57af")

def get_vault_info():
    with open("deployment_base_sepolia.json") as f:
        data = json.load(f)
    return data["vaultAddress"]

def deposit(amount_eth=0.0005):
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = {
        'from': acct.address,
        'to': vault_address,
        'value': w3.to_wei(amount_eth, 'ether'),
        'data': '0xf6326fb3',  # depositETH()
        'gas': 150000,
        'maxFeePerGas': w3.to_wei('0.15', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('0.01', 'gwei'),
        'nonce': nonce,
        'chainId': 84532
    }
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    
    result = {
        "success": bool(receipt.status == 1),
        "action": "DEPOSIT_ETH",
        "amountEth": amount_eth,
        "txHash": tx_hex,
        "vaultAddress": vault_address,
        "basescan": f"https://sepolia.basescan.org/tx/{tx_hex}"
    }
    print(json.dumps(result))

def withdraw(shares=1):
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]
    vault = w3.eth.contract(address=vault_address, abi=abi)

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = vault.functions.withdrawETH(int(shares)).build_transaction({
        'from': acct.address,
        'gas': 150000,
        'maxFeePerGas': w3.to_wei('0.15', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('0.01', 'gwei'),
        'nonce': nonce,
        'chainId': 84532
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    result = {
        "success": bool(receipt.status == 1),
        "action": "WITHDRAW_ETH",
        "sharesBurned": shares,
        "txHash": tx_hex,
        "vaultAddress": vault_address,
        "basescan": f"https://sepolia.basescan.org/tx/{tx_hex}"
    }
    print(json.dumps(result))

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "deposit"
    val = float(sys.argv[2]) if len(sys.argv) > 2 else (0.0005 if action == "deposit" else 1)
    if action == "deposit":
        deposit(val)
    elif action == "withdraw":
        withdraw(int(val))
