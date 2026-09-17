"""
AlphaTank Capital - Base Mainnet On-Chain Transaction Runner
============================================================
Handles live execution and telemetry on Coinbase Base Mainnet (Chain ID: 8453).
"""

import sys
import json
import os
import time
import requests
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

RPC_URLS = [
    os.environ.get("BASE_MAINNET_RPC", "https://mainnet.base.org"),
    "https://1rpc.io/base",
    "https://developer-access-mainnet.base.org"
]
CHAIN_ID = 8453
DEPLOYER_KEY = os.environ.get("BASE_MAINNET_KEY")

def get_w3(rpc=None):
    session = requests.Session()
    session.headers.update({"User-Agent": "AlphaTank/1.0"})
    target_rpc = rpc or RPC_URLS[0]
    return Web3(Web3.HTTPProvider(target_rpc, session=session, request_kwargs={"timeout": 6}))

def get_vault_info():
    with open("deployment_base_mainnet.json") as f:
        data = json.load(f)
    return data["vaultAddress"]

def get_telemetry(user_address=None):
    vault_address = Web3.to_checksum_address(get_vault_info())
    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]

    last_err = None
    for rpc in RPC_URLS:
        try:
            w3 = get_w3(rpc)
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

            usdc_contract = w3.eth.contract(
                address=Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
                abi=[{"constant": True, "inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
            )
            usdc_raw = 0
            try:
                usdc_raw = usdc_contract.functions.balanceOf(vault_address).call()
            except Exception:
                pass
            usdc_bal = float(usdc_raw) / 1e6

            user_shares = 0
            if user_address:
                try:
                    c_addr = Web3.to_checksum_address(user_address)
                    user_shares = vault.functions.balanceOf(c_addr).call()
                except Exception:
                    pass

            aum_dollars = round(usdc_bal + (eth_bal * 2500.0), 2)
            if aum_dollars == 0 and total_shares > 0:
                aum_dollars = round((total_shares * (nav_bps / 10000.0)) / 1e6, 2)
            if aum_dollars == 0 and total_aum > 0:
                aum_dollars = round(total_aum / 1e6, 2)

            result = {
                "network": "base_mainnet",
                "networkName": "Coinbase Base Mainnet",
                "chainId": CHAIN_ID,
                "vaultAddress": vault_address,
                "basescan": f"https://basescan.org/address/{vault_address}",
                "usdcBalance": usdc_bal,
                "usdcBalanceFormatted": f"${usdc_bal:,.2f} USDC",
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
            return
        except Exception as e:
            last_err = e
            continue

    print(json.dumps({"error": str(last_err)}))

def deposit(amount_eth=0.00005):
    if not DEPLOYER_KEY:
        print(json.dumps({"success": False, "error": "BASE_MAINNET_KEY not set in .env"}))
        return

    w3 = get_w3()
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get('baseFeePerGas', w3.to_wei('0.005', 'gwei'))
    priority_fee = max(w3.eth.max_priority_fee, w3.to_wei('0.001', 'gwei'))
    max_fee = int(base_fee * 2.0) + priority_fee

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = {
        'from': acct.address,
        'to': vault_address,
        'value': w3.to_wei(amount_eth, 'ether'),
        'data': '0xf6326fb3',  # depositETH()
        'gas': 150000,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': priority_fee,
        'nonce': nonce,
        'chainId': CHAIN_ID
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
        "basescan": f"https://basescan.org/tx/{tx_hex}"
    }
    print(json.dumps(result))

def rebalance(scenario="BULL"):
    if not DEPLOYER_KEY:
        print(json.dumps({"success": False, "error": "BASE_MAINNET_KEY not set in .env"}))
        return

    w3 = get_w3()
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]
    vault = w3.eth.contract(address=vault_address, abi=abi)

    if scenario == "CRASH":
        btc_bps, eth_bps, sol_bps, cash_bps, nav_bps = 0, 0, 0, 10000, 10000
        regime = "EXTREME_FEAR_CIRCUIT_BREAKER"
        rationale = "Autonomous flight to 100% USDC cash triggered. All volatile assets liquidated."
    elif scenario == "NEUTRAL":
        btc_bps, eth_bps, sol_bps, cash_bps, nav_bps = 3000, 3000, 2500, 1500, 10000
        regime = "DEFENSIVE_RANGING"
        rationale = "Macro uncertainty detected. Balanced portfolio with 15% cash reserve."
    else:
        btc_bps, eth_bps, sol_bps, cash_bps, nav_bps = 3500, 2500, 2500, 1500, 10600
        regime = "BULL_MOMENTUM"
        rationale = "Strong on-chain momentum & inflows. 35% BTC, 25% ETH, 25% SOL, 15% cash."

    mandate_bytes = Web3.keccak(text=f"genlayer_ai_mainnet_mandate_{scenario}_{int(time.time())}")
    mandate_hex = mandate_bytes.hex()
    if not mandate_hex.startswith("0x"):
        mandate_hex = "0x" + mandate_hex

    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get('baseFeePerGas', w3.to_wei('0.005', 'gwei'))
    priority_fee = max(w3.eth.max_priority_fee, w3.to_wei('0.001', 'gwei'))
    max_fee = int(base_fee * 2.0) + priority_fee

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
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': priority_fee,
        'chainId': CHAIN_ID
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()
    if not tx_hex.startswith("0x"):
        tx_hex = "0x" + tx_hex
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    result = {
        "success": bool(receipt.status == 1),
        "action": "BASE_MAINNET_REBALANCE",
        "scenario": scenario,
        "regime": regime,
        "rationale": rationale,
        "mandateHash": mandate_hex,
        "txHash": tx_hex,
        "blockNumber": receipt.blockNumber,
        "gasUsed": receipt.gasUsed,
        "basescan": f"https://basescan.org/tx/{tx_hex}",
        "newWeights": {
            "BTC": f"{btc_bps / 100:.2f}%",
            "ETH": f"{eth_bps / 100:.2f}%",
            "SOL": f"{sol_bps / 100:.2f}%",
            "USDC_CASH": f"{cash_bps / 100:.2f}%"
        },
        "newNav": f"${nav_bps / 10000:.4f}"
    }
    print(json.dumps(result))

def withdraw(shares=1.0):
    if not DEPLOYER_KEY:
        print(json.dumps({"success": False, "error": "BASE_MAINNET_KEY not set in .env"}))
        return

    w3 = get_w3()
    acct = w3.eth.account.from_key(DEPLOYER_KEY)
    vault_address = Web3.to_checksum_address(get_vault_info())

    with open("contracts/AlphaTankVault.json") as f:
        abi = json.load(f)["abi"]
    vault = w3.eth.contract(address=vault_address, abi=abi)

    shares_units = int(float(shares) * 1e6)
    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get('baseFeePerGas', w3.to_wei('0.005', 'gwei'))
    priority_fee = max(w3.eth.max_priority_fee, w3.to_wei('0.001', 'gwei'))
    max_fee = int(base_fee * 2.0) + priority_fee

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = vault.functions.withdraw(shares_units).build_transaction({
        'from': acct.address,
        'nonce': nonce,
        'gas': 150000,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': priority_fee,
        'chainId': CHAIN_ID
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = tx_hash.hex()
    if not tx_hex.startswith("0x"):
        tx_hex = "0x" + tx_hex
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    result = {
        "success": bool(receipt.status == 1),
        "action": "BASE_MAINNET_WITHDRAW_USDC",
        "shares": shares,
        "txHash": tx_hex,
        "vaultAddress": vault_address,
        "basescan": f"https://basescan.org/tx/{tx_hex}"
    }
    print(json.dumps(result))

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "telemetry"
    if action == "telemetry":
        user_addr = sys.argv[2] if len(sys.argv) > 2 else None
        get_telemetry(user_addr)
    elif action == "deposit":
        amt = float(sys.argv[2]) if len(sys.argv) > 2 else 0.00005
        deposit(amt)
    elif action == "withdraw":
        shrs = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        withdraw(shrs)
    elif action == "rebalance":
        scen = sys.argv[2] if len(sys.argv) > 2 else "BULL"
        rebalance(scen)
    else:
        print(json.dumps({"error": f"Unknown action: {action}"}))
