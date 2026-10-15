"""Shared HTTP defaults for non-browser retailer adapters."""

from __future__ import annotations

import requests


def new_http_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
        }
    )
    return session
