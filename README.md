# AlphaTank Capital 🛡️🤖
### Autonomous Multi-Chain AI Hedge Fund Vault on GenLayer

[![GenLayer Studio](https://img.shields.io/badge/GenLayer-Studio_Testnet-6C5CE7)](https://studio.genlayer.com)
[![Deployed Address](https://img.shields.io/badge/Contract-0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7-00D2D3)](https://explorer-studio.genlayer.com/address/0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7)
[![Settlement](https://img.shields.io/badge/Settlement-Circle_Arc_%7C_Coinbase_Base-0984E3)](https://arc.circle.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 Executive Summary

**AlphaTank Capital** is the first decentralized, fully autonomous AI hedge fund vault engineered for the GenLayer **Agent Tank Hackathon** (September 2026).

Traditional decentralized index funds and robo-advisors are constrained to rigid mechanical rules or centralized oracle feeds. They cannot read breaking macro headlines, parse institutional sentiment, or dynamically adapt to market regime transitions without centralized manager keys.

AlphaTank deploys an Intelligent Contract on GenLayer (`AlphaTankBrain.py`) that acts as an autonomous, decentralized **Chief Investment Officer (CIO)**. The contract synthesizes real-time market prices, asset momentum, and macro news through GenLayer's **Equivalence Principle** consensus. It computes risk-weighted portfolio allocations, updates share Net Asset Value (NAV), and dispatches cryptographically verified settlement mandates to **Circle Arc Mainnet** (USDC-native gas L1) and **Coinbase Base Sepolia**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Market_Telemetry["Live Market Feeds & Web Telemetry"]
        CG["CoinGecko Price & Momentum API\n(BTC, ETH, SOL)"]
        CP["CryptoPanic & Macro News Stream\n(Circle Arc, Fed, ETF flows)"]
    end

    subgraph GenLayer_Consensus["GenLayer Intelligent Consensus Layer"]
        V1["Validator Node 1\n(LLM Investment Committee)"]
        V2["Validator Node 2\n(LLM Investment Committee)"]
        V3["Validator Node 3\n(LLM Investment Committee)"]
        EQ["Equivalence Principle Consensus\n• Symmetrical 2-Way Validation\n• Strict Categorical Regimes\n• Exact 10,000 bps Weight Matching"]
    end

    subgraph AlphaTank_Brain["AlphaTank Intelligent Contract (0x0615...80A7)"]
        NAV["Dynamic NAV Accounting\n(ERC-4626 Share Mechanics)"]
        GUARD["Code-is-Law Guardrails\n• Max 35% Asset Concentration\n• Min 15% USDC Cash Buffer\n• Circuit Breaker (<25 Sentiment)"]
        HASH["Cryptographic Mandate Hash\n(0x...)"]
    end

    subgraph MultiChain_Settlement["Cross-Chain Execution Layer"]
        RELAY["AlphaTank Settlement Relay"]
        ARC["Circle Arc Mainnet Vault\n(Native USDC Gas L1)"]
        BASE["Coinbase Base Sepolia Vault\n(EVM L2)"]
    end

    CG --> V1 & V2 & V3
    CP --> V1 & V2 & V3
    V1 & V2 & V3 --> EQ
    EQ --> AlphaTank_Brain
    NAV --> GUARD --> HASH
    HASH --> RELAY
    RELAY --> ARC
    RELAY --> BASE
```

---

## ⚡ Core Invariants & Code-is-Law Guardrails

AlphaTank guarantees investor capital protection through immutable, on-chain safety invariants:

| Invariant | Specification | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Symmetrical 2-Way Consensus** | Categorical regime matching + exact weight matching | Rejects any validator proposal where regime contradicts sentiment in *either* direction. |
| **Asset Concentration Cap** | $\le 3,500\text{ bps}$ (35.00%) | No single crypto asset (BTC, ETH, SOL) can exceed 35% of total portfolio AUM. |
| **Liquidity Safety Buffer** | $\ge 1,500\text{ bps}$ (15.00%) | Minimum 15% permanently reserved in liquid USDC cash for instant redemptions. |
| **Emergency Circuit Breaker** | Sentiment $< 25$ / 100 | Rotates **100% into USDC cash** ($10,000\text{ bps}$) to shield vault principal during macro crashes. |
| **Sum-to-100% Integrity** | $\sum \text{Weights} = 10,000\text{ bps}$ | Enforces exact mathematical allocation balance. |
| **NAV-Derived Accounting** | $\text{Shares} = \frac{\text{Assets} \times 10,000}{\text{NAV}}$ | Share minting and burning derive strictly from real-time Net Asset Value. |

---

## 🌐 Multi-Chain Settlement Targets

1. **Circle Arc Mainnet** (Launched Sept 16, 2026):
   - First Layer-1 blockchain with native USDC for gas fees and transaction settlement.
   - Ideal for agentic autonomous finance without requiring volatile native gas tokens.
2. **Coinbase Base Sepolia / Base Mainnet**:
   - High-throughput Ethereum Layer-2 for broad retail DeFi composability and liquidity.
3. **Internal GenLayer Vault**:
   - Native synthetic vault ledger on GenLayer for zero-latency, gasless synthetic position tracking.

---

## 🚀 Live Deployment on GenLayer Studio

- **Contract Address:** [`0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7`](https://explorer-studio.genlayer.com/address/0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7)
- **Explorer URL:** [https://explorer-studio.genlayer.com/address/0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7](https://explorer-studio.genlayer.com/address/0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7)
- **Deployment Tx Hash:** `0xa6791ccf95e444360b0879142bdea790f50b2d5032e37c01446d8945b48bec4d`
- **Network:** GenLayer Studio Testnet (`https://studio.genlayer.com/api`)

### Genesis State (Inspected on Studio):
```json
{
  "aum_usdc": 10000,
  "total_shares": 10000,
  "nav_per_share_usdc": "$1.0000",
  "nav_bps": 10000,
  "active_regime": "NEUTRAL_RANGING",
  "macro_sentiment": 55,
  "allocations": {
    "BTC": "30.00%",
    "ETH": "30.00%",
    "SOL": "25.00%",
    "USDC_CASH": "15.00%"
  },
  "circuit_breaker_active": false,
  "target_settlement_chain": "ARC_MAINNET",
  "mandate_hash": "GENESIS_MANDATE_INIT"
}
```

---

## 🧪 Verification & Testing

### 1. Run Complete Invariant Regression Suite
```bash
python test/test_alphatank_brain.py
```
**Test Results (100% Passing):**
- `[OK] 1. Genesis Vault Initialized: $10,000 AUM at $1.0000 NAV`
- `[OK] 2. User Deposit Verified: Alice deposited $1,000 USDC -> Minted 1,000 ATK Shares`
- `[OK] 3. Bullish AI Rebalance Verified: Target Arc Mainnet | NAV rose to $1.0600 (+600 bps)`
- `[OK] 4. Code-is-Law Risk Guardrail Verified: Blocked 45% BTC concentration attempt ([ERR_CAP_01])`
- `[OK] 5. Liquidity Safety Invariant Verified: Blocked 5% cash buffer drop attempt ([ERR_LIQUIDITY_02])`
- `[OK] 6. Mathematical Integrity Verified: Blocked non-100% weight allocation ([ERR_WEIGHT_01])`
- `[OK] 7. Emergency Circuit Breaker Verified: Rotated 100% into USDC cash on extreme fear (15/100)`
- `[OK] 8. Share Redemption Verified: Alice redeemed 1,000 shares for $1,007 USDC at NAV $1.0070`
- `[OK] 9. Symmetrical 2-Way Validator Consensus Verified: Rejects regime contradictions in either direction`

### 2. Run Cross-Chain Settlement Relay
```bash
python relay/AlphaTankRelay.py
```
Dispatches verified cryptographic mandates to **Circle Arc Mainnet** and **Coinbase Base Sepolia**.

---

## 📂 Repository Structure

```
AlphaTank/
├── contracts/
│   ├── AlphaTankBrain.py        # GenLayer Intelligent Contract (AI Allocator & Risk Brain)
│   └── AlphaTankVault.sol       # Universal EVM Settlement Vault (ERC-4626 / ATK Shares)
├── test/
│   └── test_alphatank_brain.py  # 9-factor invariant regression test suite
├── scripts/
│   └── deploy_brain.mjs         # Deployment script using genlayer-js
├── relay/
│   └── AlphaTankRelay.py        # Cross-chain settlement relay (Arc Mainnet + Base)
├── deployment.json              # Live on-chain deployment receipt
├── SUBMISSION_NOTES.md          # Agent Tank portal submission notes (< 1,000 chars)
└── README.md                    # System architecture & documentation
```

---

## 📄 License
This project is open-source software licensed under the [MIT License](LICENSE).