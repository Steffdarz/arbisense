"""
onchain.py — Interact with SentinelRegistry.sol on Arbitrum.

Submits AI-generated market reports to the contract and reads
historical reports. Uses eth-account + direct JSON-RPC (no web3.py
dependency required beyond what is already installed).
"""

import os
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount

# Arbitrum Sepolia RPC
ARBITRUM_SEPOLIA_RPC = "https://sepolia-rollup.arbitrum.io/rpc"
ARBITRUM_CHAIN_ID = 421614

# Minimal ABI — only the functions the agent calls
REGISTRY_ABI = [
    {
        "name": "submitReport",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "dataHash", "type": "string"},
            {"name": "summary", "type": "string"},
            {"name": "sentimentScore", "type": "uint8"},
            {"name": "protocol", "type": "string"},
        ],
        "outputs": [{"name": "reportId", "type": "uint256"}],
    },
    {
        "name": "reportCount",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "latestReports",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "n", "type": "uint256"}],
        "outputs": [
            {
                "name": "",
                "type": "tuple[]",
                "components": [
                    {"name": "id", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "dataHash", "type": "string"},
                    {"name": "summary", "type": "string"},
                    {"name": "sentimentScore", "type": "uint8"},
                    {"name": "protocol", "type": "string"},
                ],
            }
        ],
    },
]


class OnChainClient:
    """Submit and query SentinelRegistry on Arbitrum Sepolia."""

    def __init__(
        self,
        private_key: str | None = None,
        contract_address: str | None = None,
        rpc_url: str = ARBITRUM_SEPOLIA_RPC,
    ):
        pk = private_key or os.environ.get("WALLET_PRIVATE_KEY", "")
        if not pk:
            raise ValueError("WALLET_PRIVATE_KEY not set")
        self.account: LocalAccount = Account.from_key(pk)
        self.rpc = rpc_url
        self.chain_id = ARBITRUM_CHAIN_ID
        self.contract_address = (
            contract_address
            or os.environ.get("SENTINEL_CONTRACT", "")
        )
        if not self.contract_address:
            raise ValueError(
                "SENTINEL_CONTRACT not set — run deploy.js first"
            )

        # Import web3 lazily (eth-account is already installed)
        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=REGISTRY_ABI,
            )
            self._use_web3 = True
        except ImportError:
            self._use_web3 = False

    # ── Write ─────────────────────────────────────────────────────────────────

    def submit_report(
        self,
        data_hash: str,
        summary: str,
        sentiment_score: int,
        protocol: str = "all",
    ) -> dict[str, Any]:
        """
        Submit a report to SentinelRegistry.

        Returns dict with tx_hash, block_number, report_id (if parseable).
        """
        if self._use_web3:
            return self._submit_web3(data_hash, summary, sentiment_score, protocol)
        raise RuntimeError("web3.py is not installed — cannot submit on-chain")

    def _submit_web3(
        self,
        data_hash: str,
        summary: str,
        sentiment_score: int,
        protocol: str,
    ) -> dict[str, Any]:
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        gas_price = self.w3.eth.gas_price

        tx = self.contract.functions.submitReport(
            data_hash, summary[:280], sentiment_score, protocol
        ).build_transaction(
            {
                "chainId": self.chain_id,
                "from": self.account.address,
                "nonce": nonce,
                "gasPrice": gas_price,
            }
        )
        # Estimate gas
        try:
            tx["gas"] = self.w3.eth.estimate_gas(tx)
        except Exception:
            tx["gas"] = 300_000  # safe fallback

        signed = self.account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"[onchain] tx sent: {tx_hash.hex()}")

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        return {
            "tx_hash": tx_hash.hex(),
            "block_number": receipt.blockNumber,
            "status": receipt.status,  # 1 = success
            "gas_used": receipt.gasUsed,
            "explorer": (
                f"https://sepolia.arbiscan.io/tx/{tx_hash.hex()}"
            ),
        }

    # ── Read ──────────────────────────────────────────────────────────────────

    def report_count(self) -> int:
        if self._use_web3:
            return self.contract.functions.reportCount().call()
        return 0

    def latest_reports(self, n: int = 5) -> list[dict[str, Any]]:
        if not self._use_web3:
            return []
        raw = self.contract.functions.latestReports(n).call()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "data_hash": r[2],
                "summary": r[3],
                "sentiment_score": r[4],
                "protocol": r[5],
            }
            for r in raw
        ]
