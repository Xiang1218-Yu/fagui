import difflib
import re
import unicodedata
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, Regulation

# 发文字号常见模式
_REG_NO_PATTERNS = [
    r"〔\s*20\d{2}\s*〕\s*\d+\s*号",
    r"[0-9]{4}\s*年第\s*\d+\s*号",
    r"第\s*\d+\s*号",
]

# 归一化标题时需要剥离的常见后缀词（长的优先）
_SUFFIX_WORDS = ["的通知公告", "的通知", "的公告", "的通告", "通知", "公告", "通告", "公示", "意见稿"]

_SIMILARITY_THRESHOLD = 0.85


def extract_regulation_no(title: str) -> Optional[str]:
    for pattern in _REG_NO_PATTERNS:
        m = re.search(pattern, title or "")
        if m:
            return re.sub(r"\s+", "", m.group(0))
    return None


def normalize_title(title: str) -> str:
    """标题归一化：全角转半角、去空白、去标点、剥离通知/公告等后缀词。"""
    if not title:
        return ""
    chars = []
    for ch in title:
        code = ord(ch)
        if code == 0x3000:  # 全角空格
            ch = " "
        elif 0xFF01 <= code <= 0xFF5E:  # 全角可见字符转半角
            ch = chr(code - 0xFEE0)
        chars.append(ch)
    s = "".join(chars)
    s = re.sub(r"\s+", "", s)
    s = "".join(ch for ch in s if not unicodedata.category(ch).startswith("P"))
    changed = True
    while changed:
        changed = False
        for word in _SUFFIX_WORDS:
            if s.endswith(word) and len(s) > len(word):
                s = s[: -len(word)]
                changed = True
    return s


def extract_authority(text: str) -> Optional[str]:
    """从正文中提取发布/发文机关线索，提取不到返回 None。"""
    if not text:
        return None
    m = re.search(r"(发布机关|发文机关|制定机关|发布单位)\s*[:：]?\s*([^\n，。；]{2,30})", text)
    if m:
        return m.group(2).strip()
    return None


def assign_regulation(session: Session, document: Document, text: str) -> Regulation:
    """为变更归并法规：先按发文字号精确匹配，再按归一化标题相似度归并，否则新建。"""
    title = (document.title or "").strip()
    reg_no = extract_regulation_no(title)
    if not reg_no and text:
        # 标题无文号时，优先在正文“文号/发文字号”标注附近提取，再退回正文开头
        m = re.search(r"(发文字号|发文编号|文号|字号)\s*[:：]?\s*([^\n，。；]{2,40})", text)
        if m:
            reg_no = extract_regulation_no(m.group(2))
        if not reg_no:
            reg_no = extract_regulation_no(text[:300])

    if reg_no:
        reg = session.scalar(select(Regulation).where(Regulation.regulation_no == reg_no))
        if reg is not None:
            return reg

    norm = normalize_title(title)
    best: Optional[Regulation] = None
    best_ratio = 0.0
    if norm:
        for reg in session.scalars(select(Regulation)).all():
            ratio = difflib.SequenceMatcher(None, norm, normalize_title(reg.canonical_title or "")).ratio()
            if ratio > best_ratio:
                best, best_ratio = reg, ratio
    if best is not None and best_ratio >= _SIMILARITY_THRESHOLD:
        if reg_no and not best.regulation_no:
            best.regulation_no = reg_no
        return best

    reg = Regulation(
        canonical_title=title or "未命名法规",
        regulation_no=reg_no,
        authority=extract_authority(text),
    )
    session.add(reg)
    session.flush()
    return reg
