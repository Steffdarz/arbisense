"""
collectors/base.py — Shared HTTP session factory for all ArbiSense collectors.

Every collector calls `make_session()` instead of creating a bare
`requests.Session()`. The returned session has:

  - A descriptive User-Agent header
  - urllib3 automatic retry with exponential backoff on transient errors
    (connection failures, read timeouts, and 5xx / 429 status codes)
  - Increased default timeout (30 s) passed through at call-site

Retry policy (applied to GET requests only):
  total   = 3   (maximum retry attempts per request)
  connect = 2   (connect-level failures)
  read    = 2   (read-level timeouts)
  backoff_factor = 0.5  → waits 0 s, 0.5 s, 1.0 s between retries
  status_forcelist = [429, 500, 502, 503, 504]
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "ArbiSense/0.2 (+github.com/Steffdarz/arbisense)"

_RETRY_POLICY = Retry(
    total=3,
    connect=2,
    read=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    raise_on_status=False,   # we call raise_for_status() ourselves
)


def make_session() -> requests.Session:
    """Return a requests.Session pre-configured with retry and User-Agent."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    adapter = HTTPAdapter(max_retries=_RETRY_POLICY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
