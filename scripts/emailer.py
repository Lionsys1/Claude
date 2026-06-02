import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def build_html(opportunities: list) -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    rows = ""
    for opp in opportunities:
        score = opp.get("score", 0)
        score_color = "#2e7d32" if score >= 60 else "#f57c00" if score >= 35 else "#555"
        reasons_html = "".join(
            f'<span style="background:#e3f2fd;padding:2px 6px;border-radius:3px;margin:2px;display:inline-block;font-size:12px">{r}</span>'
            for r in opp.get("reasons", [])
        )
        rows += f"""
        <div style="border:1px solid #ddd;border-radius:6px;padding:16px;margin-bottom:16px;background:#fff">
          <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div style="flex:1">
              <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px">{opp.get('source','')}</div>
              <div style="font-size:16px;font-weight:600;color:#1a1a2e;margin:4px 0">
                <a href="{opp.get('url','#')}" style="color:#1a1a2e;text-decoration:none">{opp.get('title','Untitled')}</a>
              </div>
              {f'<div style="font-size:13px;color:#555;margin-top:4px">Response deadline: {opp.get("response_date","")}</div>' if opp.get('response_date') else ''}
            </div>
            <div style="background:{score_color};color:#fff;font-size:22px;font-weight:700;padding:8px 14px;border-radius:6px;margin-left:12px;min-width:48px;text-align:center">{score}</div>
          </div>
          <div style="margin-top:10px">{reasons_html}</div>
          {f'<div style="font-size:13px;color:#555;margin-top:8px;line-height:1.5">{opp.get("description","")[:300]}...</div>' if opp.get('description') else ''}
          <div style="margin-top:10px">
            <a href="{opp.get('url','#')}" style="background:#1565c0;color:#fff;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:13px">View Opportunity →</a>
          </div>
        </div>"""

    count = len(opportunities)
    top_score = max((o.get("score", 0) for o in opportunities), default=0) if opportunities else 0

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;background:#f5f7fa;margin:0;padding:0">
  <div style="max-width:680px;margin:0 auto;padding:20px">
    <div style="background:#1a1a2e;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <div style="font-size:20px;font-weight:700">🦁 Lionsys Opportunity Alert</div>
      <div style="font-size:13px;opacity:.8;margin-top:4px">{date_str} · {count} new opportunit{'y' if count == 1 else 'ies'} · Top score: {top_score}</div>
    </div>
    <div style="background:#f5f7fa;padding:20px">
      {rows if rows else '<p style="color:#555">No new relevant opportunities found today.</p>'}
    </div>
    <div style="background:#eee;padding:12px 24px;border-radius:0 0 8px 8px;font-size:11px;color:#888;text-align:center">
      Sources: SAM.gov · SBA SUBNet · FedTech · Lionsys Solutions automated monitor
    </div>
  </div>
</body>
</html>"""
    return html


def send_email(opportunities: list):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipients_raw = os.environ.get("RECIPIENTS", "")
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    if not recipients:
        print("[Emailer] No recipients configured.")
        return

    count = len(opportunities)
    top_score = max((o.get("score", 0) for o in opportunities), default=0) if opportunities else 0

    if count == 0:
        subject = f"[LIONSYS] No new opportunities today"
    else:
        subject = f"[LIONSYS ALERT] {count} New Opportunit{'y' if count == 1 else 'ies'} — Top Score {top_score}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    plain_parts = []
    for opp in opportunities:
        plain_parts.append(
            f"[{opp.get('source','')}] {opp.get('title','')} — Score: {opp.get('score',0)}\n"
            f"  {opp.get('url','')}\n"
            f"  Why: {', '.join(opp.get('reasons', []))}\n"
        )
    plain_body = f"Lionsys Opportunity Alert — {datetime.now().strftime('%B %d, %Y')}\n\n"
    plain_body += "\n".join(plain_parts) if plain_parts else "No new relevant opportunities today."

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(build_html(opportunities), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.sendmail(sender, recipients, msg.as_string())

    print(f"[Emailer] Sent alert to {recipients} — {count} opportunities.")


if __name__ == "__main__":
    # Quick test with dummy data
    test = [
        {
            "title": "Salesforce CRM Modernization Support",
            "url": "https://example.com",
            "description": "Looking for a subcontractor to help migrate legacy CRM to Salesforce cloud platform.",
            "source": "SBA SUBNet",
            "score": 85,
            "reasons": ["Salesforce (+25)", "Cloud Migration (+18)", "CRM (+20)"],
            "response_date": "2026-06-30",
        }
    ]
    send_email(test)
