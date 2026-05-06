"""
gmx.py — GMX v2 collector for ArbiSense.

GMX v2 is the leading perpetuals DEX on Arbitrum and a hackathon sponsor.
Data is sourced from two public DeFiLlama endpoints (no API key required):
  1. /summary/dexs/gmx-v2-amm  — daily AMM trading volume
  2. /protocol/gmx              — TVL snapshot + historical series (single fetch,
                                  shared between tvl and momentum calculation)
"""

from datetime import datetime, timezone
from typing import Any

from .base import make_session

DEFILLAMA_BASE = "https://api.llama.fi"

# DeFiLlama slugs for GMX
_DEX_SLUG = "gmx-v2-amm"   # DEX volumes endpoint (AMM portion of GMX v2)
_PROTOCOL_SLUG = "gmx"      # Protocol TVL slug (covers all GMX versions)


class GmxCollector:
    """
    Collect GMX v2 trading metrics from DeFiLlama.

    Metrics produced per collect():
      - daily_volume_usd    : 24-hour AMM trading volume
      - tvl_arbitrum_usd    : current TVL locked in GMX on Arbitrum
      - tvl_change_1d_pct   : derived 1-day % TVL change (from history series)
      - vol_tvl_ratio        : daily_volume / tvl (activity indicator)
      - activity_score       : composite 0–100 score for use in MarketAnalyzer
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = make_session()

    # ── Public API ────────────────────────────────────────────────────────────

    def dex_volume(self) -> dict[str, Any]:
        """Fetch GMX v2 DEX volume from DeFiLlama."""
        try:
            resp = self.session.get(
                f"{DEFILLAMA_BASE}/summary/dexs/{_DEX_SLUG}",
                params={
                    "excludeTotalDataChart": "true",
                    "excludeTotalDataChartBreakdown": "true",
                    "dataType": "dailyVolume",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            total_24h = data.get("total24h", 0) or 0

            # Arbitrum-specific breakdown (best effort)
            breakdown = data.get("breakdown24h", {})
            arb_24h = 0
            for chain_key, chain_data in breakdown.items():
                if "arbitrum" in chain_key.lower():
                    if isinstance(chain_data, (int, float)):
                        arb_24h += chain_data
                    elif isinstance(chain_data, dict):
                        arb_24h += sum(
                            v for v in chain_data.values() if isinstance(v, (int, float))
                        )
            if arb_24h == 0:
                arb_24h = total_24h  # fallback: use total

            return {
                "source": "defillama_dex",
                "slug": _DEX_SLUG,
                "daily_volume_usd": total_24h,
                "daily_volume_arbitrum_usd": arb_24h,
                "total_volume_usd": data.get("totalAllTime", 0) or 0,
                "change_1d": data.get("change_1d", 0) or 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            return {
                "source": "defillama_dex",
                "slug": _DEX_SLUG,
                "error": str(exc),
                "daily_volume_usd": 0,
                "daily_volume_arbitrum_usd": 0,
                "total_volume_usd": 0,
                "change_1d": 0,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

    def protocol_tvl(self) -> dict[str, Any]:
        """
        Fetch GMX TVL on Arbitrum plus derived 1-day momentum.

        Makes a single call to /protocol/gmx and extracts both the current
        snapshot (currentChainTvls) and the historical series (chainTvls)
        so callers do not need a separate tvl_change() request.
        """
        raw = self._fetch_protocol()
        return self._parse_protocol(raw)

    def collect(self) -> dict[str, Any]:
        """
        Full GMX data collection — two HTTP requests total.

        1. GET /summary/dexs/gmx-v2-amm   → daily volume
        2. GET /protocol/gmx               → TVL snapshot + 1-day momentum

        Returns a flat dict with all metrics plus a composite activity_score.

        activity_score components:
          - vol_score      (50 %) : vol/TVL ratio; benchmark 0.05 → 100
          - momentum_score (50 %) : TVL change_1d; [-5%, +5%] → [0, 100]
        """
        volume = self.dex_volume()
        tvl_data = self.protocol_tvl()

        tvl_val = tvl_data.get("tvl_arbitrum_usd", 0) or 1
        vol_val = volume.get("daily_volume_usd", 0) or 0
        chg = tvl_data.get("tvl_change_1d_pct", 0) or 0

        vol_tvl_ratio = vol_val / tvl_val
        vol_score = min(100, int(vol_tvl_ratio * 2000))          # 0.05 → 100
        momentum_score = min(100, max(0, int(50 + chg * 10)))    # ±5% → [0,100]
        activity_score = int(vol_score * 0.5 + momentum_score * 0.5)

        return {
            "source": "gmx",
            "volume": volume,
            "tvl": tvl_data,
            "daily_volume_usd": vol_val,
            "tvl_arbitrum_usd": tvl_val,
            "tvl_change_1d_pct": chg,
            "vol_tvl_ratio": round(vol_tvl_ratio, 6),
            "activity_score": activity_score,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_protocol(self) -> dict[str, Any]:
        """Fetch raw /protocol/gmx JSON. Returns {} on error."""
        try:
            resp = self.session.get(
                f"{DEFILLAMA_BASE}/protocol/{_PROTOCOL_SLUG}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {}

    def _parse_protocol(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract TVL snapshot and 1-day momentum from raw protocol JSON."""
        now = datetime.now(timezone.utc).isoformat()
        if not data:
            return {
                "source": "defillama_protocol",
                "slug": _PROTOCOL_SLUG,
                "error": "fetch failed",
                "tvl_arbitrum_usd": 0,
                "tvl_total_usd": 0,
                "tvl_change_1d_pct": 0.0,
                "change_7d": 0,
                "fetched_at": now,
            }

        current_chain = data.get("currentChainTvls", {})
        arb_tvl = current_chain.get("Arbitrum", 0) or 0
        total_tvl = data.get("currentTvl", 0) or 0

        # Derive 1-day % change from the historical Arbitrum TVL series
        arb_series = data.get("chainTvls", {}).get("Arbitrum", {}).get("tvl", [])
        change_1d_pct = 0.0
        if len(arb_series) >= 2:
            prev = arb_series[-2].get("totalLiquidityUSD", 0) or 1
            curr = arb_series[-1].get("totalLiquidityUSD", 0) or 0
            change_1d_pct = round(((curr - prev) / prev) * 100, 3) if prev else 0.0

        return {
            "source": "defillama_protocol",
            "slug": _PROTOCOL_SLUG,
            "tvl_arbitrum_usd": arb_tvl,
            "tvl_total_usd": total_tvl,
            "tvl_change_1d_pct": change_1d_pct,
            "change_7d": data.get("change_7d", 0) or 0,
            "fetched_at": now,
        }
