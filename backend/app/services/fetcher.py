from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class FetchResult:
    url: str
    status_code: int = 0
    content_type: str = ""
    content: bytes = b""
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and 200 <= self.status_code < 300


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": settings.user_agent, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        timeout=settings.crawl_timeout,
        follow_redirects=True,
        verify=False,
    )


def fetch(client: httpx.Client, url: str) -> FetchResult:
    try:
        resp = client.get(url)
        content_type = resp.headers.get("content-type", "").split(";")[0].strip()
        return FetchResult(
            url=str(resp.url),
            status_code=resp.status_code,
            content_type=content_type,
            content=resp.content,
            error="" if resp.status_code < 400 else f"HTTP {resp.status_code}",
        )
    except httpx.HTTPError as exc:
        return FetchResult(url=url, error=f"请求失败: {type(exc).__name__}: {exc}")
