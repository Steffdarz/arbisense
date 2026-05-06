#!/usr/bin/env python3
"""Smoke test for the refactored GmxCollector."""
import sys
sys.path.insert(0, ".")

from arbisense.collectors.gmx import GmxCollector

c = GmxCollector()
d = c.collect()

print(f"daily_volume_usd    : {d['daily_volume_usd']:,.0f}")
print(f"tvl_arbitrum_usd    : {d['tvl_arbitrum_usd']:,.0f}")
print(f"tvl_change_1d_pct   : {d['tvl_change_1d_pct']}")
print(f"activity_score      : {d['activity_score']}")
print(f"vol_tvl_ratio       : {d['vol_tvl_ratio']}")
print(f"source              : {d['source']}")
print("OK - GmxCollector refactor smoke test passed")
