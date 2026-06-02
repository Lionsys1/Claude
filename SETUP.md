# Lionsys Opportunity Monitor — Setup Guide

## What This Does
Runs every weekday at 6 AM Eastern and emails you new IT subcontracting opportunities from:
- **FedTech** (fedtech.io/programs)
- **SBA SUBNet** (eweb1.sba.gov/subnet)
- **SAM.gov** (optional, requires free API key)

---

## One-Time Setup (15 minutes)

### Step 1 — Gmail App Password

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (if not already on)
3. Search for **"App Passwords"** in Google Account settings
4. Create a new App Password:
   - App: **Mail**
   - Device: **Other** → type `Lionsys Monitor`
5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`)

### Step 2 — Add GitHub Secrets

In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these 3 required secrets:

| Secret Name | Value |
|---|---|
| `EMAIL_USER` | The Gmail address that sends alerts (e.g. `alerts@lionsyssolutions.com`) |
| `EMAIL_PASSWORD` | The 16-char App Password from Step 1 (no spaces) |
| `RECIPIENTS` | Comma-separated list: `info@lionsyssolutions.com,sandeep891kaur@gmail.com` |

Optional (adds SAM.gov monitoring — free):

| Secret Name | Value |
|---|---|
| `SAM_GOV_API_KEY` | Get free key at sam.gov → Profile → API keys |

### Step 3 — Test It Manually

1. Go to your repo → **Actions** tab
2. Click **"Lionsys Opportunity Monitor"**
3. Click **"Run workflow"** → **"Run workflow"** button
4. Watch it run — check your email in ~2 minutes

---

## Email Format

**Subject:** `[LIONSYS ALERT] 3 New Opportunities — Top Score 87`

Each opportunity shows:
- Source (SAM.gov / SBA SUBNet / FedTech)
- Title + link
- **Match score** (0–100) based on Lionsys keywords
- Why it matched (e.g. "Salesforce +25", "Cloud Migration +18")
- Response deadline

Scores below 20 are filtered out automatically.

---

## Keyword Scoring (customize in scripts/scoring.py)

High-value matches: AI/GenAI (25pts), Salesforce (25pts), Data Analytics (20pts), CRM (20pts), Cloud Migration (18pts), Digital Transformation (18pts), Azure/AWS (18pts)

Auto-rejected: construction, road, bridge, HVAC, landscaping, trucking, food service, security guard

---

## Cost
**$0/month** — GitHub Actions free tier gives 2,000 minutes/month. This workflow uses ~2 minutes per run × 22 weekdays = ~44 minutes/month.
