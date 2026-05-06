"""
analyzer.py — Heuristic + rule-based market intelligence engine.

Ingests raw collector data and produces a structured Report with:
  - A composite sentiment score (0 = extreme fear, 100 = extreme greed)
  - A human-readable summary (≤ 280 chars)
  - A full JSON report body (to be hashed and stored on-chain)

No external LLM API key required — all logic is deterministic.

Scoring weights (v1.1 — 4-component model):
  Component              Weight   Signal
  ─────────────────────  ──────   ──────────────────────────────────────
  1. TVL momentum          30 %   Arbitrum chain 1-day TVL change
  2. Uniswap v3 activity   25 %   Volume / TVL ratio on Uniswap v3
  3. Aave v3 utilisation   25 %   Average reserve utilisation (opt. ~70%)
  4. GMX v2 activity       20 %   GMX daily volume / TVL ratio
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


class MarketAnalyzer:
    """Produce market intelligence from raw collected data."""

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(
        self,
        defillama: dict[str, Any],
        uniswap: dict[str, Any],
        aave: dict[str, Any],
        gmx: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run full analysis pipeline.

        Returns a dict with keys:
          - score:   int 0-100
          - summary: str (≤ 280 chars)
          - protocol: str ("all")
          - report:  dict (full analysis body)
          - hash:    str (SHA-256 of canonical JSON report)
        """
        gmx = gmx or {}
        score = self._compute_score(defillama, uniswap, aave, gmx)
        report = self._build_report(defillama, uniswap, aave, gmx, score)
        summary = self._build_summary(score, defillama, uniswap, gmx)
        report_json = json.dumps(report, sort_keys=True, separators=(",", ":"))
        data_hash = hashlib.sha256(report_json.encode()).hexdigest()

        return {
            "score": score,
            "summary": summary,
            "protocol": "all",
            "report": report,
            "hash": data_hash,
            "report_json": report_json,
        }

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _compute_score(
        self,
        defillama: dict[str, Any],
        uniswap: dict[str, Any],
        aave: dict[str, Any],
        gmx: dict[str, Any],
    ) -> int:
        """
        Composite sentiment score on a 0–100 scale.

        Each component is normalised to [0, 100] then weighted.
        """
        # 1. TVL momentum (30 pts)
        chain = defillama.get("arbitrum_chain", {})
        change_1d = chain.get("change_1d", 0) or 0
        # Map [-5%, +5%] → [0, 100]; clamp
        tvl_score = min(100, max(0, int(50 + change_1d * 10)))

        # 2. Uniswap v3 activity ratio (25 pts)
        u_tvl = uniswap.get("total_tvl_usd", 1) or 1
        u_vol = uniswap.get("total_volume_usd", 0) or 0
        uni_ratio = u_vol / u_tvl
        # Map [0, 0.5] → [0, 100]
        uni_score = min(100, int(uni_ratio * 200))

        # 3. Aave utilisation health (25 pts; optimal ~70%)
        avg_util = aave.get("avg_utilization")
        if avg_util is None:
            reserves = aave.get("reserves", [])
            valid = [r for r in reserves if "error" not in r and r.get("utilization_rate")]
            avg_util = (
                sum(float(r["utilization_rate"]) for r in valid) / len(valid)
                if valid else None
            )
        if avg_util is not None:
            aave_score = max(0, 100 - int(abs(float(avg_util) - 0.70) * 200))
        else:
            aave_score = 50  # neutral if no data

        # 4. GMX v2 activity (20 pts)
        # Use pre-computed activity_score from the collector.
        # Falls back to TVL momentum if activity_score is absent.
        gmx = gmx or {}
        gmx_score = gmx.get("activity_score")
        if gmx_score is None:
            chg = gmx.get("tvl_change_1d_pct", 0) or 0
            gmx_score = min(100, max(0, int(50 + chg * 10)))

        composite = int(
            tvl_score * 0.30
            + uni_score * 0.25
            + aave_score * 0.25
            + gmx_score * 0.20
        )
        return max(0, min(100, composite))

    # ── Report building ───────────────────────────────────────────────────────

    def _build_report(
        self,
        defillama: dict,
        uniswap: dict,
        aave: dict,
        gmx: dict,
        score: int,
    ) -> dict:
        chain = defillama.get("arbitrum_chain", {})
        return {
            "version": "1.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sentiment_score": score,
            "sentiment_label": self._label(score),
            "arbitrum_chain": {
                "tvl_usd": chain.get("tvl_usd", 0),
                "change_1d_pct": chain.get("change_1d", 0),
                "change_7d_pct": chain.get("change_7d", 0),
            },
            "uniswap_v3": {
                "total_tvl_usd": uniswap.get("total_tvl_usd", 0),
                "total_volume_usd": uniswap.get("total_volume_usd", 0),
                "top_pools": uniswap.get("top_pools", [])[:5],
            },
            "aave_v3": {
                "reserve_count": aave.get("reserve_count", 0),
                "reserves": aave.get("reserves", [])[:5],
            },
            "gmx_v2": {
                "daily_volume_usd": gmx.get("daily_volume_usd", 0),
                "tvl_arbitrum_usd": gmx.get("tvl_arbitrum_usd", 0),
                "tvl_change_1d_pct": gmx.get("tvl_change_1d_pct", 0),
                "vol_tvl_ratio": gmx.get("vol_tvl_ratio", 0),
                "activity_score": gmx.get("activity_score", 0),
            },
            "protocols_tracked": defillama.get("protocols", []),
        }

    def _build_summary(
        self, score: int, defillama: dict, uniswap: dict, gmx: dict
    ) -> str:
        label = self._label(score)
        chain = defillama.get("arbitrum_chain", {})
        tvl = chain.get("tvl_usd", 0)
        chg = chain.get("change_1d", 0) or 0
        tvl_str = f"${tvl/1e9:.2f}B" if tvl >= 1e9 else f"${tvl/1e6:.0f}M"
        direction = "▲" if chg >= 0 else "▼"
        gmx_vol = gmx.get("daily_volume_usd", 0) or 0
        gmx_vol_str = f"${gmx_vol/1e9:.1f}B" if gmx_vol >= 1e9 else f"${gmx_vol/1e6:.0f}M"
        summary = (
            f"Arbitrum DeFi: {label} (score {score}/100). "
            f"Chain TVL {tvl_str} {direction}{abs(chg):.1f}% 24h. "
            f"UniV3 ${uniswap.get('total_tvl_usd', 0)/1e6:.0f}M TVL. "
            f"GMX vol {gmx_vol_str}/day. ArbiSense autonomous report."
        )
        return summary[:280]

    @staticmethod
    def _label(score: int) -> str:
        if score >= 80:
            return "Extreme Greed"
        if score >= 60:
            return "Greed"
        if score >= 45:
            return "Neutral"
        if score >= 25:
            return "Fear"
        return "Extreme Fear"
