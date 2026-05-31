# Mutual Fund Tracker — Setup Guide

Live URL (once set up): `https://muralmu.github.io/mutual-fund-tracker/`

---

## Step 1 — Create the GitHub Repo

1. Go to https://github.com/new
2. Name it: `mutual-fund-tracker`
3. Set it to **Public** (required for free GitHub Pages)
4. **Do NOT** initialise with README — keep it empty
5. Click **Create repository**

---

## Step 2 — Push This Project to GitHub

Open Terminal and run these commands (copy-paste the whole block):

```bash
cd "/Users/mukesh/Downloads/Cowork Homebase/02 Projects/Mutual Fund Tracker"
git init
git add .
git commit -m "initial: mutual fund tracker"
git branch -M main
git remote add origin https://github.com/muralmu/mutual-fund-tracker.git
git push -u origin main
```

---

## Step 3 — Get Your Gmail App Password

> Gmail requires an "App Password" for SMTP access — your regular password won't work.

1. Go to https://myaccount.google.com/security
2. Make sure **2-Step Verification** is ON (required)
3. Search for **"App passwords"** in the search bar
4. Select app: **Mail** → Device: **Other** → name it `mutual-fund-tracker`
5. Copy the 16-character password shown (e.g. `abcd efgh ijkl mnop`)

---

## Step 4 — Add Secrets to GitHub

1. Go to: `https://github.com/muralmu/mutual-fund-tracker/settings/secrets/actions`
2. Click **New repository secret** and add these three:

| Secret Name | Value |
|---|---|
| `GMAIL_USER` | `mkm0007@gmail.com` |
| `GMAIL_APP_PASSWORD` | *(the 16-char app password from Step 3)* |
| `RECIPIENT_EMAIL` | `mkm0007@gmail.com` |

---

## Step 5 — Enable GitHub Pages

1. Go to: `https://github.com/muralmu/mutual-fund-tracker/settings/pages`
2. Under **Source**, select: **Deploy from a branch**
3. Branch: `main` → Folder: `/ (root)`
4. Click **Save**

The page will be live at `https://muralmu.github.io/mutual-fund-tracker/` within a minute.

---

## Step 6 — Test It Manually

1. Go to: `https://github.com/muralmu/mutual-fund-tracker/actions`
2. Click **Daily Mutual Fund Report**
3. Click **Run workflow** → **Run workflow**
4. Watch it run (~30 seconds)
5. Check your email + the GitHub Pages URL

---

## How It Runs Daily

- GitHub Actions triggers automatically at **9:30 PM IST** every day
- Fetches latest NAV from mfapi.in for all 7 funds
- Updates `index.html` on GitHub Pages
- Sends the same report to `mkm0007@gmail.com`

---

## Funds Being Tracked

| Fund | Plan | Scheme Code | Monthly SIP |
|---|---|---|---|
| HDFC Nifty 50 Index Fund | Direct | 119063 | ₹10,000 |
| ICICI Prudential NASDAQ 100 Index Fund | Direct | 149219 | ₹10,000 |
| Nippon India Small Cap Fund | Direct | 118778 | ₹8,000 |
| Nippon India Growth Mid Cap Fund | Regular | 100377 | ₹5,000 |
| UTI Nifty 200 Momentum 30 Index Fund | Regular | 148704 | ₹5,000 |
| ICICI Prudential Multi-Asset Fund | Regular | 101144 | ₹5,000 |
| SBI Silver ETF Fund of Fund | Direct | 152735 | ₹3,000 |
