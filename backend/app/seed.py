"""Seed demo data: users (with passwords), whitelisted sources, subscriptions.

Run inside the backend container:  python -m app.seed
"""
from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.models import ImpactLevel, Source, SourceType, Subscription, User


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.scalar(select(User).limit(1)) is None:
            db.add_all([
                User(
                    username="admin",
                    display_name="平台管理员",
                    role="admin",
                    password_hash=hash_password(settings.admin_password),
                ),
                User(
                    username="analyst",
                    display_name="合规分析师",
                    role="analyst",
                    password_hash=hash_password(settings.analyst_password),
                ),
            ])

        if db.scalar(select(Source).limit(1)) is None:
            db.add_all([
                Source(
                    name="示例监管机构-公告页",
                    url="https://example.com/regulations",
                    source_type=SourceType.regulator,
                    allowed_hosts="example.com",
                    frequency_minutes=1440,
                    follow_links=True,
                    max_links=20,
                    notes="演示来源：监管机构公告页面（白名单内），采集入口页并跟进正文链接",
                ),
                Source(
                    name="示例行业协会-通知页",
                    url="https://www.iana.org/help/example-domains",
                    source_type=SourceType.association,
                    allowed_hosts="iana.org,www.iana.org",
                    frequency_minutes=720,
                    follow_links=True,
                    max_links=10,
                    notes="演示来源：可真实抓取的公开页面，跟进页内 iana.org 白名单链接",
                ),
                Source(
                    name="示例征求意见页",
                    url="https://example.org/consultation",
                    source_type=SourceType.consultation,
                    allowed_hosts="example.org",
                    frequency_minutes=360,
                    follow_links=True,
                    max_links=20,
                    notes="演示来源：公开征求意见页面",
                ),
            ])

        if db.scalar(select(Subscription).limit(1)) is None:
            db.add_all([
                Subscription(
                    name="全部变更（站内）",
                    subscriber="analyst",
                    keyword="",
                    min_impact=ImpactLevel.low,
                    channel="inapp",
                ),
                Subscription(
                    name="高影响变更（邮件）",
                    subscriber="analyst",
                    keyword="",
                    min_impact=ImpactLevel.low,
                    channel="email",
                    email="compliance-team@example.com",
                ),
            ])

        db.commit()
        print("Seed completed.")
        print(f"  admin / {settings.admin_password}    (管理员，可管理来源与触发采集)")
        print(f"  analyst / {settings.analyst_password} (分析师，可复核/研判/订阅)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
