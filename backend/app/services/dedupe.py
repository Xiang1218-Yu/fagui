import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Regulation, Source

_REG_NUMBER_PATTERNS = [
    re.compile(r"[〔\[【（(]\s*(\d{4})\s*[〕\]】）)]\s*第?\s*(\d+)\s*号"),
    re.compile(r"第\s*(\d+)\s*号\s*[（(]?\s*(\d{4})"),
]

_TITLE_SIMILARITY_THRESHOLD = 0.88


def extract_reg_number(title: str, text: str) -> str | None:
    for source in (title or "", text or ""):
        for pattern in _REG_NUMBER_PATTERNS:
            match = pattern.search(source)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    year, num = groups
                    if len(year) == 4:
                        return f"〔{year}〕第{num}号"
                    return f"〔{groups[1]}〕第{groups[0]}号"
    return None


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, re.sub(r"\s+", "", a), re.sub(r"\s+", "", b)).ratio()


def find_or_create_regulation(
    db: Session, *, title: str, text: str, url: str, source: Source
) -> tuple[Regulation, bool]:
    reg_number = extract_reg_number(title, text)
    stmt = select(Regulation)
    candidates = list(db.scalars(stmt))

    if reg_number:
        for reg in candidates:
            if reg.reg_number and reg.reg_number == reg_number:
                return reg, False

    clean_title = title or url
    for reg in candidates:
        if reg.reg_number:
            continue
        if reg.authority and source.name and reg.authority != source.name:
            continue
        if _title_similarity(reg.title, clean_title) >= _TITLE_SIMILARITY_THRESHOLD:
            if reg_number and not reg.reg_number:
                reg.reg_number = reg_number
            return reg, False

    reg = Regulation(
        title=clean_title[:512],
        reg_number=reg_number,
        authority=source.name,
        primary_source_id=source.id,
        canonical_url=url,
        status="active",
        tags=[source.org_type],
    )
    db.add(reg)
    db.flush()
    return reg, True


def regulation_source_count(db: Session, regulation_id: int) -> int:
    return (
        db.query(Document.source_id)
        .filter(Document.regulation_id == regulation_id, Document.doc_type == "page")
        .distinct()
        .count()
    )
