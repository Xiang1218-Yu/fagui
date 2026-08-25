"""Email delivery for subscription notifications via SMTP.

When SMTP is not configured (``settings.smtp_host`` empty) the email is not
actually sent but recorded as ``skipped`` with a clear reason, so the platform
degrades gracefully in demo/offline environments while the real SMTP path is
fully implemented for production.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def is_configured() -> bool:
    return bool(settings.smtp_host)


def send_email(to_addr: str, subject: str, body: str) -> tuple[str, str]:
    """Send an email. Returns (status, detail).

    status ∈ {"sent", "failed", "skipped"}.
    """
    if not to_addr:
        return "skipped", "no recipient address"
    if not is_configured():
        return "skipped", "SMTP 未配置（smtp_host 为空），仅站内记录"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        if settings.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.starttls(context=context)
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        return "sent", f"已发送至 {to_addr}"
    except Exception as exc:  # noqa: BLE001 - report any SMTP failure
        return "failed", f"SMTP 发送失败: {exc}"
