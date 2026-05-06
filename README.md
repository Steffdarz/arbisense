# ArbiSense — Autonomous AI DeFi Intelligence Agent

> **Arbitrum Open House London: Online Buildathon** — Best Agentic Project track

ArbiSense is a fully autonomous AI agent that monitors Arbitrum DeFi protocols, generates market intelligence reports, and permanently records each report on-chain via a deployed Solidity smart contract — without human intervention.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT LOOP (hourly)                    │
│                                                           │
│  1. COLLECT          2. ANALYSE          3. RECORD        │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐    │
│  │DeFiLlama │──────▶ │ Heuristic│──────▶ │Sentinel  │    │
│  │Uniswap v3│        │  Engine  │        │Registry  │    │
│  │Aave v3   │        │score 0-100│       │(Arbitrum)│    │
│  └──────────┘        └──────────┘        └──────────┘    │
│                                                           │
│   Live chain TVL    Sentiment score     On-chain tx hash  │
│   DEX volumes       280-char summary    Immutable record  │
│   Lending rates     SHA-256 hash                         │
└─────────────────────────────────────────────────────────┘
```

Every hour the agent:
1. **Collects** live data from DeFiLlama, Uniswap v3, and Aave v3 on Arbitrum
2. **Analyses** TVL momentum, DEX activity, and lending utilisation into a 0–100 sentiment score
3. **Records** the report on-chain by calling `SentinelRegistry.submitReport()` — the agent wallet signs and broadcasts the transaction autonomously

---

## Smart Contract: SentinelRegistry.sol

Deployed on **Arbitrum Sepolia** testnet.

```solidity
// Only the registered agent wallet may submit reports
function submitReport(
    string calldata dataHash,      // SHA-256 of the full JSON report
    string calldata summary,       // ≤ 280-char human-readable summary
    uint8           sentimentScore, // 0 = fear, 100 = greed
    string calldata protocol       // "all", "uniswap-v3", etc.
) external onlyAgent returns (uint256 reportId)
```

Key design choices:
- **`onlyAgent` modifier** — only the AI agent wallet can submit; decouples the deployer (owner) from the agent
- **`setAgent(address)`** — owner can rotate the agent key without redeployment
- **`latestReports(n)`** — gas-efficient reverse-iteration for querying recent history
- **`reportsByProtocol()`** — filter history by protocol for specialised dashboards
- All data is stored entirely on-chain (no IPFS dependency for the summary)

---

## Sentiment Score Model

| Component | Weight | Signal |
|-----------|--------|--------|
| Arbitrum chain TVL 24h change | 40% | Positive = ecosystem growth |
| Uniswap v3 volume/TVL ratio | 30% | Higher = more active trading |
| Aave v3 avg utilisation (target 70%) | 30% | Too low = idle capital; too high = risk |

Score interpretation:

| Range | Label |
|-------|-------|
| 80–100 | Extreme Greed |
| 60–79 | Greed |
| 45–59 | Neutral |
| 25–44 | Fear |
| 0–24 | Extreme Fear |

---

## Quick Start

### Prerequisites

- Python 3.10+, Node.js 18+
- Arbitrum Sepolia ETH (free from [faucet](https://faucet.triangleplatform.com/arbitrum/sepolia))
- Wallet private key set in `../.env` as `WALLET_PRIVATE_KEY`

### 1. Install dependencies

```bash
# Python
pip install -r requirements.txt

# Node / Hardhat
npm install
```

### 2. Deploy the contract

```bash
npx hardhat run scripts/deploy.js --network arbitrumSepolia
```

This writes `SENTINEL_CONTRACT=<address>` into `arbisense/.env` automatically.

### 3. Run the agent (dry-run — no on-chain tx)

```bash
python -m arbisense run-once
```

### 4. Run the agent (live — submits on-chain)

```bash
python -m arbisense run-once --live
```

### 5. Start continuous loop

```bash
python -m arbisense run-loop
```

### 6. Inspect on-chain reports

```bash
python -m arbisense onchain-status
```

---

## Project Structure

```
arbisense/
├── contracts/
│   └── SentinelRegistry.sol     # Core Solidity contract
├── scripts/
│   └── deploy.js                # Hardhat deploy script
├── arbisense/
│   ├── collectors/
│   │   ├── defi_llama.py        # DeFiLlama chain + protocol TVL
│   │   ├── uniswap.py           # Uniswap v3 TVL + volume
│   │   └── aave.py              # Aave v3 TVL + yields
│   ├── analyzer.py              # Sentiment scoring engine
│   ├── onchain.py               # SentinelRegistry client (web3.py)
│   ├── agent.py                 # Main agent loop
│   └── cli.py                   # CLI interface
├── hardhat.config.js
├── requirements.txt
└── README.md
```

---

## On-Chain Evidence

All agent submissions are publicly verifiable on Arbitrum Sepolia:

- **Contract**: `https://sepolia.arbiscan.io/address/<SENTINEL_CONTRACT>`
- **Transactions**: Each `submitReport()` call is a signed on-chain transaction

---

## Built With

- **Arbitrum Sepolia** — EVM-compatible L2 for contract deployment
- **Solidity 0.8.20** — smart contract
- **Hardhat** — compilation and deployment
- **Python / web3.py** — agent runtime
- **DeFiLlama API** — real-time on-chain DeFi data (no API key required)

---

*Submitted to the Arbitrum Open House London: Online Buildathon — Best Agentic Project track.*
