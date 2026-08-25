import io
import re
import zipfile
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

ATTACHMENT_EXTENSIONS = (".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".zip")


@dataclass
class Link:
    url: str
    text: str
    is_attachment: bool = False
    attachment_name: str = ""


@dataclass
class ParsedPage:
    title: str = ""
    text: str = ""
    links: list[Link] = field(default_factory=list)


def normalize_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\xa0", " ").splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def is_attachment_url(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return any(path.endswith(ext) for ext in ATTACHMENT_EXTENSIONS)


def attachment_filename(url: str) -> str:
    path = urlsplit(url).path
    name = path.rsplit("/", 1)[-1]
    return name or "attachment"


def parse_html(content: bytes, base_url: str) -> ParsedPage:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    h1 = soup.find(["h1", "h2"])
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(" ", strip=True)

    container = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile("content|article|main|detail", re.I))
    if container is None:
        container = soup.body or soup

    text = normalize_text(container.get_text("\n"))

    links: list[Link] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("javascript:", "mailto:", "#", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        link_text = a.get_text(" ", strip=True)
        is_att = is_attachment_url(absolute)
        links.append(
            Link(
                url=absolute,
                text=link_text,
                is_attachment=is_att,
                attachment_name=attachment_filename(absolute) if is_att else "",
            )
        )
    return ParsedPage(title=title, text=text, links=links)


def extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue
        return normalize_text("\n".join(pages))
    except Exception as exc:
        return f"[PDF 文本提取失败: {type(exc).__name__}: {exc}]"


def extract_docx_text(content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            xml_bytes = zf.read("word/document.xml")
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_bytes)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for para in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [node.text or "" for node in para.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
            line = "".join(texts).strip()
            if line:
                paragraphs.append(line)
        return normalize_text("\n".join(paragraphs))
    except Exception as exc:
        return f"[DOCX 文本提取失败: {type(exc).__name__}: {exc}]"


def extract_plain_text(content: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return normalize_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return ""


def extract_attachment_text(url: str, content_type: str, content: bytes) -> str:
    path = urlsplit(url).path.lower()
    if path.endswith(".pdf") or "pdf" in content_type:
        return extract_pdf_text(content)
    if path.endswith(".docx") or "word" in content_type:
        return extract_docx_text(content)
    if path.endswith((".txt", ".doc", ".xls", ".xlsx", ".zip")):
        if path.endswith(".txt"):
            return extract_plain_text(content)
        return f"[二进制附件 {path.rsplit('.', 1)[-1].upper()}，已留存原始快照并比对哈希]"
    return ""


def guess_extension(url: str, content_type: str) -> str:
    path = urlsplit(url).path
    if "." in path.rsplit("/", 1)[-1]:
        return "." + path.rsplit(".", 1)[-1].lower()[:8]
    mapping = {
        "text/html": ".html",
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    return mapping.get(content_type, ".bin")
