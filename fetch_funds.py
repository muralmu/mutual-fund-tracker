import requests
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

# ── Fund Configuration ──────────────────────────────────────────────────────
FUNDS = [
    {
        "name": "HDFC Nifty 50 Index Fund",
        "scheme": "119063", "plan": "Direct", "sip": 10000,
        "benchmark_name": "UTI Nifty 50 Direct", "benchmark_scheme": "120716"
    },
    {
        "name": "ICICI Prudential NASDAQ 100 Index Fund",
        "scheme": "149219", "plan": "Direct", "sip": 10000,
        "benchmark_name": "Mirae FANG+ ETF FoF Direct", "benchmark_scheme": "148928"
    },
    {
        "name": "Nippon India Small Cap Fund",
        "scheme": "118778", "plan": "Direct", "sip": 8000,
        "benchmark_name": "SBI Small Cap Direct", "benchmark_scheme": "125497"
    },
    {
        "name": "Nippon India Growth Mid Cap Fund",
        "scheme": "100377", "plan": "Regular", "sip": 5000,
        "benchmark_name": "DSP Midcap Direct", "benchmark_scheme": "119071"
    },
    {
        "name": "UTI Nifty 200 Momentum 30 Index Fund",
        "scheme": "148704", "plan": "Regular", "sip": 5000,
        "benchmark_name": "MO Nifty 200 Momentum 30 Direct", "benchmark_scheme": "149800"
    },
    {
        "name": "ICICI Prudential Multi-Asset Fund",
        "scheme": "101144", "plan": "Regular", "sip": 5000,
        "benchmark_name": "SBI Multi Asset Allocation Direct", "benchmark_scheme": "119843"
    },
    {
        "name": "SBI Silver ETF Fund of Fund",
        "scheme": "152735", "plan": "Direct", "sip": 3000,
        "benchmark_name": "Nippon India Silver ETF FoF Direct", "benchmark_scheme": "149760"
    },
]

TOTAL_SIP = 51000

# ── Health Scoring Weights ───────────────────────────────────────────────────
# Short-term dips are forgiven — long-term performance carries more weight
WEIGHTS = {"1M": 0.10, "3M": 0.15, "6M": 0.20, "1Y": 0.30, "3Y": 0.25}

def compute_health(returns, benchmark_returns):
    """
    Returns a score (0–100), verdict emoji, label, and one-liner explanation.
    Logic:
      - Weighted score based on absolute returns across periods
      - Benchmark delta: adds/subtracts bonus points based on outperformance
      - Short-term (1D/1W) is intentionally excluded from scoring
    """
    score = 50.0  # neutral starting point
    notes = []
    periods_available = 0

    for period, weight in WEIGHTS.items():
        val = returns.get(period)
        if val is None:
            continue
        periods_available += 1

        # Add points for positive returns, scaled by magnitude (capped)
        contribution = weight * min(max(val, -30), 30)  # cap at ±30% per period
        score += contribution

        # Track notable periods
        if period in ("1Y", "3Y") and val > 10:
            notes.append(f"strong {period}")
        elif period in ("1Y", "3Y") and val < 0:
            notes.append(f"negative {period}")

    # Benchmark comparison bonus/penalty (based on 1Y and 3Y)
    benchmark_delta_note = None
    for period in ("1Y", "3Y"):
        fund_r = returns.get(period)
        bench_r = benchmark_returns.get(period) if benchmark_returns else None
        if fund_r is not None and bench_r is not None:
            delta = fund_r - bench_r
            if period == "1Y":
                score += delta * 0.15
            else:
                score += delta * 0.10
            if abs(delta) >= 2:
                direction = "outperforming" if delta > 0 else "lagging"
                benchmark_delta_note = f"{direction} peer by {abs(delta):.1f}% ({period})"

    # Clamp score to 0–100
    score = max(0, min(100, score))

    # Determine verdict
    if score >= 65:
        emoji = "🟢"
        label = "Healthy"
    elif score >= 40:
        emoji = "🟡"
        label = "Watch"
    else:
        emoji = "🔴"
        label = "Concern"

    # Build one-liner
    if notes and benchmark_delta_note:
        oneliner = f"{', '.join(notes[:2]).capitalize()}; {benchmark_delta_note}"
    elif notes:
        oneliner = f"{', '.join(notes[:2]).capitalize()}"
    elif benchmark_delta_note:
        oneliner = benchmark_delta_note.capitalize()
    elif periods_available == 0:
        oneliner = "Insufficient history"
    else:
        oneliner = "Performing in line with expectations"

    return round(score, 1), emoji, label, oneliner

# ── Fetch NAV Data ───────────────────────────────────────────────────────────
def fetch_fund_data(scheme_code):
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_nav_on_or_before(nav_list, target_date):
    for entry in nav_list:
        entry_date = datetime.strptime(entry["date"], "%d-%m-%Y").date()
        if entry_date <= target_date:
            return entry
    return None

def calculate_returns(nav_list, current_nav, current_date):
    results = {}
    periods = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095}
    for label, days in periods.items():
        past_date = current_date - timedelta(days=days)
        past_entry = get_nav_on_or_before(nav_list, past_date)
        if past_entry:
            past_nav = float(past_entry["nav"])
            change = ((current_nav - past_nav) / past_nav) * 100
            results[label] = round(change, 2)
        else:
            results[label] = None
    return results

def process_funds():
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).date()
    report_date = today.strftime("%d %b %Y")
    fund_results = []

    for fund in FUNDS:
        try:
            data = fetch_fund_data(fund["scheme"])
            nav_list = data["data"]
            meta = data["meta"]

            latest = nav_list[0]
            current_nav = float(latest["nav"])
            nav_date = latest["date"]

            prev_entry = nav_list[1] if len(nav_list) > 1 else None
            prev_nav = float(prev_entry["nav"]) if prev_entry else None
            day_change = round(((current_nav - prev_nav) / prev_nav) * 100, 2) if prev_nav else None

            current_date = datetime.strptime(nav_date, "%d-%m-%Y").date()
            returns = calculate_returns(nav_list, current_nav, current_date)

            # Fetch benchmark returns
            benchmark_returns = None
            try:
                bdata = fetch_fund_data(fund["benchmark_scheme"])
                bnav_list = bdata["data"]
                blatest_nav = float(bnav_list[0]["nav"])
                bcurrent_date = datetime.strptime(bnav_list[0]["date"], "%d-%m-%Y").date()
                benchmark_returns = calculate_returns(bnav_list, blatest_nav, bcurrent_date)
            except Exception:
                pass  # benchmark failure is non-fatal

            score, emoji, label, oneliner = compute_health(returns, benchmark_returns)

            fund_results.append({
                "name": fund["name"],
                "plan": fund["plan"],
                "sip": fund["sip"],
                "scheme": fund["scheme"],
                "fund_house": meta.get("fund_house", ""),
                "category": meta.get("scheme_category", ""),
                "nav": current_nav,
                "nav_date": nav_date,
                "day_change": day_change,
                "returns": returns,
                "benchmark_name": fund["benchmark_name"],
                "benchmark_returns": benchmark_returns,
                "health_score": score,
                "health_emoji": emoji,
                "health_label": label,
                "health_oneliner": oneliner,
                "status": "ok"
            })
        except Exception as e:
            fund_results.append({
                "name": fund["name"],
                "plan": fund["plan"],
                "sip": fund["sip"],
                "scheme": fund["scheme"],
                "status": "error",
                "error": str(e)
            })

    return fund_results, report_date

# ── HTML Helpers ─────────────────────────────────────────────────────────────
def color_for(value):
    if value is None:
        return "#888888"
    return "#16a34a" if value >= 0 else "#dc2626"

def arrow_for(value):
    if value is None:
        return ""
    return "▲" if value >= 0 else "▼"

def fmt_return(value):
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"

def score_bar(score):
    """Render a small inline progress bar for the health score."""
    pct = int(score)
    if score >= 65:
        bar_color = "#16a34a"
    elif score >= 40:
        bar_color = "#d97706"
    else:
        bar_color = "#dc2626"
    return f"""
    <div style="font-size:11px;color:#888;margin-top:3px;">Score: {score}/100</div>
    <div style="background:#e5e7eb;border-radius:4px;height:5px;margin-top:3px;width:90px;">
      <div style="background:{bar_color};width:{pct}%;height:5px;border-radius:4px;"></div>
    </div>"""

def benchmark_delta_cell(fund_returns, benchmark_returns):
    """Show fund 1Y vs benchmark 1Y delta."""
    if not benchmark_returns:
        return '<td style="text-align:center;padding:8px 10px;color:#aaa;font-size:12px;">—</td>'
    f1y = fund_returns.get("1Y")
    b1y = benchmark_returns.get("1Y")
    if f1y is None or b1y is None:
        return '<td style="text-align:center;padding:8px 10px;color:#aaa;font-size:12px;">—</td>'
    delta = f1y - b1y
    color = color_for(delta)
    arrow = arrow_for(delta)
    sign = "+" if delta >= 0 else ""
    return f'<td style="text-align:right;padding:8px 10px;color:{color};font-size:13px;">{arrow} {sign}{delta:.2f}%</td>'

# ── HTML Report ───────────────────────────────────────────────────────────────
def generate_html(fund_results, report_date):
    rows = ""
    for f in fund_results:
        if f["status"] == "error":
            rows += f"""
            <tr>
                <td colspan="12" style="color:#dc2626;padding:12px;">
                    ⚠️ {f['name']} — Failed to fetch data: {f.get('error','')}
                </td>
            </tr>"""
            continue

        r = f["returns"]
        br = f.get("benchmark_returns")
        dc = f["day_change"]
        dc_color = color_for(dc)
        dc_arrow = arrow_for(dc)

        plan_badge = (
            '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 7px;border-radius:4px;font-size:11px;">Direct</span>'
            if f["plan"] == "Direct" else
            '<span style="background:#fef9c3;color:#854d0e;padding:2px 7px;border-radius:4px;font-size:11px;">Regular</span>'
        )

        # Health verdict cell
        emoji = f["health_emoji"]
        label = f["health_label"]
        score = f["health_score"]
        oneliner = f["health_oneliner"]
        bench_name = f.get("benchmark_name", "")

        if label == "Healthy":
            verdict_bg = "#f0fdf4"
            verdict_border = "#86efac"
        elif label == "Watch":
            verdict_bg = "#fffbeb"
            verdict_border = "#fcd34d"
        else:
            verdict_bg = "#fff1f2"
            verdict_border = "#fca5a5"

        verdict_cell = f"""
        <td style="padding:10px;min-width:180px;">
          <div style="background:{verdict_bg};border:1px solid {verdict_border};border-radius:8px;padding:8px 10px;">
            <div style="font-size:13px;font-weight:700;">{emoji} {label}</div>
            {score_bar(score)}
            <div style="font-size:11px;color:#555;margin-top:5px;line-height:1.4;">{oneliner}</div>
            <div style="font-size:10px;color:#aaa;margin-top:4px;">vs {bench_name}</div>
          </div>
        </td>"""

        def ret_cell(key):
            v = r.get(key)
            c = color_for(v)
            return f'<td style="text-align:right;color:{c};padding:8px 10px;font-size:13px;">{fmt_return(v)}</td>'

        rows += f"""
        <tr style="border-bottom:1px solid #f0f0f0;">
            <td style="padding:12px 10px;min-width:200px;">
                <div style="font-weight:600;font-size:14px;">{f['name']}</div>
                <div style="font-size:11px;color:#888;margin-top:2px;">{f['category']} &nbsp;|&nbsp; {plan_badge}</div>
            </td>
            <td style="text-align:right;padding:8px 10px;">
              <div style="font-weight:600;">₹{f['nav']:.4f}</div>
              <div style="font-size:10px;color:#aaa;">{f['nav_date']}</div>
            </td>
            <td style="text-align:right;padding:8px 10px;color:{dc_color};font-weight:600;">{dc_arrow} {fmt_return(dc)}</td>
            {ret_cell('1W')}
            {ret_cell('1M')}
            {ret_cell('3M')}
            {ret_cell('6M')}
            {ret_cell('1Y')}
            {ret_cell('3Y')}
            {benchmark_delta_cell(r, br)}
            {verdict_cell}
            <td style="text-align:right;padding:8px 10px;font-weight:600;">₹{f['sip']:,}</td>
        </tr>"""

    # Portfolio-level health summary
    ok_funds = [f for f in fund_results if f["status"] == "ok"]
    healthy_count = sum(1 for f in ok_funds if f.get("health_label") == "Healthy")
    watch_count = sum(1 for f in ok_funds if f.get("health_label") == "Watch")
    concern_count = sum(1 for f in ok_funds if f.get("health_label") == "Concern")
    avg_score = round(sum(f["health_score"] for f in ok_funds) / len(ok_funds), 1) if ok_funds else 0

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mutual Fund Daily Report — {report_date}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8fafc; margin:0; padding:20px; color:#1a1a1a; }}
  .container {{ max-width:1200px; margin:0 auto; background:#fff; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.08); overflow:hidden; }}
  .header {{ background:linear-gradient(135deg,#1e3a5f,#2563eb); color:#fff; padding:28px 32px; }}
  .header h1 {{ margin:0 0 4px 0; font-size:22px; }}
  .header p {{ margin:0; opacity:0.8; font-size:14px; }}
  .summary {{ display:flex; gap:16px; padding:20px 32px; background:#f0f7ff; border-bottom:1px solid #e0eaff; flex-wrap:wrap; }}
  .summary-card {{ background:#fff; border-radius:8px; padding:12px 20px; flex:1; min-width:120px; box-shadow:0 1px 4px rgba(0,0,0,0.06); text-align:center; }}
  .summary-card .label {{ font-size:11px; color:#888; text-transform:uppercase; letter-spacing:0.5px; }}
  .summary-card .value {{ font-size:22px; font-weight:700; margin-top:4px; }}
  .note {{ font-size:11px; color:#aaa; padding:8px 32px; background:#fafafa; border-bottom:1px solid #f0f0f0; }}
  table {{ width:100%; border-collapse:collapse; }}
  th {{ background:#f8fafc; color:#666; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; padding:10px; text-align:right; border-bottom:2px solid #e5e7eb; white-space:nowrap; }}
  th:first-child {{ text-align:left; }}
  tr:hover {{ background:#fafafa; }}
  .footer {{ padding:16px 32px; font-size:12px; color:#aaa; text-align:center; border-top:1px solid #f0f0f0; }}
  @media(max-width:768px) {{ body {{ padding:8px; }} .summary {{ padding:12px; }} }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>📊 Mutual Fund Daily Report</h1>
    <p>As of {report_date} &nbsp;·&nbsp; 7 funds tracked &nbsp;·&nbsp; Total Monthly SIP: ₹{TOTAL_SIP:,}</p>
  </div>

  <div class="summary">
    <div class="summary-card">
      <div class="label">Monthly SIP</div>
      <div class="value" style="color:#2563eb;">₹{TOTAL_SIP:,}</div>
    </div>
    <div class="summary-card">
      <div class="label">Avg Health Score</div>
      <div class="value" style="color:{'#16a34a' if avg_score>=65 else '#d97706' if avg_score>=40 else '#dc2626'};">{avg_score}</div>
    </div>
    <div class="summary-card">
      <div class="label">🟢 Healthy</div>
      <div class="value" style="color:#16a34a;">{healthy_count}</div>
    </div>
    <div class="summary-card">
      <div class="label">🟡 Watch</div>
      <div class="value" style="color:#d97706;">{watch_count}</div>
    </div>
    <div class="summary-card">
      <div class="label">🔴 Concern</div>
      <div class="value" style="color:#dc2626;">{concern_count}</div>
    </div>
  </div>

  <div class="note">
    ℹ️ Health verdict is based on weighted returns (1M–3Y) + performance vs peer benchmark. Short-term dips are intentionally weighted low.
    1D change is informational only and does not affect the health score.
    Returns &lt;1Y are absolute; 3Y is absolute cumulative.
  </div>

  <div style="overflow-x:auto;">
  <table>
    <thead>
      <tr>
        <th style="text-align:left;padding:10px;">Fund</th>
        <th>NAV</th>
        <th>1D</th>
        <th>1W</th>
        <th>1M</th>
        <th>3M</th>
        <th>6M</th>
        <th>1Y</th>
        <th>3Y</th>
        <th>vs Peer (1Y)</th>
        <th style="text-align:left;">Health</th>
        <th>Monthly SIP</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
  </div>

  <div class="footer">
    Data sourced from <a href="https://mfapi.in" style="color:#2563eb;">mfapi.in</a> &nbsp;·&nbsp;
    Health score is data-driven (NAV-based) — not a financial rating or advice &nbsp;·&nbsp;
    Generated automatically at 9:30 PM IST
  </div>

</div>
</body>
</html>"""
    return html

# ── Email ────────────────────────────────────────────────────────────────────
def send_email(html_content, report_date):
    sender = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("RECIPIENT_EMAIL", sender)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Mutual Fund Report — {report_date}"
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    print(f"Email sent to {recipient}")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Fetching fund data...")
    fund_results, report_date = process_funds()

    print("Generating HTML report...")
    html = generate_html(fund_results, report_date)

    with open("index.html", "w") as f:
        f.write(html)
    print("index.html written.")

    try:
        send_email(html, report_date)
    except KeyError:
        print("Email env vars not set — skipping email (HTML still generated).")
    except Exception as e:
        print(f"Email failed: {e}")
