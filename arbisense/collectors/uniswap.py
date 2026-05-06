"""
Uniswap v3 collector — fetches Arbitrum pool data via DeFiLlama.

Primary source: DeFiLlama protocol API (no key required, public endpoint).
The Graph hosted subgraphs for Uniswap v3 on Arbitrum are deprecated;
we use DeFiLlama which aggregates data from multiple on-chain sources.
"""

import requests
from datetime import datetime, timezone
from typing import Any

DEFILLAMA_BASE = "https://api.llama.fi"


class UniswapCollector:
    """Fetch Uniswap v3 Arbitrum data via DeFiLlama."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "ArbiSense/0.1"

    def protocol_data(self) -> dict[str, Any]:
        """Fetch Uniswap v3 data from DeFiLlama protocol endpoint."""
        try:
            resp = self.session.get(
                f"{DEFILLAMA_BASE}/protocol/uniswap-v3",
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
            }
        except Exception as exc:
            return {"error": str(exc), "tvl_arbitrum_usd": 0, "tvl_total_usd": 0}

    def dex_volume(self) -> dict[str, Any]:
        """Fetch 24h DEX volume for Uniswap on Arbitrum via DeFiLlama DEX endpoint."""
        try:
            resp = self.session.get(
                f"{DEFILLAMA_BASE}/summary/dexs/uniswap?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            chain_data = data.get("chainSummary", {})
            arbi_vol = float(chain_data.get("Arbitrum", {}).get("total24h", 0) or 0)
            total_vol = float(data.get("total24h", 0) or 0)
            return {
                "volume_24h_arbitrum_usd": arbi_vol,
                "volume_24h_total_usd": total_vol,
            }
        except Exception as exc:
            return {"error": str(exc), "volume_24h_arbitrum_usd": 0}

    def collect(self) -> dict[str, Any]:
        """Full collection run."""
        proto = self.protocol_data()
        vol = self.dex_volume()
        return {
            "source": "uniswap-v3",
            "total_tvl_usd": proto.get("tvl_arbitrum_usd", 0),
            "total_volume_usd": vol.get("volume_24h_arbitrum_usd", 0),
            "protocol_detail": proto,
            "volume_detail": vol,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
