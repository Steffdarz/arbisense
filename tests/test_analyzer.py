"""
Tests for arbisense.analyzer.MarketAnalyzer.

All tests use static fixture data — no network calls.
"""
import pytest
from arbisense.analyzer import MarketAnalyzer


@pytest.fixture(autouse=True)
def analyzer():
    return MarketAnalyzer()


# ── _label ────────────────────────────────────────────────────────────────────

class TestLabel:
    def test_extreme_greed(self, analyzer):
        assert analyzer._label(80) == "Extreme Greed"
        assert analyzer._label(100) == "Extreme Greed"

    def test_greed(self, analyzer):
        assert analyzer._label(60) == "Greed"
        assert analyzer._label(79) == "Greed"

    def test_neutral(self, analyzer):
        assert analyzer._label(45) == "Neutral"
        assert analyzer._label(59) == "Neutral"

    def test_fear(self, analyzer):
        assert analyzer._label(25) == "Fear"
        assert analyzer._label(44) == "Fear"

    def test_extreme_fear(self, analyzer):
        assert analyzer._label(0) == "Extreme Fear"
        assert analyzer._label(24) == "Extreme Fear"


# ── _compute_score ────────────────────────────────────────────────────────────

class TestComputeScore:
    def test_score_always_in_range(
        self, analyzer, defillama_bullish, uniswap_active, aave_healthy, gmx_active
    ):
        score = analyzer._compute_score(
            defillama_bullish, uniswap_active, aave_healthy, gmx_active
        )
        assert 0 <= score <= 100

    def test_bullish_inputs_give_high_score(
        self, analyzer, defillama_bullish, uniswap_active, aave_healthy, gmx_active
    ):
        score = analyzer._compute_score(
            defillama_bullish, uniswap_active, aave_healthy, gmx_active
        )
        assert score >= 50, f"Expected bullish score >= 50, got {score}"

    def test_bearish_inputs_give_low_score(
        self, analyzer, defillama_bearish, uniswap_inactive, aave_over_utilised, gmx_bearish
    ):
        score = analyzer._compute_score(
            defillama_bearish, uniswap_inactive, aave_over_utilised, gmx_bearish
        )
        assert score < 40, f"Expected bearish score < 40, got {score}"

    def test_neutral_tvl_gives_midrange_tvl_component(self, analyzer):
        """TVL change=0 should map to tvl_score=50."""
        # Using 0% TVL change with otherwise neutral data
        defillama = {
            "arbitrum_chain": {"tvl_usd": 1_700_000_000, "change_1d": 0.0, "change_7d": 0}
        }
        uniswap = {"total_tvl_usd": 1, "total_volume_usd": 0}
        aave = {}
        gmx = {}
        score = analyzer._compute_score(defillama, uniswap, aave, gmx)
        # tvl_score=50*0.30 + uni=0*0.25 + aave=50*0.25 + gmx=50*0.20 = 15+0+12.5+10 = 37
        assert 30 <= score <= 50

    def test_missing_uniswap_data_doesnt_crash(
        self, analyzer, defillama_neutral, uniswap_empty, aave_healthy, gmx_empty
    ):
        score = analyzer._compute_score(
            defillama_neutral, uniswap_empty, aave_healthy, gmx_empty
        )
        assert 0 <= score <= 100

    def test_missing_aave_data_falls_back_to_neutral(
        self, analyzer, defillama_neutral, uniswap_inactive, aave_empty, gmx_empty
    ):
        score = analyzer._compute_score(
            defillama_neutral, uniswap_inactive, aave_empty, gmx_empty
        )
        # aave_score falls back to 50 (neutral); total should be moderate
        assert 0 <= score <= 100

    def test_aave_no_utilisation_rate_falls_back_to_neutral(
        self, analyzer, defillama_neutral, uniswap_inactive, aave_no_utilisation, gmx_empty
    ):
        score = analyzer._compute_score(
            defillama_neutral, uniswap_inactive, aave_no_utilisation, gmx_empty
        )
        assert 0 <= score <= 100

    def test_gmx_none_defaults_to_neutral(
        self, analyzer, defillama_neutral, uniswap_inactive, aave_healthy
    ):
        score_none = analyzer._compute_score(
            defillama_neutral, uniswap_inactive, aave_healthy, None
        )
        score_empty = analyzer._compute_score(
            defillama_neutral, uniswap_inactive, aave_healthy, {}
        )
        # Both should give same result (empty gmx → fallback score of 50)
        assert score_none == score_empty

    def test_tvl_change_clamped_at_bounds(self, analyzer):
        """TVL changes beyond ±5% should still clamp to [0, 100]."""
        defillama_spike = {
            "arbitrum_chain": {"tvl_usd": 2e9, "change_1d": 99.0, "change_7d": 0}
        }
        defillama_crash = {
            "arbitrum_chain": {"tvl_usd": 1e9, "change_1d": -99.0, "change_7d": 0}
        }
        uniswap = {"total_tvl_usd": 1, "total_volume_usd": 0}
        score_spike = analyzer._compute_score(defillama_spike, uniswap, {}, {})
        score_crash = analyzer._compute_score(defillama_crash, uniswap, {}, {})
        assert 0 <= score_spike <= 100
        assert 0 <= score_crash <= 100
        assert score_spike > score_crash


# ── analyze (full pipeline) ───────────────────────────────────────────────────

class TestAnalyze:
    def test_returns_required_keys(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy, gmx_active
    ):
        result = analyzer.analyze(
            defillama_neutral, uniswap_active, aave_healthy, gmx_active
        )
        for key in ("score", "summary", "protocol", "report", "hash", "report_json"):
            assert key in result, f"Missing key: {key}"

    def test_summary_within_280_chars(
        self, analyzer, defillama_bullish, uniswap_active, aave_healthy, gmx_active
    ):
        result = analyzer.analyze(
            defillama_bullish, uniswap_active, aave_healthy, gmx_active
        )
        assert len(result["summary"]) <= 280

    def test_hash_is_sha256_hex(
        self, analyzer, defillama_neutral, uniswap_inactive, aave_healthy, gmx_empty
    ):
        result = analyzer.analyze(
            defillama_neutral, uniswap_inactive, aave_healthy, gmx_empty
        )
        assert len(result["hash"]) == 64
        int(result["hash"], 16)  # raises if not valid hex

    def test_report_version_is_1_1(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy, gmx_active
    ):
        result = analyzer.analyze(
            defillama_neutral, uniswap_active, aave_healthy, gmx_active
        )
        assert result["report"]["version"] == "1.1"

    def test_report_contains_gmx_section(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy, gmx_active
    ):
        result = analyzer.analyze(
            defillama_neutral, uniswap_active, aave_healthy, gmx_active
        )
        gmx_section = result["report"]["gmx_v2"]
        assert "daily_volume_usd" in gmx_section
        assert "tvl_arbitrum_usd" in gmx_section
        assert "activity_score" in gmx_section

    def test_deterministic_hash(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy, gmx_active
    ):
        """Same inputs should produce the same hash (modulo timestamp)."""
        # The report includes generated_at timestamp, so hashes will differ per call.
        # What we can test: score is deterministic for same inputs.
        r1 = analyzer.analyze(defillama_neutral, uniswap_active, aave_healthy, gmx_active)
        r2 = analyzer.analyze(defillama_neutral, uniswap_active, aave_healthy, gmx_active)
        assert r1["score"] == r2["score"]
        assert r1["summary"][:60] == r2["summary"][:60]

    def test_gmx_defaults_to_empty_dict_when_none(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy
    ):
        """analyze() should not crash when gmx is omitted."""
        result = analyzer.analyze(defillama_neutral, uniswap_active, aave_healthy)
        assert "score" in result
        assert 0 <= result["score"] <= 100

    def test_protocol_is_all(
        self, analyzer, defillama_neutral, uniswap_active, aave_healthy, gmx_empty
    ):
        result = analyzer.analyze(
            defillama_neutral, uniswap_active, aave_healthy, gmx_empty
        )
        assert result["protocol"] == "all"
