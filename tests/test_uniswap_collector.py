"""
tests/test_uniswap_collector.py — Tests for UniswapCollector.

All tests mock session.get — no live HTTP calls are made.
"""

from unittest.mock import MagicMock, patch

from arbisense.collectors.uniswap import UniswapCollector


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _http_error():
    import requests
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
    return resp


# ── TestTopPools ───────────────────────────────────────────────────────────────

class TestTopPools:
    """Tests for UniswapCollector.top_pools()."""

    def test_filters_to_arbitrum_only(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        symbols = [p["symbol"] for p in pools]
        # Ethereum USDC-USDT pool must not appear
        assert "USDC-USDT" not in symbols

    def test_filters_out_non_uniswap_projects(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        # Aave pool must not appear
        assert all("aave" not in p.get("symbol", "").lower() for p in pools)

    def test_filters_out_below_min_tvl(self, yields_pools_response):
        """Pool with tvlUsd=50_000 must be excluded."""
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        assert all(p.get("tvl_usd", 0) >= 100_000 for p in pools)

    def test_sorted_by_tvl_descending(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        tvls = [p["tvl_usd"] for p in pools]
        assert tvls == sorted(tvls, reverse=True)

    def test_respects_limit(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools(limit=1)

        assert len(pools) == 1

    def test_pool_has_required_keys(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        required = {"symbol", "tvl_usd", "apy", "apy_base", "volume_usd_1d",
                    "fee_tier", "pool_id"}
        for pool in pools:
            assert required.issubset(pool.keys()), f"Missing keys in {pool}"

    def test_http_error_returns_error_entry(self):
        collector = UniswapCollector()
        with patch.object(collector.session, "get", return_value=_http_error()):
            pools = collector.top_pools()

        assert len(pools) == 1
        assert "error" in pools[0]

    def test_volume_usd_is_numeric(self, yields_pools_response):
        collector = UniswapCollector()
        with patch.object(collector.session, "get",
                          return_value=_mock_response(yields_pools_response)):
            pools = collector.top_pools()

        for p in pools:
            if "error" not in p:
                assert isinstance(p["volume_usd_1d"], float)


# ── TestCollect ───────────────────────────────────────────────────────────────

class TestCollect:
    """Integration tests for UniswapCollector.collect()."""

    def _make_responses(self, yields_pools_response):
        proto_resp = _mock_response({
            "currentChainTvls": {"Arbitrum": 180_000_000, "Ethereum": 2_000_000_000},
            "currentTvl": 2_180_000_000,
            "change_1d": 1.2,
            "change_7d": 3.5,
        })
        dex_resp = _mock_response({
            "total24h": 400_000_000,
            "chainSummary": {
                "Arbitrum": {"total24h": 45_000_000},
            },
        })
        pools_resp = _mock_response(yields_pools_response)
        return [proto_resp, dex_resp, pools_resp]

    def test_collect_has_top_pools_key(self, yields_pools_response):
        collector = UniswapCollector()
        responses = self._make_responses(yields_pools_response)
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()

        assert "top_pools" in result

    def test_collect_top_pools_filtered(self, yields_pools_response):
        collector = UniswapCollector()
        responses = self._make_responses(yields_pools_response)
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()

        # Should contain only Arbitrum Uniswap v3 pools above min TVL
        pools = result["top_pools"]
        assert len(pools) >= 1
        if "error" not in pools[0]:
            assert pools[0]["tvl_usd"] >= 100_000

    def test_collect_makes_three_http_calls(self, yields_pools_response):
        collector = UniswapCollector()
        responses = self._make_responses(yields_pools_response)
        with patch.object(collector.session, "get", side_effect=responses) as mock_get:
            collector.collect()

        assert mock_get.call_count == 3

    def test_collect_tvl_from_arbitrum_chain(self, yields_pools_response):
        collector = UniswapCollector()
        responses = self._make_responses(yields_pools_response)
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()

        assert result["total_tvl_usd"] == 180_000_000

    def test_collect_volume_from_arbitrum_chain(self, yields_pools_response):
        collector = UniswapCollector()
        responses = self._make_responses(yields_pools_response)
        with patch.object(collector.session, "get", side_effect=responses):
            result = collector.collect()

        assert result["total_volume_usd"] == 45_000_000
