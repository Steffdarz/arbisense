"""
Aave v3 collector — fetches Arbitrum market data via DeFiLlama.

Primary source: DeFiLlama protocol API (no key required).
Uses DeFiLlama's lending/borrowing data endpoint for Aave v3.
"""

import requests
from datetime import datetime, timezone
from typing import Any

DEFILLAMA_BASE = "https://api.llama.fi"


class AaveCollector:
    """Fetch Aave v3 Arbitrum market data via DeFiLlama."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "ArbiSense/0.1"

    def protocol_data(self) -> dict[str, Any]:
        """Fetch Aave v3 TVL and lending data from DeFiLlama."""
        try:
            resp = self.session.get(
                f"{DEFILLAMA_BASE}/protocol/aave-v3",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            current_chain = data.get("currentChainTvls", {})
            arbi_tvl = float(current_chain.get("Arbitrum", 0) or 0)
            total_tvl = float(data.get("currentTvl", 0) or 0)

            return {
                "tvl_arbitrum_usd": arbi_tvl,
                "tvl_total_usd": total_tvl,
                "change_1d": data.get("change_1d", 0),
                "change_7d": data.get("change_7d", 0),
                "category": data.get("category", "Lending"),
            }
        except Exception as exc:
            return {"error": str(exc), "tvl_arbitrum_usd": 0, "tvl_total_usd": 0}

    def yields(self) -> list[dict[str, Any]]:
        """
        Fetch top Aave v3 yield pools on Arbitrum from DeFiLlama yields API.
        Returns up to 10 pools sorted by TVL descending.
        """
        try:
            resp = self.session.get(
                "https://yields.llama.fi/pools",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            all_pools = resp.json().get("data", [])
            aave_arbi = [
                p for p in all_pools
                if p.get("project", "").startswith("aave-v3")
                and p.get("chain", "").lower() == "arbitrum"
            ]
            aave_arbi.sort(key=lambda p: p.get("tvlUsd", 0), reverse=True)
            return [
                {
                    "symbol": p.get("symbol", ""),
                    "tvl_usd": p.get("tvlUsd", 0),
                    "apy": p.get("apy", 0),
                    "apy_base": p.get("apyBase", 0),
                    "utilization_rate": p.get("utilization", None),
                    "pool_id": p.get("pool", ""),
                }
                for p in aave_arbi[:10]
            ]
        except Exception as exc:
            return [{"error": str(exc)}]

    def collect(self) -> dict[str, Any]:
        """Full collection run."""
        proto = self.protocol_data()
        pools = self.yields()
        valid = [p for p in pools if "error" not in p]

        # Synthesise utilization metric from pool data
        utils = [
            p["utilization_rate"]
            for p in valid
            if p.get("utilization_rate") is not None
        ]
        avg_util = sum(utils) / len(utils) if utils else None

        return {
            "source": "aave-v3",
            "tvl_arbitrum_usd": proto.get("tvl_arbitrum_usd", 0),
            "reserve_count": len(valid),
            "avg_utilization": avg_util,
            "reserves": valid,
            "protocol_detail": proto,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
