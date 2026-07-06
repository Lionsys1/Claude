# Newsletter System

A small, self-hosted newsletter tool that sends **through your own Outlook /
Office 365 account** (not a third-party ESP), so there's no "sent via
Mailchimp/SendGrid" branding anywhere. It includes:

- Two professional, Outlook-safe HTML newsletter templates ("modern" and
  "corporate") you compose in a web form — no HTML editor required.
- A subscriber database with a public **subscribe** page and working
  **unsubscribe** links in every email (required by law — see below).
- A compose screen where you can send to your whole list, paste a list of
  emails, or upload a CSV — plus a "send test to myself" button before you
  commit to the real send.

This is *not* a mass-marketing platform (Outlook/Office 365 will throttle or
flag you if you try to blast tens of thousands of emails). It's built for
sending a real, professional-looking newsletter to a list in the hundreds
through an account you control.

## 1. Setup

```bash
cd newsletter-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

| Variable | What it's for |
|---|---|
| `EMAIL_USER` / `EMAIL_PASSWORD` | The Outlook/Office 365 account you'll send from. |
| `SMTP_HOST` / `SMTP_PORT` | Defaults to `smtp.office365.com:587`, works for both Outlook.com and Office 365 work/school accounts. |
| `ADMIN_PASSWORD` | Password to log into `/dashboard` and `/compose`. Keep this private — anyone with it can send to your whole list. |
| `FLASK_SECRET_KEY` | Random string used to sign login sessions. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `BASE_URL` | The public URL where this app is reachable (see "Deploying" below). Used to build unsubscribe links. |
| `COMPANY_NAME` / `COMPANY_ADDRESS` | Shown in every email footer — required by the CAN-SPAM Act (see Compliance section). |

### Getting an Outlook / Office 365 app password

Outlook and Office 365 usually block plain password SMTP login when
multi-factor authentication is on, so you'll need an **app password** instead
of your normal login password:

- **Personal Outlook.com/Hotmail account**: sign in at
  `account.live.com` → Security → Advanced security options → App passwords
  → Create a new app password. Use that as `EMAIL_PASSWORD`.
- **Work/school Office 365 account**: go to `myaccount.microsoft.com` →
  Security info → Add sign-in method → App password. If you don't see that
  option, your organization's admin has to enable "SMTP AUTH" and app
  passwords for your mailbox (Exchange Admin Center → mail flow / Azure AD
  security defaults).

### Run it locally

```bash
python app.py
```

Visit `http://localhost:5000` and log in with `ADMIN_PASSWORD`.

## 2. Using it

1. **Log in** at `/login`.
2. **Compose** (`/compose`): pick a template style, write your subject,
   headline, and body (basic HTML like `<p>`, `<b>`, `<a>`, `<ul>` is fine),
   optionally add a hero image URL and a call-to-action button.
3. **Preview** before sending — renders exactly what recipients will see.
4. **Send a test** to yourself first. Always do this.
5. **Choose recipients**:
   - *All active subscribers* — everyone who's opted in and hasn't
     unsubscribed.
   - *Paste emails* — one per line, `email`, `Name, email`, or
     `Name <email>`. These get added to your subscriber list automatically.
   - *Upload CSV* — columns `email` and (optional) `name`. See
     `data/sample_recipients.csv` for the format.
6. **Send**. Each recipient gets a personalized copy with their own
   unsubscribe link. A short delay is added between sends to stay within
   normal sending patterns.

The dashboard (`/dashboard`) shows your subscriber counts and a log of past
sends.

## 3. Subscribe / unsubscribe (what these actually do)

- **Subscribe** (`/subscribe`, public): anyone can visit this page and enter
  their email to opt in. It's added to the subscriber database
  immediately (single opt-in). Share this link on your website or in your
  email signature.
- **Unsubscribe**: every newsletter includes a link like
  `/unsubscribe?email=...&token=...`. The token is a long random string
  unique to that subscriber, so nobody can unsubscribe someone else by
  guessing their email. Clicking it flips that subscriber to
  "unsubscribed" — they're automatically excluded from future sends, but
  stay in the database (so they can't be silently re-added later).

If you want fewer spam complaints, a common upgrade is **double opt-in**:
send a confirmation email after someone subscribes and only mark them
active once they click a confirm link. Not implemented here, but the
`db.py` schema and `/subscribe` route are the place to add it.

## 4. Deploying (so subscribe/unsubscribe links work for real recipients)

Running only on `localhost` is fine for testing, but a recipient clicking
"unsubscribe" from their inbox needs a real public URL to hit. Any small
Python-hosting option works, e.g. Render, Railway, Fly.io, or a small VPS.
Whatever you pick:

1. Set `BASE_URL` in the environment to the real public URL (e.g.
   `https://newsletter.yourdomain.com`).
2. Set all the same environment variables from `.env` in that host's
   environment variable settings (don't commit `.env`).
3. Use a real WSGI server for production instead of Flask's dev server,
   e.g. `gunicorn app:app`.
4. The SQLite file (`subscribers.db`) needs to live on persistent storage —
   most platforms with ephemeral filesystems (some free tiers) will wipe it
   on redeploy, so check that before relying on it.

## 5. Compliance (US CAN-SPAM Act — applies to commercial email)

This tool builds in the two hard requirements:

- A working, one-click unsubscribe link in every email.
- Your real postal address in every email footer (`COMPANY_ADDRESS`).

You're still responsible for: honoring unsubscribes within 10 business days
(this tool does it immediately), not using deceptive subject lines, and
identifying the message as an ad if it is one. If you have EU/UK/Canada
subscribers, GDPR/CASL have similar but stricter consent rules — worth a
look before sending internationally at any real volume.

## File structure

```
newsletter-system/
├── app.py                    Flask app: routes, auth, recipient handling
├── db.py                     SQLite subscriber storage
├── mailer.py                 Template rendering + SMTP sending
├── newsletter_templates/     The actual newsletter HTML (what recipients see)
│   ├── modern.html
│   └── corporate.html
├── templates/                The admin/subscribe web UI (not the newsletter)
├── static/style.css
├── data/sample_recipients.csv
└── .env.example
```
