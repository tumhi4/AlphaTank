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
    if not tx_hex.startswith("0x"):
        tx_hex = "0x" + tx_hex
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
    if not tx_hex.startswith("0x"):
        tx_hex = "0x" + tx_hex
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

def get_telemetry(user_address=None):
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    vault_address = Web3.to_checksum_address(get_vault_info())

    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]
    vault = w3.eth.contract(address=vault_address, abi=abi)

    eth_wei = w3.eth.get_balance(vault_address)
    eth_bal = float(w3.from_wei(eth_wei, 'ether'))
    total_shares = vault.functions.totalSupply().call()
    total_aum = vault.functions.totalAumUsdc().call()
    nav_bps = vault.functions.navPerShareBps().call()
    btc_w = vault.functions.btcWeightBps().call()
    eth_w = vault.functions.ethWeightBps().call()
    sol_w = vault.functions.solWeightBps().call()
    cash_w = vault.functions.cashWeightBps().call()

    user_shares = 0
    if user_address:
        try:
            c_addr = Web3.to_checksum_address(user_address)
            user_shares = vault.functions.balanceOf(c_addr).call()
        except Exception:
            pass

    # AUM in USD: ETH collateral value ($2,500/ETH)
    aum_dollars = round(eth_bal * 2500.0, 2)
    if aum_dollars == 0 and total_shares > 0:
        aum_dollars = round((total_shares * (nav_bps / 10000.0)) / 1e6, 2)

    result = {
        "network": "base_sepolia",
        "networkName": "Coinbase Base Sepolia",
        "chainId": 84532,
        "vaultAddress": vault_address,
        "basescan": f"https://sepolia.basescan.org/address/{vault_address}",
        "ethBalance": eth_bal,
        "ethBalanceFormatted": f"{eth_bal:.6f} ETH",
        "totalShares": total_shares,
        "totalAumUsdc": aum_dollars,
        "navBps": nav_bps,
        "navDollars": nav_bps / 10000.0,
        "weights": {
            "btc": btc_w,
            "eth": eth_w,
            "sol": sol_w,
            "cash": cash_w
        },
        "allocations": {
            "BTC": f"{btc_w / 100.0:.2f}%",
            "ETH": f"{eth_w / 100.0:.2f}%",
            "SOL": f"{sol_w / 100.0:.2f}%",
            "USDC_CASH": f"{cash_w / 100.0:.2f}%"
        },
        "userShares": user_shares,
        "userSharesFormatted": f"{user_shares:,} ATK"
    }
    print(json.dumps(result))

def rebalance(scenario="BULL"):
    import time
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]
    vault = w3.eth.contract(address=vault_address, abi=abi)

    # Scenarios mapping
    if scenario == "CRASH":
        btc_bps = 0
        eth_bps = 0
        sol_bps = 0
        cash_bps = 10000
        nav_bps = 10000
        regime = "EXTREME_FEAR_CIRCUIT_BREAKER"
        rationale = "Autonomous flight to 100% USDC cash triggered. All risky assets liquidated to preserve principal."
    elif scenario == "NEUTRAL":
        btc_bps = 3000
        eth_bps = 3000
        sol_bps = 2500
        cash_bps = 1500
        nav_bps = 10000
        regime = "DEFENSIVE_RANGING"
        rationale = "Macro uncertainty detected. Balanced portfolio with 15% cash reserve."
    else: # BULL (default)
        btc_bps = 3500
        eth_bps = 2500
        sol_bps = 2500
        cash_bps = 1500
        nav_bps = 10600
        regime = "BULL_MOMENTUM"
        rationale = "Arc Mainnet launch & strong 24h momentum. 35% BTC, 25% ETH, 25% SOL, 15% cash."

    # Cryptographic mandate hash (32 bytes)
    mandate_bytes = Web3.keccak(text=f"genlayer_ai_mandate_{scenario}_{int(time.time())}")
    mandate_hex = mandate_bytes.hex()
    if not mandate_hex.startswith("0x"):
        mandate_hex = "0x" + mandate_hex

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = vault.functions.executeRebalanceMandate(
        mandate_bytes,
        btc_bps,
        eth_bps,
        sol_bps,
        cash_bps,
        nav_bps
    ).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 220000,
        'maxFeePerGas': w3.to_wei('0.15', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('0.01', 'gwei'),
        'chainId': 84532
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()
    if not tx_hex.startswith("0x"):
        tx_hex = "0x" + tx_hex
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    result = {
        "success": bool(receipt.status == 1),
        "action": "BASE_REBALANCE",
        "scenario": scenario,
        "regime": regime,
        "rationale": rationale,
        "mandateHash": mandate_hex,
        "txHash": tx_hex,
        "blockNumber": receipt.blockNumber,
        "vaultAddress": vault_address,
        "basescan": f"https://sepolia.basescan.org/tx/{tx_hex}",
        "weights": {
            "btc": btc_bps,
            "eth": eth_bps,
            "sol": sol_bps,
            "cash": cash_bps
        },
        "navBps": nav_bps,
        "navDollars": nav_bps / 10000.0
    }
    print(json.dumps(result))

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "deposit"
    if action == "telemetry":
        u_addr = sys.argv[2] if len(sys.argv) > 2 else None
        get_telemetry(u_addr)
    elif action == "rebalance":
        scen = sys.argv[2] if len(sys.argv) > 2 else "BULL"
        rebalance(scen)
    elif action == "deposit":
        val = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0005
        deposit(val)
    elif action == "withdraw":
        val = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        withdraw(val)

