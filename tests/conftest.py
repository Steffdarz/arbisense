"""
Shared pytest fixtures for ArbiSense tests.

All fixtures use static data so no live network calls are made.
"""
import pytest


# ── DeFiLlama fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def defillama_bullish():
    """Arbitrum chain TVL rising strongly — bullish signal."""
    return {
        "source": "defillama",
        "arbitrum_chain": {
            "tvl_usd": 2_000_000_000,
            "change_1d": 4.0,   # +4% → tvl_score ≈ 90
            "change_7d": 8.0,
        },
        "protocols": [],
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def defillama_bearish():
    """Arbitrum chain TVL falling — bearish signal."""
    return {
        "source": "defillama",
        "arbitrum_chain": {
            "tvl_usd": 1_200_000_000,
            "change_1d": -4.0,  # -4% → tvl_score ≈ 10
            "change_7d": -12.0,
        },
        "protocols": [],
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.fixture
def defillama_neutral():
    """Flat TVL — neutral signal."""
    return {
        "source": "defillama",
        "arbitrum_chain": {
            "tvl_usd": 1_700_000_000,
            "change_1d": 0.0,
            "change_7d": 1.0,
        },
        "protocols": [],
        "fetched_at": "2026-01-01T00:00:00+00:00",
    }


# ── Uniswap fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def uniswap_active():
    """High volume/TVL ratio (25%) — active market."""
    return {
        "source": "uniswap",
        "total_tvl_usd": 200_000_000,
        "total_volume_usd": 50_000_000,   # ratio = 0.25 → uni_score = 50
        "top_pools": [],
    }


@pytest.fixture
def uniswap_inactive():
    """Very low volume — dormant market."""
    return {
        "source": "uniswap",
        "total_tvl_usd": 200_000_000,
        "total_volume_usd": 100_000,      # ratio ≈ 0 → uni_score ≈ 0
        "top_pools": [],
    }


@pytest.fixture
def uniswap_empty():
    """No Uniswap data available."""
    return {"source": "uniswap", "error": "timeout"}


# ── Aave fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def aave_healthy():
    """Utilisation near optimal 70% — healthy lending market."""
    return {
        "source": "aave",
        "reserve_count": 3,
        "reserves": [
            {"symbol": "USDC", "utilization_rate": 0.68, "tvl_usd": 100_000_000},
            {"symbol": "WETH", "utilization_rate": 0.72, "tvl_usd": 80_000_000},
            {"symbol": "WBTC", "utilization_rate": 0.70, "tvl_usd": 60_000_000},
        ],
    }


@pytest.fixture
def aave_over_utilised():
    """Very high utilisation — liquidity risk signal."""
    return {
        "source": "aave",
        "reserve_count": 2,
        "reserves": [
            {"symbol": "USDC", "utilization_rate": 0.98, "tvl_usd": 50_000_000},
            {"symbol": "USDT", "utilization_rate": 0.95, "tvl_usd": 40_000_000},
        ],
    }


@pytest.fixture
def aave_no_utilisation():
    """Reserves present but no utilisation data."""
    return {
        "source": "aave",
        "reserve_count": 2,
        "reserves": [
            {"symbol": "WBTC", "utilization_rate": None, "tvl_usd": 90_000_000},
        ],
    }


@pytest.fixture
def aave_empty():
    """No Aave data at all."""
    return {"source": "aave", "error": "fetch failed"}


# ── GMX fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def gmx_active():
    """GMX with meaningful volume relative to TVL."""
    return {
        "source": "gmx",
        "daily_volume_usd": 10_000_000,
        "tvl_arbitrum_usd": 200_000_000,
        "tvl_change_1d_pct": 2.0,         # mild positive momentum
        "vol_tvl_ratio": 0.05,
        "activity_score": 60,
    }


@pytest.fixture
def gmx_bearish():
    """GMX with falling TVL and minimal volume."""
    return {
        "source": "gmx",
        "daily_volume_usd": 5_000,
        "tvl_arbitrum_usd": 200_000_000,
        "tvl_change_1d_pct": -7.5,
        "vol_tvl_ratio": 0.000025,
        "activity_score": 0,
    }


@pytest.fixture
def gmx_empty():
    """No GMX data."""
    return {}


# ── DeFiLlama raw protocol response (for GmxCollector unit tests) ─────────────

@pytest.fixture
def raw_protocol_response():
    """Minimal DeFiLlama /protocol/gmx JSON with historical series."""
    return {
        "currentChainTvls": {"Arbitrum": 207_553_355, "Avalanche": 13_386_154},
        "currentTvl": 220_939_509,
        "change_7d": -2.1,
        "chainTvls": {
            "Arbitrum": {
                "tvl": [
                    {"date": 1746576000, "totalLiquidityUSD": 224_500_000},
                    {"date": 1746662400, "totalLiquidityUSD": 207_553_355},
                ]
            }
        },
    }
