# ArbiSense — Autonomous AI DeFi Intelligence Agent

> **Arbitrum Open House London: Online Buildathon** — Best Agentic Project track

ArbiSense is a fully autonomous AI agent that monitors Arbitrum DeFi protocols, generates market intelligence reports, and permanently records each report on-chain via a deployed Solidity smart contract — without human intervention.

---

## How It Works

```
┌───────────────────────────────────────────────────────────────┐
│                      AGENT LOOP (hourly)                       │
│                                                                │
│  1. COLLECT               2. ANALYSE           3. RECORD       │
│  ┌────────────────┐       ┌──────────┐         ┌──────────┐   │
│  │ DeFiLlama TVL  │──────▶│ 4-signal │────────▶│Sentinel  │   │
│  │ Uniswap v3 DEX │       │ Heuristic│         │Registry  │   │
│  │ Aave v3 Lending│       │ Engine   │         │(Arbitrum)│   │
│  │ GMX v2 Perps   │       │score 0-100         └──────────┘   │
│  └────────────────┘       └──────────┘                        │
│                                                                │
│  Live chain TVL      Sentiment score      On-chain tx hash    │
│  DEX/perps volumes   280-char summary     Immutable record    │
│  Lending rates       SHA-256 data hash    Arbitrum Sepolia    │
└───────────────────────────────────────────────────────────────┘
```

Every hour the agent:
1. **Collects** live data from DeFiLlama, Uniswap v3, Aave v3, and GMX v2 on Arbitrum
2. **Analyses** four market signals into a composite 0–100 sentiment score
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

## Sentiment Score Model (v1.1)

Four independent signals are each normalised to [0, 100] and weighted:

| Component | Weight | Signal | Source |
|-----------|--------|--------|--------|
| Arbitrum chain TVL 24h change | 30% | Positive = ecosystem growth | DeFiLlama chains |
| Uniswap v3 volume/TVL ratio | 25% | Higher = more active spot trading | DeFiLlama DEX |
| Aave v3 avg utilisation (opt. 70%) | 25% | Too low = idle; too high = risk | DeFiLlama yields |
| **GMX v2** TVL momentum + vol/TVL | **20%** | Perpetuals activity on Arbitrum | DeFiLlama DEX + protocol |

GMX v2 is an Arbitrum-native perpetuals DEX and official buildathon sponsor. Its inclusion makes the score sensitive to leveraged-trading sentiment — a key signal that spot-only models miss.

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
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI (pytest + ruff, py3.11+3.12)
├── contracts/
│   └── SentinelRegistry.sol     # Core Solidity contract (Solidity 0.8.20)
├── scripts/
│   └── deploy.js                # Hardhat deploy script
├── arbisense/
│   ├── collectors/
│   │   ├── base.py              # Shared session factory (urllib3 retry + User-Agent)
│   │   ├── defi_llama.py        # DeFiLlama chain + protocol TVL
│   │   ├── uniswap.py           # Uniswap v3 TVL + volume + top pools
│   │   ├── aave.py              # Aave v3 TVL + yields
│   │   └── gmx.py               # GMX v2 AMM volume + TVL momentum
│   ├── analyzer.py              # 4-component sentiment scoring engine (v1.1)
│   ├── onchain.py               # SentinelRegistry client (web3.py)
│   ├── agent.py                 # Main agent loop
│   └── cli.py                   # CLI interface
├── tests/
│   ├── conftest.py              # Shared fixtures (no live HTTP)
│   ├── test_base.py             # 11 tests for session factory / retry config
│   ├── test_analyzer.py         # 22 tests for scoring logic
│   ├── test_gmx_collector.py    # 14 tests for GMX collector
│   └── test_uniswap_collector.py# 13 tests for Uniswap top_pools + collect()
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

## Testing

```bash
pip install pytest
python3 -m pytest tests/ -v
```

60 tests, 0 live HTTP calls — all network I/O is mocked via `unittest.mock`.

---

## Built With

- **Arbitrum Sepolia** — EVM-compatible L2 for contract deployment
- **Solidity 0.8.20 / Hardhat** — smart contract compilation and deployment
- **Python 3.11 / web3.py** — agent runtime
- **DeFiLlama API** — real-time TVL, volume, and yield data (no API key required)
- **GMX v2** — Arbitrum-native perpetuals DEX data (official buildathon sponsor)
- **urllib3 Retry** — automatic exponential-backoff retry on all collectors (3× max, covers 429/5xx + read timeouts)
- **GitHub Actions** — CI on Python 3.11 + 3.12

---

*Submitted to the Arbitrum Open House London: Online Buildathon — Best Agentic Project track.*
