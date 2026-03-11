"""
Email delivery via SMTP (async).
Wraps aiosmtplib so the FastAPI event loop is never blocked.

Usage:
    result = await send_email(to="...", subject="...", body="...", cfg=settings)
"""

from __future__ import annotations

import logging
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from config import Settings

logger = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    cfg: Settings,
) -> tuple[bool, str | None, str | None]:
    """
    Send a plain-text email via SMTP.

    Returns:
        (success: bool, message_id: str | None, error: str | None)
    """
    if not cfg.smtp_user or not cfg.smtp_password:
        logger.warning("SMTP credentials not configured – email NOT sent.")
        return False, None, "SMTP credentials missing in environment."

    message_id = f"<{uuid.uuid4().hex}@firereach>"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{cfg.smtp_from_name} <{cfg.smtp_user}>"
    msg["To"] = to
    msg["Message-ID"] = message_id

    # Plain-text part
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Minimal HTML wrapper for email clients that prefer it
    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><title>{subject}</title></head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #1a1a1a; max-width: 640px; margin: 0 auto; padding: 32px 16px;">
  <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit;">{body}</pre>
  <hr style="margin-top: 40px; border: none; border-top: 1px solid #e0e0e0;" />
  <p style="font-size: 12px; color: #888;">Sent by FireReach Autonomous Outreach Engine</p>
</body>
</html>
"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=cfg.smtp_host,
            port=cfg.smtp_port,
            username=cfg.smtp_user,
            password=cfg.smtp_password,
            start_tls=True,
            timeout=20,
        )
        logger.info("Email sent to %s (id=%s)", to, message_id)
        return True, message_id, None

    except aiosmtplib.SMTPException as exc:
        logger.error("SMTP error sending to %s: %s", to, exc)
        return False, None, str(exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error sending email: %s", exc)
        return False, None, str(exc)
