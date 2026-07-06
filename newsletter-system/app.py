import csv
import io
import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for

load_dotenv()

import db
import mailer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

db.init_db()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def parse_pasted_emails(text: str) -> list[dict]:
    """Accepts lines like 'email' or 'Name,email' or 'Name <email>'."""
    entries = []
    for line in (text or "").splitlines():
        line = line.strip().strip(",")
        if not line:
            continue
        name = ""
        email = line
        if "," in line:
            parts = [p.strip() for p in line.split(",", 1)]
            if "@" in parts[-1]:
                name, email = (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])
        elif "<" in line and ">" in line:
            name = line.split("<")[0].strip()
            email = line.split("<")[1].split(">")[0].strip()
        entries.append({"name": name, "email": email})
    return entries


def parse_csv_upload(file_storage) -> list[dict]:
    content = file_storage.read().decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    entries = []
    for row in reader:
        normalized = {k.strip().lower(): v for k, v in row.items() if k}
        email = normalized.get("email", "").strip()
        name = normalized.get("name", "").strip()
        if email:
            entries.append({"name": name, "email": email})
    return entries


# ---------- Public routes ----------

@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("logged_in") else url_for("login"))


@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        name = request.form.get("name", "").strip()
        if not email or "@" not in email:
            flash("Please enter a valid email address.")
            return redirect(url_for("subscribe"))
        db.upsert_subscriber(email, name, source="form")
        return render_template("subscribed.html", email=email)
    return render_template("subscribe.html")


@app.route("/unsubscribe")
def unsubscribe():
    email = request.args.get("email", "")
    token = request.args.get("token", "")
    success = db.unsubscribe(email, token) if email and token else False
    return render_template("unsubscribed.html", success=success, email=email)


# ---------- Auth ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password and password == os.environ.get("ADMIN_PASSWORD"):
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Incorrect password.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Admin ----------

@app.route("/dashboard")
@login_required
def dashboard():
    counts = db.get_subscriber_counts()
    recent = db.get_recent_sends()
    return render_template("dashboard.html", counts=counts, recent=recent)


@app.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    templates = mailer.available_templates()
    preview_html = None
    form_data = {
        "template": templates[0] if templates else "modern",
        "subject": "",
        "preheader": "",
        "headline": "",
        "body_html": "",
        "cta_text": "",
        "cta_url": "",
        "hero_image_url": "",
        "recipients_mode": "all",
        "pasted_emails": "",
    }

    if request.method == "POST":
        for key in form_data:
            if key in request.form:
                form_data[key] = request.form.get(key, "")

        action = request.form.get("action")
        content = {
            "subject": form_data["subject"],
            "preheader": form_data["preheader"],
            "headline": form_data["headline"],
            "body_html": form_data["body_html"],
            "cta_text": form_data["cta_text"],
            "cta_url": form_data["cta_url"],
            "hero_image_url": form_data["hero_image_url"],
        }

        if action == "preview":
            preview_html = mailer.render_newsletter(
                form_data["template"],
                content,
                recipient={"email": "preview@example.com", "name": "Jane", "token": "preview"},
            )

        elif action == "send_test":
            test_email = request.form.get("test_email", "").strip()
            if not test_email:
                flash("Enter an email address to send the test to.")
            else:
                try:
                    mailer.send_test_email(form_data["template"], content, test_email)
                    flash(f"Test email sent to {test_email}.")
                except Exception as exc:  # noqa: BLE001
                    flash(f"Failed to send test: {exc}")

        elif action == "send_all":
            recipients_mode = form_data["recipients_mode"]
            new_entries = []
            if recipients_mode == "paste":
                new_entries = parse_pasted_emails(form_data["pasted_emails"])
            elif recipients_mode == "upload":
                uploaded = request.files.get("csv_file")
                if uploaded and uploaded.filename:
                    new_entries = parse_csv_upload(uploaded)

            if new_entries:
                db.bulk_upsert(new_entries, source="manual" if recipients_mode == "paste" else "upload")

            recipients = db.get_active_subscribers()
            if not recipients:
                flash("No active subscribers to send to.")
            else:
                try:
                    result = mailer.send_bulk(form_data["template"], content, recipients)
                except Exception as exc:  # noqa: BLE001 - surface SMTP/connection errors as a flash, not a 500
                    flash(f"Could not connect to the mail server: {exc}")
                else:
                    db.log_send(
                        form_data["subject"], form_data["template"], result["sent"], result["failed"]
                    )
                    msg = f"Sent to {result['sent']} recipients."
                    if result["failed"]:
                        msg += f" {result['failed']} failed."
                    flash(msg)
                    return redirect(url_for("dashboard"))

    counts = db.get_subscriber_counts()
    return render_template(
        "compose.html",
        templates=templates,
        form_data=form_data,
        preview_html=preview_html,
        counts=counts,
    )


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
