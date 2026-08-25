import time
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.config import settings


@dataclass
class RobotsCacheEntry:
    parser: urllib.robotparser.RobotFileParser
    crawl_delay: float | None
    fetched_at: float


class RobotsChecker:
    def __init__(self, respect: bool = True, user_agent: str | None = None):
        self.respect = respect
        self.user_agent = user_agent or settings.user_agent
        self._cache: dict[str, RobotsCacheEntry] = {}

    @staticmethod
    def _origin(url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, "", "", ""))

    def _load(self, url: str) -> RobotsCacheEntry | None:
        origin = self._origin(url)
        if origin in self._cache:
            return self._cache[origin]
        robots_url = origin + "/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        crawl_delay: float | None = None
        try:
            resp = httpx.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=settings.crawl_timeout,
                follow_redirects=True,
            )
            if resp.status_code >= 400:
                parser.parse([])
            else:
                parser.parse(resp.text.splitlines())
            try:
                crawl_delay = parser.crawl_delay(self.user_agent)
            except Exception:
                crawl_delay = None
        except Exception:
            parser.parse([])
        entry = RobotsCacheEntry(parser=parser, crawl_delay=crawl_delay, fetched_at=time.time())
        self._cache[origin] = entry
        return entry

    def can_fetch(self, url: str) -> bool:
        if not self.respect:
            return True
        entry = self._load(url)
        if entry is None:
            return True
        try:
            return entry.parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def crawl_delay(self, url: str) -> float:
        if not self.respect:
            return settings.crawl_politeness_delay
        entry = self._load(url)
        if entry and entry.crawl_delay:
            return max(entry.crawl_delay, settings.crawl_politeness_delay)
        return settings.crawl_politeness_delay
