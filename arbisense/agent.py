"""
agent.py — Main autonomous agent loop for ArbiSense.

Each cycle:
  1. Collect data from DeFiLlama, Uniswap v3, Aave v3
  2. Analyse the data → sentiment score + summary
  3. Submit the report on-chain to SentinelRegistry.sol
  4. Sleep until the next cycle
"""

import json
import os
import time
import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .collectors import DefiLlamaCollector, UniswapCollector, AaveCollector
from .analyzer import MarketAnalyzer
from .onchain import OnChainClient

# Load .env relative to this file
_ENV = Path(__file__).parent / ".env"
load_dotenv(_ENV, override=False)
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("arbisense.agent")

DEFAULT_INTERVAL = int(os.environ.get("AGENT_INTERVAL_SEC", "3600"))  # 1 hour


class ArbiSenseAgent:
    """Autonomous DeFi intelligence agent for Arbitrum."""

    def __init__(self, interval_sec: int = DEFAULT_INTERVAL, dry_run: bool = False):
        self.interval = interval_sec
        self.dry_run = dry_run

        self.defillama = DefiLlamaCollector()
        self.uniswap = UniswapCollector()
        self.aave = AaveCollector()
        self.analyzer = MarketAnalyzer()

        if not dry_run:
            self.onchain = OnChainClient()
        else:
            self.onchain = None
            log.info("Dry-run mode: no on-chain transactions will be sent")

    # ── Public API ────────────────────────────────────────────────────────────

    def run_once(self) -> dict:
        """Execute one full agent cycle."""
        log.info("=== ArbiSense cycle started ===")

        # Step 1: Collect
        log.info("Collecting DeFiLlama data …")
        defi_data = self._safe_collect(self.defillama.collect, "defillama")

        log.info("Collecting Uniswap v3 data …")
        uni_data = self._safe_collect(self.uniswap.collect, "uniswap")

        log.info("Collecting Aave v3 data …")
        aave_data = self._safe_collect(self.aave.collect, "aave")

        # Step 2: Analyse
        log.info("Running market analysis …")
        result = self.analyzer.analyze(defi_data, uni_data, aave_data)
        log.info(
            "Score: %d/100 (%s) | %s",
            result["score"],
            self.analyzer._label(result["score"]),
            result["summary"][:80],
        )

        # Step 3: Submit on-chain
        if not self.dry_run and self.onchain:
            log.info("Submitting report on-chain …")
            tx = self.onchain.submit_report(
                data_hash=result["hash"],
                summary=result["summary"],
                sentiment_score=result["score"],
                protocol=result["protocol"],
            )
            result["transaction"] = tx
            log.info("On-chain tx: %s", tx.get("explorer", tx.get("tx_hash")))
        else:
            result["transaction"] = None

        log.info("=== Cycle complete ===")
        return result

    def run_loop(self) -> None:
        """Run the agent in a continuous loop."""
        log.info(
            "ArbiSense agent starting (interval=%ds, dry_run=%s)",
            self.interval,
            self.dry_run,
        )
        while True:
            try:
                result = self.run_once()
                self._save_report(result)
            except KeyboardInterrupt:
                log.info("Agent stopped by user.")
                break
            except Exception as exc:
                log.error("Cycle failed: %s", exc, exc_info=True)

            log.info("Sleeping %d seconds …", self.interval)
            time.sleep(self.interval)

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_collect(fn, source: str) -> dict:
        try:
            return fn()
        except Exception as exc:
            log.warning("Collector %s failed: %s", source, exc)
            return {"source": source, "error": str(exc)}

    @staticmethod
    def _save_report(result: dict) -> None:
        """Write report JSON to ./reports/ directory."""
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = reports_dir / f"report_{ts}.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        log.info("Report saved to %s", path)
