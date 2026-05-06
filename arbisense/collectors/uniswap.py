"""
Uniswap v3 collector — fetches Arbitrum pool data via DeFiLlama.

Primary source: DeFiLlama protocol API (no key required, public endpoint).
The Graph hosted subgraphs for Uniswap v3 on Arbitrum are deprecated;
we use DeFiLlama which aggregates data from multiple on-chain sources.

Three API calls per collect():
  1. GET /protocol/uniswap-v3              — TVL snapshot
  2. GET /summary/dexs/uniswap?...         — 24h DEX volume
  3. GET https://yields.llama.fi/pools     — pool-level yield / TVL data
                                             (filtered to Uniswap v3 Arbitrum)
"""

from datetime import datetime, timezone
from typing import Any

from .base import make_session

DEFILLAMA_BASE = "https://api.llama.fi"
YIELDS_BASE = "https://yields.llama.fi"

# Only pools with at least $100k TVL are included in top_pools
_MIN_POOL_TVL = 100_000


class UniswapCollector:
    """Fetch Uniswap v3 Arbitrum data via DeFiLlama."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = make_session()

    # ── Public API ────────────────────────────────────────────────────────────

    def protocol_data(self) -> dict[str, Any]:
        """Fetch Uniswap v3 TVL from DeFiLlama protocol endpoint."""
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
                f"{DEFILLAMA_BASE}/summary/dexs/uniswap",
                params={
                    "excludeTotalDataChart": "true",
                    "excludeTotalDataChartBreakdown": "true",
                    "dataType": "dailyVolume",
                },
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

    def top_pools(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Return the top Uniswap v3 pools on Arbitrum by TVL.

        Source: DeFiLlama yields API (yields.llama.fi/pools).
        Filters: project starts with 'uniswap-v3', chain == 'Arbitrum',
                 tvlUsd >= _MIN_POOL_TVL.

        Each pool dict includes:
          symbol, tvl_usd, apy, volume_usd_1d, fee_tier, pool_id
        """
        try:
            resp = self.session.get(
                f"{YIELDS_BASE}/pools",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            all_pools = resp.json().get("data", [])

            # Filter to Uniswap v3 on Arbitrum with meaningful TVL
            arbi_pools = [
                p for p in all_pools
                if p.get("project", "").startswith("uniswap-v3")
                and p.get("chain", "").lower() == "arbitrum"
                and float(p.get("tvlUsd", 0) or 0) >= _MIN_POOL_TVL
            ]
            arbi_pools.sort(key=lambda p: float(p.get("tvlUsd", 0) or 0), reverse=True)

            return [
                {
                    "symbol": p.get("symbol", ""),
                    "tvl_usd": float(p.get("tvlUsd", 0) or 0),
                    "apy": float(p.get("apy", 0) or 0),
                    "apy_base": float(p.get("apyBase", 0) or 0),
                    "volume_usd_1d": float(p.get("volumeUsd1d", 0) or 0),
                    "fee_tier": p.get("feeTier", None),
                    "pool_id": p.get("pool", ""),
                }
                for p in arbi_pools[:limit]
            ]
        except Exception as exc:
            return [{"error": str(exc)}]

    def collect(self) -> dict[str, Any]:
        """Full collection run — TVL, 24h volume, and top 5 pools."""
        proto = self.protocol_data()
        vol = self.dex_volume()
        pools = self.top_pools()

        return {
            "source": "uniswap-v3",
            "total_tvl_usd": proto.get("tvl_arbitrum_usd", 0),
            "total_volume_usd": vol.get("volume_24h_arbitrum_usd", 0),
            "top_pools": pools,
            "protocol_detail": proto,
            "volume_detail": vol,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
