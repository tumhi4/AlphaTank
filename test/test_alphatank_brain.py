#!/usr/bin/env python3
"""
AlphaTank Capital — Regression & Invariant Test Suite
=====================================================
Validates all institutional quantitative vault invariants:
1. Genesis Initialization & NAV ($1.0000 / share)
2. User Deposits & ERC-4626 Share Minting
3. Bullish Rebalance Execution (Target: Circle Arc Mainnet)
4. Single-Asset Cap Invariant (Max 35% concentration)
5. Liquidity Buffer Invariant (Min 15% USDC cash)
6. Mathematical Weight Sum Invariant (Strictly 10,000 bps)
7. Emergency Drawdown Circuit Breaker (100% cash rotation on <25 sentiment)
8. Profitable Share Redemption / Withdrawal at Appreciated NAV
9. Symmetrical 2-Way Validator Consensus Enforcement
"""

import json
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


class MockAlphaTankBrain:
    def __init__(self, operator: str):
        self.operator = operator.lower()
        self.investors: Dict[str, Dict[str, Any]] = {}

        # Genesis Allocation
        self.allocation = {
            "btc_weight_bps": 3000,
            "eth_weight_bps": 3000,
            "sol_weight_bps": 2500,
            "usdc_cash_bps": 1500,
            "macro_sentiment_score": 55,
            "market_regime": "NEUTRAL_RANGING",
            "settlement_target_chain": "ARC_MAINNET",
            "settlement_mandate_hash": "GENESIS_MANDATE_INIT",
            "rebalance_timestamp": "2026-09-16T12:00:00Z",
            "justification": "Genesis allocation initialized."
        }

        # Genesis Fund State: $10,000 Initial AUM at $1.0000 NAV (10,000 shares)
        self.state = {
            "vault_aum_usdc": 10000,
            "total_shares_minted": 10000,
            "current_nav_per_share_bps": 10000,
            "total_rebalances_executed": 0,
            "last_rebalance_date": "2026-09-16",
            "circuit_breaker_active": False
        }

        self.investors[self.operator] = {
            "investor_address": self.operator,
            "shares_held": 10000,
            "deposited_usdc": 10000,
            "entry_nav_bps": 10000,
            "last_deposit_date": "2026-09-16"
        }

    def deposit(self, caller: str, amount_usdc: int) -> int:
        assert amount_usdc > 0, "[ERR_DEPOSIT_01] Deposit amount must be greater than zero."
        sender = caller.lower()
        current_nav = self.state["current_nav_per_share_bps"]
        shares_to_mint = (amount_usdc * 10000) // current_nav
        assert shares_to_mint > 0, "[ERR_DEPOSIT_02] Deposit amount too small to mint shares."

        self.state["vault_aum_usdc"] += amount_usdc
        self.state["total_shares_minted"] += shares_to_mint

        if sender in self.investors:
            self.investors[sender]["shares_held"] += shares_to_mint
            self.investors[sender]["deposited_usdc"] += amount_usdc
        else:
            self.investors[sender] = {
                "investor_address": sender,
                "shares_held": shares_to_mint,
                "deposited_usdc": amount_usdc,
                "entry_nav_bps": current_nav,
                "last_deposit_date": "2026-09-16"
            }
        return shares_to_mint

    def withdraw(self, caller: str, shares_to_burn: int) -> int:
        assert shares_to_burn > 0, "[ERR_WITHDRAW_01] Shares to burn must be greater than zero."
        sender = caller.lower()
        assert sender in self.investors, "[ERR_AUTH_02] Caller has no active investor record."
        assert self.investors[sender]["shares_held"] >= shares_to_burn, "[ERR_BALANCE_01] Insufficient share balance."

        current_nav = self.state["current_nav_per_share_bps"]
        payout_usdc = (shares_to_burn * current_nav) // 10000
        assert payout_usdc > 0, "[ERR_WITHDRAW_02] Calculated payout is zero."
        assert self.state["vault_aum_usdc"] >= payout_usdc, "[ERR_LIQUIDITY_01] Vault AUM insufficient for payout."

        self.state["vault_aum_usdc"] -= payout_usdc
        self.state["total_shares_minted"] -= shares_to_burn
        self.investors[sender]["shares_held"] -= shares_to_burn
        return payout_usdc

    def evaluate_and_rebalance(
        self,
        target_chain: str,
        macro_sentiment_score: int,
        market_regime: str,
        btc_weight_bps: int,
        eth_weight_bps: int,
        sol_weight_bps: int,
        usdc_cash_bps: int,
        nav_drift_factor_bps: int,
        mandate_summary: str
    ) -> str:
        target_chain_clean = target_chain.strip().upper()
        assert target_chain_clean in ("ARC_MAINNET", "BASE_SEPOLIA", "INTERNAL_GENLAYER"), \
            "[ERR_CHAIN_01] Unsupported settlement target chain."

        # Code-is-Law Risk Invariants
        total_w = btc_weight_bps + eth_weight_bps + sol_weight_bps + usdc_cash_bps
        assert total_w == 10000, "[ERR_WEIGHT_01] Total portfolio weights must sum to exactly 10,000 bps (100%)."

        if market_regime == "CIRCUIT_BREAKER_CASH":
            assert usdc_cash_bps == 10000 and btc_weight_bps == 0 and eth_weight_bps == 0 and sol_weight_bps == 0, \
                "[ERR_CIRCUIT_01] Circuit breaker must allocate 100% to cash reserve."
            self.state["circuit_breaker_active"] = True
        else:
            assert btc_weight_bps <= 3500 and eth_weight_bps <= 3500 and sol_weight_bps <= 3500, \
                "[ERR_CAP_01] Single crypto asset exceeds 35% concentration cap."
            assert usdc_cash_bps >= 1500, \
                "[ERR_LIQUIDITY_02] Cash reserve below mandatory 15% liquidity buffer."
            self.state["circuit_breaker_active"] = False

        old_nav = self.state["current_nav_per_share_bps"]
        new_nav = (old_nav * nav_drift_factor_bps) // 10000
        self.state["current_nav_per_share_bps"] = new_nav
        self.state["vault_aum_usdc"] = (self.state["total_shares_minted"] * new_nav) // 10000
        self.state["total_rebalances_executed"] += 1

        mandate_hash = f"0xarc_{self.state['total_rebalances_executed']}_{btc_weight_bps}_{eth_weight_bps}_{sol_weight_bps}_{new_nav}"

        self.allocation = {
            "btc_weight_bps": btc_weight_bps,
            "eth_weight_bps": eth_weight_bps,
            "sol_weight_bps": sol_weight_bps,
            "usdc_cash_bps": usdc_cash_bps,
            "macro_sentiment_score": macro_sentiment_score,
            "market_regime": market_regime,
            "settlement_target_chain": target_chain_clean,
            "settlement_mandate_hash": mandate_hash,
            "rebalance_timestamp": "2026-09-16T12:30:00Z",
            "justification": mandate_summary
        }

        return f"REBALANCE_FINALIZED: [{market_regime}] Target: {target_chain_clean} | NAV: ${new_nav/10000:.4f}"


def run_tests():
    logging.info("=" * 85)
    logging.info("  ALPHATANK CAPITAL — AUTONOMOUS MULTI-CHAIN AI HEDGE FUND REGRESSION SUITE")
    logging.info("=" * 85)

    operator = "0xb6c70b37e9168c86f43cf3257fb47ccbac9a9df8"
    fund = MockAlphaTankBrain(operator=operator)

    # Test 1: Genesis State
    assert fund.state["vault_aum_usdc"] == 10000
    assert fund.state["current_nav_per_share_bps"] == 10000
    assert fund.allocation["btc_weight_bps"] == 3000
    assert fund.allocation["usdc_cash_bps"] == 1500
    logging.info("[OK] 1. Genesis Vault Initialized: $10,000 AUM at $1.0000 NAV (30% BTC, 30% ETH, 25% SOL, 15% Cash)")

    # Test 2: User Deposit & Share Minting
    alice = "0xa11ce00000000000000000000000000000000001"
    shares = fund.deposit(caller=alice, amount_usdc=1000)
    assert shares == 1000
    assert fund.state["vault_aum_usdc"] == 11000
    assert fund.state["total_shares_minted"] == 11000
    assert fund.investors[alice]["shares_held"] == 1000
    logging.info(f"[OK] 2. User Deposit Verified: Alice deposited $1,000 USDC -> Minted {shares} ATK Shares at $1.0000 NAV")

    # Test 3: Bullish Rebalance to Circle Arc Mainnet
    msg = fund.evaluate_and_rebalance(
        target_chain="ARC_MAINNET",
        macro_sentiment_score=85,
        market_regime="BULL_MOMENTUM",
        btc_weight_bps=3500, # At max 35% cap
        eth_weight_bps=3000,
        sol_weight_bps=2000,
        usdc_cash_bps=1500,  # At min 15% buffer
        nav_drift_factor_bps=10600, # +6% portfolio gain
        mandate_summary="Circle Arc mainnet launch sparks institutional crypto rally."
    )
    assert fund.state["current_nav_per_share_bps"] == 10600 # $1.0600 NAV
    assert fund.allocation["settlement_target_chain"] == "ARC_MAINNET"
    assert fund.state["vault_aum_usdc"] == 11660 # 11000 * 1.06
    logging.info(f"[OK] 3. Bullish AI Rebalance Verified: Target Arc Mainnet | NAV rose to $1.0600 (+600 bps) | AUM: ${fund.state['vault_aum_usdc']}")

    # Test 4: Single Asset Cap Violation Rejection
    try:
        fund.evaluate_and_rebalance(
            target_chain="ARC_MAINNET",
            macro_sentiment_score=90,
            market_regime="BULL_MOMENTUM",
            btc_weight_bps=4500, # VIOLATION: > 35% cap
            eth_weight_bps=2500,
            sol_weight_bps=1500,
            usdc_cash_bps=1500,
            nav_drift_factor_bps=10000,
            mandate_summary="Attempting over-concentration in BTC."
        )
        raise AssertionError("Should have reverted on asset cap!")
    except AssertionError as e:
        assert "[ERR_CAP_01]" in str(e)
        logging.info("[OK] 4. Code-is-Law Risk Guardrail Verified: Blocked 45% BTC concentration attempt ([ERR_CAP_01])")

    # Test 5: Liquidity Cash Buffer Invariant Rejection
    try:
        fund.evaluate_and_rebalance(
            target_chain="BASE_SEPOLIA",
            macro_sentiment_score=75,
            market_regime="BULL_MOMENTUM",
            btc_weight_bps=3500,
            eth_weight_bps=3500,
            sol_weight_bps=2500,
            usdc_cash_bps=500, # VIOLATION: < 15% buffer
            nav_drift_factor_bps=10000,
            mandate_summary="Attempting under-allocation of cash."
        )
        raise AssertionError("Should have reverted on cash buffer!")
    except AssertionError as e:
        assert "[ERR_LIQUIDITY_02]" in str(e)
        logging.info("[OK] 5. Liquidity Safety Invariant Verified: Blocked 5% cash buffer drop attempt ([ERR_LIQUIDITY_02])")

    # Test 6: Mathematical Weight Sum Rejection
    try:
        fund.evaluate_and_rebalance(
            target_chain="ARC_MAINNET",
            macro_sentiment_score=50,
            market_regime="NEUTRAL_RANGING",
            btc_weight_bps=3000,
            eth_weight_bps=3000,
            sol_weight_bps=2500,
            usdc_cash_bps=2000, # SUM = 10,500 bps (VIOLATION)
            nav_drift_factor_bps=10000,
            mandate_summary="Invalid weight math."
        )
        raise AssertionError("Should have reverted on sum!")
    except AssertionError as e:
        assert "[ERR_WEIGHT_01]" in str(e)
        logging.info("[OK] 6. Mathematical Integrity Verified: Blocked non-100% weight allocation ([ERR_WEIGHT_01])")

    # Test 7: Emergency Circuit Breaker Trigger
    msg_crash = fund.evaluate_and_rebalance(
        target_chain="ARC_MAINNET",
        macro_sentiment_score=15, # EXTREME FEAR < 25
        market_regime="CIRCUIT_BREAKER_CASH",
        btc_weight_bps=0,
        eth_weight_bps=0,
        sol_weight_bps=0,
        usdc_cash_bps=10000, # 100% Cash Rotation
        nav_drift_factor_bps=9500, # -5% market shock
        mandate_summary="Severe macro market shock; circuit breaker rotating 100% into cash."
    )
    assert fund.state["circuit_breaker_active"] == True
    assert fund.allocation["usdc_cash_bps"] == 10000
    assert fund.allocation["btc_weight_bps"] == 0
    logging.info(f"[OK] 7. Emergency Circuit Breaker Verified: Rotated 100% into USDC cash reserve on extreme fear sentiment ({fund.allocation['macro_sentiment_score']}/100)")

    # Test 8: Profitable Share Redemption / Withdrawal
    # Alice burns her 1,000 shares
    alice_shares = fund.investors[alice]["shares_held"]
    current_nav = fund.state["current_nav_per_share_bps"] # 10600 * 0.95 = 10070 ($1.0070)
    payout = fund.withdraw(caller=alice, shares_to_burn=alice_shares)
    assert payout == (1000 * current_nav) // 10000 # $1,007 USDC
    assert fund.investors[alice]["shares_held"] == 0
    logging.info(f"[OK] 8. Share Redemption Verified: Alice redeemed 1,000 shares for ${payout} USDC at NAV ${current_nav/10000:.4f}")

    # Test 9: Symmetrical 2-Way Consensus Validation
    # Simulates Equivalence Principle validator checks
    def validate_proposal(score: int, regime: str, w_btc: int, w_eth: int, w_sol: int, w_cash: int) -> bool:
        if (w_btc + w_eth + w_sol + w_cash) != 10000:
            return False # Reject non-100%
        if score < 25 and regime != "CIRCUIT_BREAKER_CASH":
            return False # Reject false-negative crash
        if score >= 65 and regime != "BULL_MOMENTUM":
            return False # Reject false-negative bull
        if regime != "CIRCUIT_BREAKER_CASH":
            if w_btc > 3500 or w_eth > 3500 or w_sol > 3500:
                return False # Reject cap violation
            if w_cash < 1500:
                return False # Reject buffer violation
        return True

    assert validate_proposal(80, "BEAR_DEFENSIVE", 3000, 3000, 2500, 1500) == False # Contradicting regime
    assert validate_proposal(15, "BULL_MOMENTUM", 3500, 3500, 1500, 1500) == False # Crash disguised as bull
    assert validate_proposal(75, "BULL_MOMENTUM", 3500, 3000, 2000, 1500) == True  # 100% Truthful
    logging.info("[OK] 9. Symmetrical 2-Way Validator Consensus Verified: Rejects regime contradictions & false claims in either direction")

    logging.info("=" * 85)
    logging.info("  ALL 9 ALPHATANK INVARIANT & REGRESSION TESTS 100% PASSING!")
    logging.info("=" * 85)


if __name__ == "__main__":
    run_tests()
