import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


async def send_email(to: str, subject: str, body: str) -> None:
    if not settings.smtp_user or not settings.smtp_password:
        logger.info(
            "Email (console fallback) → to=%s subject=%s\n%s",
            to,
            subject,
            body,
        )
        return

    import aiosmtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, subtype="html")
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=True,
        username=settings.smtp_user,
        password=settings.smtp_password,
    )


async def send_templated_email(to: str, template_name: str, context: dict) -> None:
    """Load an HTML template, replace {key} placeholders, and send."""
    template_path = TEMPLATES_DIR / f"{template_name}.html"
    if not template_path.exists():
        logger.warning("Email template not found: %s", template_path)
        return

    html = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        html = html.replace(f"{{{key}}}", str(value))

    subject_map = {
        "low_attendance": "Low Attendance Alert — SmartAttend",
        "proxy_alert": "Proxy Attendance Detected — SmartAttend",
        "daily_digest": "Daily Attendance Digest — SmartAttend",
        "password_reset": "Password Reset Request — SmartAttend",
        "verification": "Verify Your Email — SmartAttend",
    }
    subject = subject_map.get(template_name, f"SmartAttend — {template_name}")

    await send_email(to, subject, html)
