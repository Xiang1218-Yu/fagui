import urllib.robotparser
from urllib.parse import urlparse, urljoin
import httpx
from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)


class RobotsChecker:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._parsers: dict[str, tuple[urllib.robotparser.RobotFileParser, float]] = {}
        self._cache_ttl = 3600

    def _get_base_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _fetch_robots(self, base_url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        robots_url = urljoin(base_url, "/robots.txt")
        rp = urllib.robotparser.RobotFileParser()
        try:
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                resp = client.get(robots_url, headers={"User-Agent": self.user_agent})
                if resp.status_code == 200:
                    rp.parse(resp.text.splitlines())
                    return rp
                elif resp.status_code == 404:
                    rp.parse([""])
                    return rp
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
            rp.parse([""])
            return rp
        return None

    def can_fetch(self, url: str) -> bool:
        base_url = self._get_base_url(url)
        now = time.time()

        if base_url in self._parsers:
            rp, cached_at = self._parsers[base_url]
            if now - cached_at < self._cache_ttl:
                return rp.can_fetch(self.user_agent, url)

        rp = self._fetch_robots(base_url)
        if rp:
            self._parsers[base_url] = (rp, now)
            return rp.can_fetch(self.user_agent, url)
        return True

    def get_crawl_delay(self, url: str) -> float:
        base_url = self._get_base_url(url)
        self.can_fetch(url)
        if base_url in self._parsers:
            rp, _ = self._parsers[base_url]
            delay = rp.crawl_delay(self.user_agent)
            return float(delay) if delay else 0.0
        return 0.0
