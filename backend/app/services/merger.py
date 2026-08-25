import re
import hashlib
import logging
from typing import Optional
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models import Regulation, RegulationMergeLog, RegulationStatus

logger = logging.getLogger(__name__)


class RegulationMerger:
    def __init__(self, db: Session):
        self.db = db

    def find_duplicates(self, regulation: Regulation) -> list[tuple[Regulation, float, list[str]]]:
        candidates = self._find_candidates(regulation)
        matches = []

        for candidate in candidates:
            if candidate.id == regulation.id:
                continue
            confidence, reasons = self._calculate_similarity(regulation, candidate)
            if confidence >= 0.6:
                matches.append((candidate, confidence, reasons))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    def _find_candidates(self, regulation: Regulation) -> list[Regulation]:
        query = self.db.query(Regulation).filter(
            Regulation.id != regulation.id,
            Regulation.is_primary == True,
        )

        conditions = []
        if regulation.regulation_number:
            conditions.append(Regulation.regulation_number == regulation.regulation_number)
        if regulation.title:
            short_title = regulation.title[:100]
            conditions.append(Regulation.title.ilike(f"%{short_title}%"))

        if conditions:
            query = query.filter(or_(*conditions))

        return query.limit(50).all()

    def _calculate_similarity(
        self, reg1: Regulation, reg2: Regulation
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons = []

        if reg1.regulation_number and reg2.regulation_number:
            if self._normalize_reg_number(reg1.regulation_number) == self._normalize_reg_number(reg2.regulation_number):
                score += 0.6
                reasons.append("文号完全匹配")

        if reg1.title and reg2.title:
            title_sim = SequenceMatcher(
                None,
                self._normalize_title(reg1.title),
                self._normalize_title(reg2.title)
            ).ratio()
            score += title_sim * 0.25
            if title_sim > 0.8:
                reasons.append(f"标题高度相似 ({title_sim:.0%})")

        if reg1.issuing_authority and reg2.issuing_authority:
            if self._normalize_text(reg1.issuing_authority) == self._normalize_text(reg2.issuing_authority):
                score += 0.1
                reasons.append("发布机构相同")

        if reg1.publish_date and reg2.publish_date:
            if abs((reg1.publish_date - reg2.publish_date).days) <= 1:
                score += 0.05
                reasons.append("发布日期接近")

        if reg1.content_hash and reg2.content_hash and reg1.content_hash == reg2.content_hash:
            score = 1.0
            reasons.append("内容哈希完全一致")

        return min(score, 1.0), reasons

    def _normalize_reg_number(self, number: str) -> str:
        return re.sub(r"[\s\-_〔〕\[\]()（）]", "", number or "").lower()

    def _normalize_title(self, title: str) -> str:
        title = re.sub(r"[（(].*?[)）]", "", title)
        title = re.sub(r"[\s\-—_·]", "", title)
        return title.lower()

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", "", text or "").lower()

    def merge_regulations(
        self,
        primary_id: str,
        duplicate_id: str,
        confidence: float,
        reasons: list[str],
        merged_by: str = "manual",
    ) -> Optional[Regulation]:
        primary = self.db.query(Regulation).filter(Regulation.id == primary_id).first()
        duplicate = self.db.query(Regulation).filter(Regulation.id == duplicate_id).first()

        if not primary or not duplicate:
            return None

        group_id = primary.merge_group_id or primary.id
        primary.merge_group_id = group_id
        primary.merge_confidence = 1.0

        duplicate.is_primary = False
        duplicate.merge_group_id = group_id
        duplicate.merge_confidence = confidence
        duplicate.canonical_id = primary.id

        if not primary.regulation_number and duplicate.regulation_number:
            primary.regulation_number = duplicate.regulation_number
        if not primary.issuing_authority and duplicate.issuing_authority:
            primary.issuing_authority = duplicate.issuing_authority
        if not primary.publish_date and duplicate.publish_date:
            primary.publish_date = duplicate.publish_date
        if not primary.effective_date and duplicate.effective_date:
            primary.effective_date = duplicate.effective_date

        merge_log = RegulationMergeLog(
            primary_regulation_id=primary_id,
            duplicate_regulation_id=duplicate_id,
            confidence=confidence,
            match_reasons=reasons,
            merged_by=merged_by,
        )
        self.db.add(merge_log)
        self.db.commit()
        self.db.refresh(primary)

        logger.info(f"Merged regulation {duplicate_id} into {primary_id} (confidence: {confidence})")
        return primary

    def auto_merge(self, regulation: Regulation, threshold: float = 0.85) -> Optional[Regulation]:
        duplicates = self.find_duplicates(regulation)
        for candidate, confidence, reasons in duplicates:
            if confidence >= threshold:
                return self.merge_regulations(
                    primary_id=candidate.id,
                    duplicate_id=regulation.id,
                    confidence=confidence,
                    reasons=reasons,
                    merged_by="auto",
                )
        return None
