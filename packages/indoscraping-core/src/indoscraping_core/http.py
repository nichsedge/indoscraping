from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, Optional, Sequence
from curl_cffi import requests
from fake_useragent import UserAgent

_ua = UserAgent()


def get_proxy_config(custom_proxy: Optional[str] = None) -> Optional[Dict[str, str]]:
    """Resolve proxy configuration from parameter or environment variables."""
    proxy = custom_proxy or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("ALL_PROXY")
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def fetch_stealth_json(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    proxy: Optional[str] = None,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    timeout: float = 20.0,
    impersonate: str = "chrome"
) -> Any:
    """Enterprise HTTP fetcher using curl_cffi TLS impersonation, proxies, and retry logic with jitter."""
    req_headers = headers.copy() if headers else {}
    if "User-Agent" not in req_headers and "user-agent" not in req_headers:
        req_headers["User-Agent"] = _ua.random

    proxies = get_proxy_config(proxy)

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params,
                headers=req_headers,
                proxies=proxies,
                impersonate=impersonate,
                timeout=timeout
            )
            
            # Handle Rate Limits (HTTP 429)
            if response.status_code == 429:
                delay = initial_delay * (2 ** attempt) + random.uniform(5.0, 15.0)
                time.sleep(delay)
                continue

            response.raise_for_status()
            
            text = response.text
            if text.strip().startswith("<!DOCTYPE"):
                raise ValueError("Endpoint returned HTML content instead of expected JSON payload.")

            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Enterprise HTTP fetch failed for {url} after {max_retries} attempts. Error: {e}") from e
            
            delay = min(initial_delay * (2 ** attempt), 30.0) + random.uniform(0.1, 1.0)
            time.sleep(delay)
