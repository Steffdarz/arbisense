"""
cli.py — Command-line interface for ArbiSense.

Usage:
  python -m arbisense.cli run-once         # one analysis cycle (dry-run)
  python -m arbisense.cli run-once --live  # one cycle + on-chain submit
  python -m arbisense.cli run-loop         # continuous loop (live)
  python -m arbisense.cli reports          # list stored reports
  python -m arbisense.cli onchain status   # show on-chain report count
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load envs
load_dotenv(Path(__file__).parent / ".env", override=False)
load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)


def cmd_run_once(args: argparse.Namespace) -> None:
    from .agent import ArbiSenseAgent

    agent = ArbiSenseAgent(dry_run=not args.live)
    result = agent.run_once()
    agent._save_report(result)

    print(f"\n{'='*60}")
    print(f"  Sentiment Score : {result['score']}/100")
    print(f"  Label           : {_label(result['score'])}")
    print(f"  Summary         : {result['summary']}")
    print(f"  Data Hash       : {result['hash']}")
    if result.get("transaction"):
        tx = result["transaction"]
        print(f"  Tx Hash         : {tx.get('tx_hash', '—')}")
        print(f"  Explorer        : {tx.get('explorer', '—')}")
    print(f"{'='*60}\n")


def cmd_run_loop(args: argparse.Namespace) -> None:
    from .agent import ArbiSenseAgent

    interval = int(os.environ.get("AGENT_INTERVAL_SEC", "3600"))
    agent = ArbiSenseAgent(interval_sec=interval, dry_run=False)
    agent.run_loop()


def cmd_reports(args: argparse.Namespace) -> None:
    reports_dir = Path("reports")
    if not reports_dir.exists():
        print("No reports directory found.")
        return
    files = sorted(reports_dir.glob("report_*.json"), reverse=True)
    if not files:
        print("No reports found.")
        return
    for f in files[:10]:
        try:
            data = json.loads(f.read_text())
            print(
                f"  {f.name}  score={data.get('score', '?')}/100"
                f"  hash={data.get('hash', '?')[:16]}…"
            )
        except Exception:
            print(f"  {f.name}  [unreadable]")


def cmd_onchain_status(args: argparse.Namespace) -> None:
    from .onchain import OnChainClient

    try:
        client = OnChainClient()
        count = client.report_count()
        print(f"On-chain reports: {count}")
        if count > 0:
            latest = client.latest_reports(min(5, count))
            for r in latest:
                from datetime import datetime, timezone

                ts = datetime.fromtimestamp(r["timestamp"], tz=timezone.utc)
                print(
                    f"  [{r['id']}] {ts.strftime('%Y-%m-%d %H:%M')} UTC"
                    f"  score={r['sentiment_score']}/100"
                    f"  hash={r['data_hash'][:16]}…"
                )
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="arbisense",
        description="ArbiSense — Autonomous AI DeFi Intelligence Agent",
    )
    sub = parser.add_subparsers(dest="command")

    p_once = sub.add_parser("run-once", help="Execute one analysis cycle")
    p_once.add_argument(
        "--live",
        action="store_true",
        help="Submit report on-chain (default: dry-run)",
    )

    sub.add_parser("run-loop", help="Run continuous agent loop (always live)")
    sub.add_parser("reports", help="List locally saved reports")
    sub.add_parser("onchain-status", help="Show on-chain report count")

    args = parser.parse_args()

    dispatch = {
        "run-once": cmd_run_once,
        "run-loop": cmd_run_loop,
        "reports": cmd_reports,
        "onchain-status": cmd_onchain_status,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
