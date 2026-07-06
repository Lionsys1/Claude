import os
import re
import time
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "newsletter_templates")

_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(disabled_extensions=("txt",)),
)


def available_templates() -> list[str]:
    return sorted(
        f[:-5] for f in os.listdir(TEMPLATE_DIR) if f.endswith(".html")
    )


def _strip_tags(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def build_unsubscribe_url(email: str, token: str) -> str:
    base_url = os.environ.get("BASE_URL", "http://localhost:5000").rstrip("/")
    return f"{base_url}/unsubscribe?email={quote(email)}&token={quote(token)}"


def render_newsletter(template_name: str, content: dict, recipient: dict | None = None) -> str:
    """content: subject, preheader, headline, body_html, cta_text, cta_url, hero_image_url.
    recipient: {'email', 'name', 'token'} — optional, used to fill personalized fields."""
    template = _env.get_template(f"{template_name}.html")
    recipient = recipient or {}
    context = {
        "subject": content.get("subject", ""),
        "preheader": content.get("preheader", ""),
        "headline": content.get("headline", ""),
        "body_html": content.get("body_html", ""),
        "cta_text": content.get("cta_text", ""),
        "cta_url": content.get("cta_url", ""),
        "hero_image_url": content.get("hero_image_url", ""),
        "recipient_name": recipient.get("name", ""),
        "company_name": os.environ.get("COMPANY_NAME", "Your Company"),
        "company_address": os.environ.get("COMPANY_ADDRESS", "Add your mailing address in .env"),
        "issue_date": datetime.now().strftime("%B %d, %Y"),
        "year": datetime.now().year,
        "unsubscribe_url": build_unsubscribe_url(
            recipient.get("email", "preview@example.com"),
            recipient.get("token", "preview"),
        )
        if recipient.get("email")
        else "#",
    }
    return template.render(**context)


def _smtp_connect():
    host = os.environ.get("SMTP_HOST", "smtp.office365.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASSWORD"]

    smtp = smtplib.SMTP(host, port, timeout=30)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(user, password)
    return smtp


def send_test_email(template_name: str, content: dict, to_email: str) -> None:
    html = render_newsletter(template_name, content, recipient={"email": to_email, "name": "", "token": "preview"})
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[TEST] {content.get('subject', '')}"
    msg["From"] = os.environ["EMAIL_USER"]
    msg["To"] = to_email
    msg.attach(MIMEText(_strip_tags(content.get("body_html", "")), "plain"))
    msg.attach(MIMEText(html, "html"))

    with _smtp_connect() as smtp:
        smtp.sendmail(os.environ["EMAIL_USER"], [to_email], msg.as_string())


def send_bulk(template_name: str, content: dict, recipients: list[dict]) -> dict:
    """recipients: [{'email', 'name', 'token'}, ...]. Returns {'sent': n, 'failed': n, 'errors': [...]}"""
    sender = os.environ["EMAIL_USER"]
    delay = float(os.environ.get("SEND_DELAY_SECONDS", "0.4"))

    sent = 0
    failed = 0
    errors = []

    smtp = _smtp_connect()
    try:
        for recipient in recipients:
            email = recipient.get("email")
            try:
                html = render_newsletter(template_name, content, recipient=recipient)
                msg = MIMEMultipart("alternative")
                msg["Subject"] = content.get("subject", "")
                msg["From"] = sender
                msg["To"] = email
                msg.attach(MIMEText(_strip_tags(content.get("body_html", "")), "plain"))
                msg.attach(MIMEText(html, "html"))

                smtp.sendmail(sender, [email], msg.as_string())
                sent += 1
            except Exception as exc:  # noqa: BLE001 - log and keep going, one bad address shouldn't kill the batch
                failed += 1
                errors.append(f"{email}: {exc}")
            time.sleep(delay)
    finally:
        smtp.quit()

    return {"sent": sent, "failed": failed, "errors": errors}
