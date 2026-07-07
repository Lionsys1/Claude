import os
import re
import time
import smtplib
import requests
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


# ---------- Sending transports ----------
# Two ways to actually hand the email to Microsoft: plain SMTP with a
# username/app-password ("Basic Auth"), or OAuth via the Graph API. Pick
# with SEND_METHOD=smtp|graph in .env. Graph is the one to use if your
# Microsoft 365 tenant has Security Defaults / Conditional Access blocking
# basic auth — see README for setup of either.

class _SmtpTransport:
    def __init__(self):
        host = os.environ.get("SMTP_HOST", "smtp.office365.com")
        port = int(os.environ.get("SMTP_PORT", "587"))
        self.sender = os.environ["EMAIL_USER"]
        password = os.environ["EMAIL_PASSWORD"]

        self.smtp = smtplib.SMTP(host, port, timeout=30)
        self.smtp.ehlo()
        self.smtp.starttls()
        self.smtp.ehlo()
        self.smtp.login(self.sender, password)

    def send(self, to_email: str, subject: str, html: str, plain: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to_email
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))
        self.smtp.sendmail(self.sender, [to_email], msg.as_string())

    def close(self):
        self.smtp.quit()


class _GraphTransport:
    """Sends via Microsoft Graph using OAuth2 client-credentials (app-only) auth.
    Requires an Entra ID app registration with Mail.Send application permission
    and admin consent — see README for the exact setup steps."""

    TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    SEND_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

    def __init__(self):
        self.sender = os.environ["EMAIL_USER"]
        tenant_id = os.environ["AZURE_TENANT_ID"]
        client_id = os.environ["AZURE_CLIENT_ID"]
        client_secret = os.environ["AZURE_CLIENT_SECRET"]

        resp = requests.post(
            self.TOKEN_URL.format(tenant=tenant_id),
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Could not get an access token ({resp.status_code}): {resp.text[:300]}")
        self.access_token = resp.json()["access_token"]

    def send(self, to_email: str, subject: str, html: str, plain: str):
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": "true",
        }
        resp = requests.post(
            self.SEND_URL.format(sender=self.sender),
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code >= 300:
            raise RuntimeError(f"Graph sendMail failed ({resp.status_code}): {resp.text[:300]}")

    def close(self):
        pass


def _open_transport():
    method = os.environ.get("SEND_METHOD", "smtp").strip().lower()
    if method == "graph":
        return _GraphTransport()
    return _SmtpTransport()


def send_test_email(template_name: str, content: dict, to_email: str) -> None:
    html = render_newsletter(template_name, content, recipient={"email": to_email, "name": "", "token": "preview"})
    plain = _strip_tags(content.get("body_html", ""))

    transport = _open_transport()
    try:
        transport.send(to_email, f"[TEST] {content.get('subject', '')}", html, plain)
    finally:
        transport.close()


def send_bulk(template_name: str, content: dict, recipients: list[dict]) -> dict:
    """recipients: [{'email', 'name', 'token'}, ...]. Returns {'sent': n, 'failed': n, 'errors': [...]}"""
    delay = float(os.environ.get("SEND_DELAY_SECONDS", "0.4"))

    sent = 0
    failed = 0
    errors = []

    transport = _open_transport()
    try:
        for recipient in recipients:
            email = recipient.get("email")
            try:
                html = render_newsletter(template_name, content, recipient=recipient)
                plain = _strip_tags(content.get("body_html", ""))
                transport.send(email, content.get("subject", ""), html, plain)
                sent += 1
            except Exception as exc:  # noqa: BLE001 - log and keep going, one bad address shouldn't kill the batch
                failed += 1
                errors.append(f"{email}: {exc}")
            time.sleep(delay)
    finally:
        transport.close()

    return {"sent": sent, "failed": failed, "errors": errors}
