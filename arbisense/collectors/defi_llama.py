"""
DeFiLlama collector — pulls TVL and protocol data for Arbitrum.

Uses the public DeFiLlama REST API (no key required).
"""

import requests
from datetime import datetime, timezone
from typing import Any


DEFILLAMA_BASE = "https://api.llama.fi"

# Top Arbitrum protocols to track
ARBITRUM_PROTOCOLS = [
    "gmx",
    "uniswap-v3",
    "aave-v3",
    "camelot-dex",
    "pendle",
    "radiant-v2",
]


class DefiLlamaCollector:
    """Fetch TVL data for Arbitrum DeFi protocols via DeFiLlama."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "ArbiSense/0.1 (+github.com/arbisense)"

    # ── Public API ────────────────────────────────────────────────────────────

    def arbitrum_tvl(self) -> dict[str, Any]:
        """Return total TVL on Arbitrum chain."""
        resp = self.session.get(
            f"{DEFILLAMA_BASE}/v2/chains", timeout=self.timeout
        )
        resp.raise_for_status()
        chains = resp.json()
        for chain in chains:
            if chain.get("name", "").lower() == "arbitrum":
                return {
                    "tvl_usd": chain.get("tvl", 0),
                    "change_1d": chain.get("change_1d", 0),
                    "change_7d": chain.get("change_7d", 0),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
        return {"tvl_usd": 0, "change_1d": 0, "change_7d": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat()}

    def protocol_tvls(self) -> list[dict[str, Any]]:
        """Return TVL snapshots for the tracked Arbitrum protocols."""
        results = []
        for slug in ARBITRUM_PROTOCOLS:
            try:
                resp = self.session.get(
                    f"{DEFILLAMA_BASE}/protocol/{slug}", timeout=self.timeout
                )
                resp.raise_for_status()
                data = resp.json()

                # currentChainTvls has the current snapshot (not historical array)
                current_chain = data.get("currentChainTvls", {})
                arbi_tvl = current_chain.get("Arbitrum", 0) or 0

                # Top-level tvl field is also sometimes an array; use currentTvl
                total_tvl = data.get("currentTvl", 0) or data.get("tvl", 0)
                if isinstance(total_tvl, list):
                    # Historical array — take last entry
                    total_tvl = total_tvl[-1].get("totalLiquidityUSD", 0) if total_tvl else 0

                results.append({
                    "protocol": slug,
                    "name": data.get("name", slug),
                    "tvl_total_usd": total_tvl,
                    "tvl_arbitrum_usd": arbi_tvl,
                    "category": data.get("category", ""),
                    "change_1d": data.get("change_1d", 0),
                    "change_7d": data.get("change_7d", 0),
                })
            except Exception as exc:
                results.append({"protocol": slug, "error": str(exc)})
        return results

    def collect(self) -> dict[str, Any]:
        """Full collection run — returns structured data dict."""
        return {
            "source": "defillama",
            "arbitrum_chain": self.arbitrum_tvl(),
            "protocols": self.protocol_tvls(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
