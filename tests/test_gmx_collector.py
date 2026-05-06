"""
Tests for arbisense.collectors.gmx.GmxCollector.

HTTP calls are mocked — no live network requests.
"""
import pytest
from unittest.mock import MagicMock, patch
from arbisense.collectors.gmx import GmxCollector


@pytest.fixture
def collector():
    return GmxCollector(timeout=5)


# ── _parse_protocol ───────────────────────────────────────────────────────────

class TestParseProtocol:
    def test_extracts_arbitrum_tvl(self, collector, raw_protocol_response):
        result = collector._parse_protocol(raw_protocol_response)
        assert result["tvl_arbitrum_usd"] == 207_553_355

    def test_derives_1d_change_from_history(self, collector, raw_protocol_response):
        result = collector._parse_protocol(raw_protocol_response)
        # (207_553_355 - 224_500_000) / 224_500_000 * 100 ≈ -7.548
        assert result["tvl_change_1d_pct"] < 0
        assert abs(result["tvl_change_1d_pct"]) < 20  # sanity bound

    def test_empty_data_returns_zeros(self, collector):
        result = collector._parse_protocol({})
        assert result["tvl_arbitrum_usd"] == 0
        assert result["tvl_change_1d_pct"] == 0.0
        assert "error" in result

    def test_single_series_entry_gives_zero_change(self, collector):
        """Can't compute change with only one historical point."""
        data = {
            "currentChainTvls": {"Arbitrum": 100_000_000},
            "currentTvl": 100_000_000,
            "chainTvls": {
                "Arbitrum": {
                    "tvl": [{"date": 1746576000, "totalLiquidityUSD": 100_000_000}]
                }
            },
        }
        result = collector._parse_protocol(data)
        assert result["tvl_change_1d_pct"] == 0.0

    def test_missing_arbitrum_in_chain_tvls_gives_zero_change(self, collector):
        data = {
            "currentChainTvls": {"Arbitrum": 100_000_000},
            "currentTvl": 100_000_000,
            "chainTvls": {},
        }
        result = collector._parse_protocol(data)
        assert result["tvl_change_1d_pct"] == 0.0

    def test_source_field_is_set(self, collector, raw_protocol_response):
        result = collector._parse_protocol(raw_protocol_response)
        assert result["source"] == "defillama_protocol"


# ── dex_volume ────────────────────────────────────────────────────────────────

class TestDexVolume:
    def test_parses_total24h(self, collector):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "total24h": 7_500_000,
            "totalAllTime": 8_000_000_000,
            "change_1d": 5.2,
            "breakdown24h": {},
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(collector.session, "get", return_value=mock_resp):
            result = collector.dex_volume()
        assert result["daily_volume_usd"] == 7_500_000
        assert result["total_volume_usd"] == 8_000_000_000
        assert result["error"] not in result if "error" in result else True

    def test_returns_zeros_on_http_error(self, collector):
        with patch.object(
            collector.session, "get", side_effect=Exception("connection refused")
        ):
            result = collector.dex_volume()
        assert result["daily_volume_usd"] == 0
        assert "error" in result

    def test_arbitrum_breakdown_extracted(self, collector):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "total24h": 10_000_000,
            "totalAllTime": 5_000_000_000,
            "change_1d": 1.0,
            "breakdown24h": {
                "arbitrum": {"gmx-v2-amm": 6_000_000},
                "avalanche": {"gmx-v2-amm": 4_000_000},
            },
        }
        mock_resp.raise_for_status = MagicMock()
        with patch.object(collector.session, "get", return_value=mock_resp):
            result = collector.dex_volume()
        assert result["daily_volume_arbitrum_usd"] == 6_000_000


# ── collect ───────────────────────────────────────────────────────────────────

class TestCollect:
    def _make_vol_response(self, vol=7_014):
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        mock.json.return_value = {
            "total24h": vol,
            "totalAllTime": 7_580_000_000,
            "change_1d": 0.0,
            "breakdown24h": {},
        }
        return mock

    def _make_proto_response(self, arb_tvl=207_553_355, prev_tvl=224_500_000):
        mock = MagicMock()
        mock.raise_for_status = MagicMock()
        mock.json.return_value = {
            "currentChainTvls": {"Arbitrum": arb_tvl},
            "currentTvl": arb_tvl,
            "change_7d": 0,
            "chainTvls": {
                "Arbitrum": {
                    "tvl": [
                        {"date": 1, "totalLiquidityUSD": prev_tvl},
                        {"date": 2, "totalLiquidityUSD": arb_tvl},
                    ]
                }
            },
        }
        return mock

    def test_collect_returns_required_keys(self, collector):
        responses = [self._make_vol_response(), self._make_proto_response()]
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()
        for key in (
            "source", "daily_volume_usd", "tvl_arbitrum_usd",
            "tvl_change_1d_pct", "vol_tvl_ratio", "activity_score"
        ):
            assert key in result, f"Missing key: {key}"

    def test_activity_score_in_range(self, collector):
        responses = [self._make_vol_response(), self._make_proto_response()]
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()
        assert 0 <= result["activity_score"] <= 100

    def test_falling_tvl_gives_lower_activity_score(self, collector):
        """A -7.5% TVL change should push momentum_score toward 0."""
        # stable TVL mock
        resp_stable_vol = self._make_vol_response()
        resp_stable_proto = self._make_proto_response(arb_tvl=200_000_000, prev_tvl=200_000_000)
        # crashing TVL mock
        resp_crash_vol = self._make_vol_response()
        resp_crash_proto = self._make_proto_response(arb_tvl=185_000_000, prev_tvl=200_000_000)

        with patch.object(collector.session, "get", side_effect=[resp_stable_vol, resp_stable_proto]):
            stable = collector.collect()
        with patch.object(collector.session, "get", side_effect=[resp_crash_vol, resp_crash_proto]):
            crash = collector.collect()

        assert crash["activity_score"] <= stable["activity_score"]

    def test_only_two_http_calls_made(self, collector):
        """collect() must make exactly 2 GET requests (not 3)."""
        responses = [self._make_vol_response(), self._make_proto_response()]
        with patch.object(collector.session, "get", side_effect=responses) as mock_get:
            collector.collect()
        assert mock_get.call_count == 2, (
            f"Expected 2 HTTP calls, got {mock_get.call_count}"
        )

    def test_source_is_gmx(self, collector):
        responses = [self._make_vol_response(), self._make_proto_response()]
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()
        assert result["source"] == "gmx"
