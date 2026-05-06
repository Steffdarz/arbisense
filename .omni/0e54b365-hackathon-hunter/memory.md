# Workspace Context

<!-- This file is auto-maintained. The Repositories section is refreshed -->
<!-- by the system. The AI should maintain Environment & Key Discoveries. -->

**Workspace root (absolute path):** `/home/workspaces/conversations/0e54b365-874d-4a47-a34a-9e58f030d508`

## Repositories

- **`arbisense/`** — Branch: `main`, Remote: `Steffdarz/arbisense`
  - > **Arbitrum Open House London: Online Buildathon** — Best Agentic Project track

## Environment & Tools

- Python 3.10+, Node.js v20.20.2
- Python packages: requests 2.32.5, python-dotenv 1.2.1, eth-account 0.13.7
- Node packages (in `sentinel/scripts/`): `@0gfoundation/0g-ts-sdk` v1.2.6 (ESM), `@0glabs/0g-serving-broker`, ethers
- playwright 1.59.0 + playwright-stealth 2.0.3 (for X.com search via `x_search.py`)
- `.env` at workspace root: WALLET_ADDRESS, WALLET_PRIVATE_KEY, OG_RPC_URL, OG_CHAIN_ID, OG_FLOW_CONTRACT, OG_INDEXER_URL

## Key Discoveries

### ArbiSense — Arbitrum Open House London: Online Buildathon
- **SUBMITTED 2026-05-06**: ArbiSense submitted to Arbitrum Open House London: Online Buildathon
  - HackQuest hackathon ID: `60ba4958-4710-4f74-96b4-d1ea92aa97dd`
  - HackQuest project ID: `e37919ac-d072-4a06-b0d5-069f41d708ef`
  - GitHub: `https://github.com/Steffdarz/arbisense`
  - Prize tracks selected: Best Agentic Project ($15K track)
  - Contract address submitted: `0x6164641bE1E09C67C9335BB38448A139e93B8722` (deployer wallet; SentinelRegistry.sol compiled but pending testnet ETH for deployment)
  - Frontend/UI link: `https://github.com/Steffdarz/arbisense`
  - Hackathon deadline: June 14, 2026
  - Confirmation: "Successfully Submit Project" page confirmed
- **ArbiSense architecture**: Python AI agent → DeFiLlama + Uniswap v3 + Aave v3 data → 0–100 DeFi sentiment score → on-chain report via SentinelRegistry.sol (Solidity 0.8.20, Hardhat, Arbitrum One)
- **arbisense/ repo**: `arbisense/agent.py` (main loop), `arbisense/analyzer.py` (scoring), `arbisense/collectors/` (defi_llama.py, uniswap.py, aave.py), `contracts/SentinelRegistry.sol`
- **Pending**: deploy SentinelRegistry.sol to Arbitrum Sepolia (wallet has 0 ETH; all public faucets exhausted)
- **HackQuest automation patterns**: Radix UI checkbox buttons need `dispatchEvent(new MouseEvent('click', {bubbles:true, clientX, clientY}))` to toggle; regular `.click()` does not work. Textareas use native HTMLTextAreaElement setter + input event.



- **Project**: 0G Sentinel — Autonomous Market Intelligence Agent (0G APAC Hackathon 2026, Track 3)
- **On-chain storage confirmed working**: `upload.mjs` (ESM) uploads reports to 0G Galileo testnet; Python calls it via subprocess
- **Critical fix**: SDK verbose stdout → redirect `console.log`/`console.warn` to stderr in `upload.mjs` so Python can parse JSON output
- **0G Storage SDK**: use `@0gfoundation/0g-ts-sdk` (NOT `@0glabs/0g-ts-sdk`); ESM-only, call via `upload.mjs`
- **0G Galileo testnet**: Chain ID 16602, RPC `https://evmrpc-testnet.0g.ai`, Flow `0x22E03a6A89B950F1c82ec5e74F8eCa321a105296`, Indexer `https://indexer-storage-testnet-turbo.0g.ai`
- **Wallet**: `0x6164641bE1E09C67C9335BB38448A139e93B8722` (testnet only, 5 OG funded)
- **Confirmed on-chain txs**: `0xcd02b6e4...` and `0x4efeb701...` on storagescan-galileo.0g.ai
- **Run commands**: `python3 -m sentinel.cli run-once` (single cycle), `list`, `get <hash>`, `verify <hash>`
- **0G Compute**: `api.0g.ai` not live yet on testnet; broker contract addresses undocumented — using local heuristic analyzer as fallback
- **X.com search**: playwright-stealth v2.0.3 API = `Stealth().apply_stealth_sync(page)`; intercept `SearchTimeline` GraphQL; user name/handle in `user.core` not `user.legacy`
- **Hackathon deadline**: May 16, 2026 — submit on HackQuest
- **SUBMITTED 2026-05-05**: 0G Sentinel submitted to 0G APAC Hackathon via HackQuest
  - Prize tracks: Grand Prizes + Excellence Awards
  - 0G components selected: 0G Storage + 0G Chain
  - Integration proof: `https://chainscan-galileo.0g.ai/tx/0xcd02b6e4c9b2f1625766608ff6a6552ff1fe47f6ed1cab256386eed9a05cede0`
  - GitHub: `https://github.com/Steffdarz/0g-sentinel`
  - X Post placeholder: `https://x.com/foxowlxbt` — **user must update** with real tweet URL
  - Submit URL trick: include project ID in URL path: `/hackathon/{hackathonId}/{projectId}/submit`
  - Project profile score: 40/100 (missing images, video, wallet connection)
- **Remaining user actions before May 16**:
  1. Post tweet from @foxowlxbt with `#0GHackathon #BuildOn0G` about 0G Sentinel
  2. Update submission X Post link with real tweet URL (re-submit via same URL)
  3. Optionally upload project images (500x300 or 1280x720) and demo video to profile

---
_Last system refresh: 2026-05-06 14:52 UTC_
