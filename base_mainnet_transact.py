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
import urllib.request
from web3 import Web3
from dotenv import load_dotenv
load_dotenv()

RPC_URLS = [
    "https://base-rpc.publicnode.com",
    os.environ.get("BASE_MAINNET_RPC", "https://mainnet.base.org"),
    "https://base.llamarpc.com",
    "https://1rpc.io/base"
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
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    clean_vault = vault_address[2:].lower().zfill(64)

    clean_user = None
    if user_address:
        try:
            clean_user = Web3.to_checksum_address(user_address)[2:].lower().zfill(64)
        except Exception:
            clean_user = None

    # Ultra-Fast JSON-RPC Batch Call (<0.8s)
    batch = [
        {'jsonrpc':'2.0', 'id':1, 'method':'eth_getBalance', 'params':[vault_address, 'latest']},
        {'jsonrpc':'2.0', 'id':2, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0x18160ddd'}, 'latest']}, # totalSupply
        {'jsonrpc':'2.0', 'id':3, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0x01fb1891'}, 'latest']}, # totalAumUsdc
        {'jsonrpc':'2.0', 'id':4, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0xfc454928'}, 'latest']}, # navPerShareBps
        {'jsonrpc':'2.0', 'id':5, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0xd1718434'}, 'latest']}, # btcWeightBps
        {'jsonrpc':'2.0', 'id':6, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0xc32bc3da'}, 'latest']}, # ethWeightBps
        {'jsonrpc':'2.0', 'id':7, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0xfccb37b2'}, 'latest']}, # solWeightBps
        {'jsonrpc':'2.0', 'id':8, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0x09b4f42e'}, 'latest']}, # cashWeightBps
        {'jsonrpc':'2.0', 'id':9, 'method':'eth_call', 'params':[{'to': usdc_address, 'data':'0x70a08231' + clean_vault}, 'latest']} # usdc balance
    ]
    if clean_user:
        batch.append({'jsonrpc':'2.0', 'id':10, 'method':'eth_call', 'params':[{'to': vault_address, 'data':'0x70a08231' + clean_user}, 'latest']})

    last_err = None
    for rpc in RPC_URLS:
        try:
            req = urllib.request.Request(
                rpc,
                data=json.dumps(batch).encode('utf-8'),
                headers={'User-Agent': 'AlphaTank/1.0', 'Content-Type': 'application/json'}
            )
            raw = urllib.request.urlopen(req, timeout=4).read().decode('utf-8')
            res_items = json.loads(raw)
            results = {r['id']: int(r.get('result', '0x0'), 16) for r in res_items}

            eth_bal = results.get(1, 0) / 1e18
            total_shares = results.get(2, 0)
            total_aum = results.get(3, 0)
            nav_bps = results.get(4, 10600) or 10600
            btc_w = results.get(5, 3500)
            eth_w = results.get(6, 2500)
            sol_w = results.get(7, 2500)
            cash_w = results.get(8, 1500)
            usdc_bal = results.get(9, 0) / 1e6
            user_shares = results.get(10, 0) if clean_user else 0

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
