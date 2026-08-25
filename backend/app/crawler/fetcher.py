"""HTTP fetcher that enforces the source host whitelist and robots rules.

Redirects are followed manually so that every intermediate/target URL is
re-validated against the whitelist and robots.txt before it is fetched –
a redirect must never be a way to escape the allow-list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.crawler import robots

MAX_REDIRECTS = 5


class FetchError(Exception):
    pass


class RobotsBlocked(FetchError):
    pass


class HostNotAllowed(FetchError):
    pass


class TooManyRedirects(FetchError):
    pass


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: bytes
    content_type: str
    text: str
    redirect_chain: list[str] = field(default_factory=list)


def host_allowed(url: str, allowed_hosts: list[str]) -> bool:
    """Whitelist check: the URL host must be in the source's allowed hosts."""
    host = urlparse(url).netloc.lower()
    if not host:
        return False
    for allowed in allowed_hosts:
        allowed = allowed.strip().lower()
        if not allowed:
            continue
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


def parse_allowed_hosts(source_url: str, allowed_hosts_csv: str) -> list[str]:
    hosts = [h.strip() for h in (allowed_hosts_csv or "").split(",") if h.strip()]
    # always include the source's own host
    own = urlparse(source_url).netloc.lower()
    if own and own not in hosts:
        hosts.append(own)
    return hosts


def _guard(url: str, allowed_hosts: list[str], respect_robots: bool) -> None:
    """Raise if ``url`` violates the whitelist or robots rules."""
    if not host_allowed(url, allowed_hosts):
        raise HostNotAllowed(f"host not in whitelist: {url}")
    if not robots.can_fetch(url, respect_robots=respect_robots):
        raise RobotsBlocked(f"blocked by robots.txt: {url}")


def fetch(url: str, allowed_hosts: list[str], respect_robots: bool = True,
          client: httpx.Client | None = None) -> FetchResult:
    """Fetch ``url`` following redirects manually.

    Every hop (the initial URL and each redirect target) is re-checked against
    the host whitelist and robots.txt, so a 30x redirect cannot lead the crawler
    to a host outside the source's allow-list.
    """
    owns_client = client is None
    # NOTE: follow_redirects is disabled – we resolve them ourselves.
    client = client or httpx.Client(
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=False,
    )

    chain: list[str] = []
    current = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            _guard(current, allowed_hosts, respect_robots)
            chain.append(current)
            resp = client.get(current, follow_redirects=False)

            if resp.is_redirect and resp.headers.get("location"):
                target = urljoin(current, resp.headers["location"])
                # re-validate the redirect target BEFORE following it
                _guard(target, allowed_hosts, respect_robots)
                current = target
                continue

            content_type = resp.headers.get("content-type", "")
            text = ""
            if content_type.startswith("text/") or "html" in content_type or "xml" in content_type:
                text = resp.text
            return FetchResult(
                url=str(resp.url),
                status_code=resp.status_code,
                content=resp.content,
                content_type=content_type,
                text=text,
                redirect_chain=chain,
            )
        raise TooManyRedirects(f"exceeded {MAX_REDIRECTS} redirects starting at {url}")
    except httpx.HTTPError as exc:
        raise FetchError(str(exc)) from exc
    finally:
        if owns_client:
            client.close()
