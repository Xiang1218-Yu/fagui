"""HTML and document (PDF/DOCX) parsing helpers."""
from __future__ import annotations

import io
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

ATTACHMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar", ".txt")


def extract_html_text(html: str) -> str:
    """Return the visible main text of an HTML page."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    # prefer an <h1>, fall back to <title>
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)
    return ""


def find_attachment_links(html: str, base_url: str) -> list[dict]:
    """Return attachment links (pdf/doc/...) discovered in the page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url, href)
        path = urlparse(abs_url).path.lower()
        if path.endswith(ATTACHMENT_EXTENSIONS) and abs_url not in seen:
            seen.add(abs_url)
            results.append({"url": abs_url, "text": a.get_text(strip=True) or path.rsplit("/", 1)[-1]})
    return results


def find_content_links(html: str, base_url: str, allowed_hosts: list[str],
                       selector: str = "", limit: int = 20) -> list[dict]:
    """Return in-whitelist article/content links found on an entry page.

    These are the links to individual regulation pages that the crawler should
    follow (as opposed to attachments). Only http(s) links whose host is inside
    ``allowed_hosts`` are returned, and only anchors carrying real link text.
    """
    from app.crawler.fetcher import host_allowed  # local import to avoid cycle

    soup = BeautifulSoup(html, "lxml")
    anchors = soup.select(selector) if selector else soup.find_all("a", href=True)

    results: list[dict] = []
    seen: set[str] = set()
    base_no_frag = base_url.split("#", 1)[0]
    for a in anchors:
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        abs_url = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        path = parsed.path.lower()
        if path.endswith(ATTACHMENT_EXTENSIONS):  # attachments handled separately
            continue
        if abs_url == base_no_frag or abs_url in seen:
            continue
        if not host_allowed(abs_url, allowed_hosts):  # stay inside the whitelist
            continue
        text = a.get_text(strip=True)
        if not text:
            continue
        seen.add(abs_url)
        results.append({"url": abs_url, "text": text})
        if len(results) >= limit:
            break
    return results


def find_revision_note(html: str) -> str:
    """Heuristically extract a revision / update record snippet from the page."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ")
    patterns = [
        r"(修订记录[:：].{0,120})",
        r"(修改说明[:：].{0,120})",
        r"(发布日期[:：]\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
        r"(更新时间[:：]\s*\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)",
    ]
    notes = []
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            notes.append(m.group(1).strip())
    return " | ".join(notes)


def extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001 - parsing is best-effort
        return f"[PDF 解析失败: {exc}]"


def extract_docx_text(data: bytes) -> str:
    try:
        import docx

        document = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()
    except Exception as exc:  # noqa: BLE001
        return f"[DOCX 解析失败: {exc}]"


def extract_attachment_text(filename: str, content_type: str, data: bytes) -> str:
    name = filename.lower()
    ctype = (content_type or "").lower()
    if name.endswith(".pdf") or "pdf" in ctype:
        return extract_pdf_text(data)
    if name.endswith(".docx") or "wordprocessingml" in ctype:
        return extract_docx_text(data)
    if name.endswith(".txt") or ctype.startswith("text/"):
        try:
            return data.decode("utf-8", errors="ignore").strip()
        except Exception:  # noqa: BLE001
            return ""
    return f"[不支持解析的附件类型: {filename}]"
