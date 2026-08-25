import httpx
import hashlib
import logging
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import settings

logger = logging.getLogger(__name__)


class FetchResult:
    def __init__(
        self,
        url: str,
        status_code: int,
        content: bytes,
        text: str,
        content_type: str,
        headers: dict[str, str],
        final_url: str,
    ):
        self.url = url
        self.status_code = status_code
        self.content = content
        self.text = text
        self.content_type = content_type
        self.headers = headers
        self.final_url = final_url
        self.content_hash = hashlib.sha256(content).hexdigest()


class HttpFetcher:
    def __init__(self, user_agent: Optional[str] = None, timeout: int = 30):
        self.user_agent = user_agent or settings.USER_AGENT
        self.timeout = timeout

    def _get_client(self, extra_headers: Optional[dict[str, str]] = None) -> httpx.Client:
        headers = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if extra_headers:
            headers.update(extra_headers)
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers,
            verify=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    def fetch(self, url: str, extra_headers: Optional[dict[str, str]] = None) -> Optional[FetchResult]:
        try:
            with self._get_client(extra_headers) as client:
                resp = client.get(url)
                resp.raise_for_status()
                encoding = resp.encoding or "utf-8"
                text = resp.content.decode(encoding, errors="replace")
                return FetchResult(
                    url=url,
                    status_code=resp.status_code,
                    content=resp.content,
                    text=text,
                    content_type=resp.headers.get("content-type", ""),
                    headers=dict(resp.headers),
                    final_url=str(resp.url),
                )
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise

    def fetch_attachment(self, url: str, extra_headers: Optional[dict[str, str]] = None) -> Optional[FetchResult]:
        try:
            with self._get_client(extra_headers) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    content_length = int(resp.headers.get("content-length", 0))
                    max_size = settings.MAX_ATTACHMENT_SIZE_MB * 1024 * 1024
                    if content_length > max_size:
                        logger.warning(f"Attachment too large: {url} ({content_length} bytes)")
                        return None
                    chunks = []
                    downloaded = 0
                    for chunk in resp.iter_bytes(chunk_size=8192):
                        downloaded += len(chunk)
                        if downloaded > max_size:
                            logger.warning(f"Attachment exceeded size limit during download: {url}")
                            return None
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    encoding = resp.encoding or "utf-8"
                    text = content.decode(encoding, errors="replace")
                    return FetchResult(
                        url=url,
                        status_code=resp.status_code,
                        content=content,
                        text=text,
                        content_type=resp.headers.get("content-type", ""),
                        headers=dict(resp.headers),
                        final_url=str(resp.url),
                    )
        except Exception as e:
            logger.error(f"Failed to fetch attachment {url}: {e}")
            return None
