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
| `SEND_METHOD` | `smtp` (default) or `graph` — see the two options below. |
| `EMAIL_USER` | The mailbox you're sending from, either way. |
| `EMAIL_PASSWORD` | Only for `SEND_METHOD=smtp` — an app password, not your login password. |
| `SMTP_HOST` / `SMTP_PORT` | Only for `SEND_METHOD=smtp` — `smtp-mail.outlook.com:587` for personal Outlook.com/Hotmail, `smtp.office365.com:587` for work/school Microsoft 365. |
| `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` | Only for `SEND_METHOD=graph` — from your Entra ID app registration, see below. |
| `ADMIN_PASSWORD` | Password to log into `/dashboard` and `/compose`. Keep this private — anyone with it can send to your whole list. |
| `FLASK_SECRET_KEY` | Random string used to sign login sessions. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `BASE_URL` | The public URL where this app is reachable (see "Deploying" below). Used to build unsubscribe links. |
| `COMPANY_NAME` / `COMPANY_ADDRESS` | Shown in every email footer — required by the CAN-SPAM Act (see Compliance section). |

There are two ways this app can actually send mail. Use **Option A** if you
have (or can get) an app password. Use **Option B** if your Microsoft 365
tenant blocks that — most work/school tenants with Security Defaults or
Conditional Access on will.

### Option A: SMTP with an app password (`SEND_METHOD=smtp`)

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

### Why this might get blocked, and how to make sure it doesn't

This tool authenticates to SMTP with a username + app password ("Basic
Auth"). Microsoft is in the middle of retiring that method for **work/school
Microsoft 365 accounts** (not personal Outlook.com), so read this before you
assume a connection failure is a bug in the code:

- **Right now (as of mid-2026)**: Basic Auth for SMTP AUTH still works for
  Microsoft 365 tenants that have it enabled — nothing changes automatically
  yet.
- **End of December 2026**: Microsoft turns SMTP AUTH Basic Auth **off by
  default** for tenants that haven't been actively using it. Admins can
  still turn it back on per mailbox.
- **Later (date TBD, to be announced in H2 2027)**: Microsoft plans to
  retire it permanently, with no way to re-enable it — at that point
  sending mail requires OAuth 2.0 (e.g. via the Microsoft Graph API) instead
  of SMTP + password.
- Personal Outlook.com/Hotmail accounts are **not** on this deprecation
  path — app passwords there are expected to keep working.

**What to actually do:**

1. If you're on a **work/school Microsoft 365 account**, go to the Microsoft
   365 admin center → Active users → your account → **Mail** tab → **Manage
   email apps** → make sure **"Authenticated SMTP"** is checked, and do this
   soon (before the Dec 2026 default flip) rather than waiting until it
   breaks.
2. If your organization has **Security Defaults** or **Conditional Access**
   turned on, Basic Auth may be blocked outright regardless of the toggle
   above — in that case there is no app-password option at all, and this
   SMTP approach won't work until an admin carves out an exception, or you
   switch to sending via the Microsoft Graph API (OAuth) instead. Tell me if
   you hit this and I'll add a Graph API sending path as an alternative.
3. If you're on **personal Outlook.com**, none of the above applies — an
   app password from `account.live.com` should keep working.
4. Regardless of account type, to avoid being flagged/throttled as spammy:
   don't disable the built-in `SEND_DELAY_SECONDS` throttle, don't send to
   large lists of unverified/bounced addresses, and keep the unsubscribe
   link and company address in the footer (both are already built in and
   required by CAN-SPAM).

### Option B: Microsoft Graph API / OAuth (`SEND_METHOD=graph`)

Use this if you're an admin and app passwords aren't available (Security
Defaults / Conditional Access blocking basic auth is the usual reason). This
registers your own script as a trusted application inside your Microsoft
365 tenant. Instead of a username + password, it authenticates with a
Client ID and a secret key, gets a short-lived access token from Microsoft,
and calls the Graph API directly to send mail — no SMTP, no basic auth, so
none of the Security Defaults / Conditional Access restrictions apply.

**One-time setup, done by an admin:**

1. Go to **entra.microsoft.com** (or `portal.azure.com` → search "App
   registrations").
2. **App registrations → New registration.**
   - Name: anything, e.g. `Newsletter Sender`.
   - Supported account types: "Accounts in this organizational directory
     only" (single tenant).
   - Click **Register**.
3. On the app's **Overview** page, copy:
   - **Application (client) ID** → this is `AZURE_CLIENT_ID`.
   - **Directory (tenant) ID** → this is `AZURE_TENANT_ID`.
4. Go to **Certificates & secrets → Client secrets → New client secret**.
   - Give it a description and expiry (e.g. 12 months — you'll need to
     rotate it before it expires).
   - Copy the secret's **Value** immediately — this is `AZURE_CLIENT_SECRET`,
     and it's only shown once.
5. Go to **API permissions → Add a permission → Microsoft Graph →
   Application permissions** (not Delegated) → search "Mail" → check
   **`Mail.Send`** → **Add permissions**.
6. Click **Grant admin consent for [your organization]** and confirm. The
   permission should now show a green checkmark under "Status".
7. (Recommended, not required to get started) By default `Mail.Send`
   application permission lets this app send as *any* mailbox in your
   tenant. To restrict it to only the one newsletter mailbox, run this once
   in Exchange Online PowerShell (`Connect-ExchangeOnline` first):
   ```powershell
   New-ApplicationAccessPolicy -AppId <your-client-id> `
     -PolicyScopeGroupId <your-sending-mailbox@yourdomain.com> `
     -AccessRight RestrictAccess `
     -Description "Newsletter Sender can only send as this one mailbox"
   ```

8. In `.env`, set:
   ```
   SEND_METHOD=graph
   EMAIL_USER=your-sending-mailbox@yourdomain.com
   AZURE_TENANT_ID=<from step 3>
   AZURE_CLIENT_ID=<from step 3>
   AZURE_CLIENT_SECRET=<from step 4>
   ```

That's it — no app password, no SMTP host, and it keeps working even after
Microsoft finishes retiring Basic Auth for SMTP entirely.

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
├── mailer.py                 Template rendering + sending (SMTP or Graph API)
├── newsletter_templates/     The actual newsletter HTML (what recipients see)
│   ├── modern.html
│   └── corporate.html
├── templates/                The admin/subscribe web UI (not the newsletter)
├── static/style.css
├── data/sample_recipients.csv
└── .env.example
```
