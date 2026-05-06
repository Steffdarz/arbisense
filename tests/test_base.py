"""
tests/test_base.py — Tests for the shared session factory (collectors/base.py).

Verifies that:
  - make_session() returns a requests.Session
  - The User-Agent header is set to the ArbiSense value
  - The HTTPS adapter has the expected retry configuration
  - The retry policy covers 5xx status codes and read/connect failures
"""

import requests
from requests.adapters import HTTPAdapter

from arbisense.collectors.base import make_session, USER_AGENT, _RETRY_POLICY


class TestMakeSession:
    def test_returns_requests_session(self):
        session = make_session()
        assert isinstance(session, requests.Session)

    def test_user_agent_is_arbisense(self):
        session = make_session()
        assert session.headers["User-Agent"] == USER_AGENT
        assert "ArbiSense" in USER_AGENT

    def test_https_adapter_is_http_adapter(self):
        session = make_session()
        adapter = session.get_adapter("https://api.llama.fi")
        assert isinstance(adapter, HTTPAdapter)

    def test_http_adapter_is_http_adapter(self):
        session = make_session()
        adapter = session.get_adapter("http://example.com")
        assert isinstance(adapter, HTTPAdapter)

    def test_adapter_has_max_retries(self):
        session = make_session()
        adapter = session.get_adapter("https://api.llama.fi")
        assert adapter.max_retries is not None

    def test_retry_total_is_three(self):
        assert _RETRY_POLICY.total == 3

    def test_retry_covers_read_errors(self):
        assert _RETRY_POLICY.read >= 1

    def test_retry_covers_connect_errors(self):
        assert _RETRY_POLICY.connect >= 1

    def test_retry_covers_5xx_status_codes(self):
        assert 500 in _RETRY_POLICY.status_forcelist
        assert 503 in _RETRY_POLICY.status_forcelist

    def test_retry_covers_429(self):
        assert 429 in _RETRY_POLICY.status_forcelist

    def test_each_call_returns_independent_session(self):
        """make_session must not return a singleton."""
        s1 = make_session()
        s2 = make_session()
        assert s1 is not s2
