"""robots.txt handling honoring the standard exclusion rules."""
from __future__ import annotations

import urllib.robotparser
from urllib.parse import urlparse

import httpx

from app.core.config import settings

# small in-process cache: host -> RobotFileParser
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _robots_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def _load_robots(url: str) -> urllib.robotparser.RobotFileParser:
    parsed = urlparse(url)
    host = parsed.netloc
    if host in _robots_cache:
        return _robots_cache[host]

    rp = urllib.robotparser.RobotFileParser()
    robots_url = _robots_url(url)
    try:
        resp = httpx.get(
            robots_url,
            timeout=settings.request_timeout,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True,
        )
        if resp.status_code == 200:
            rp.parse(resp.text.splitlines())
        else:
            # No robots.txt -> allow everything
            rp.parse([])
    except httpx.HTTPError:
        # Network error fetching robots -> be conservative but do not hard-block
        rp.parse([])

    _robots_cache[host] = rp
    return rp


def can_fetch(url: str, respect_robots: bool = True) -> bool:
    """Return True if the crawler is allowed to fetch ``url``."""
    if not respect_robots or not settings.respect_robots:
        return True
    rp = _load_robots(url)
    return rp.can_fetch(settings.user_agent, url)


def clear_cache() -> None:
    _robots_cache.clear()
