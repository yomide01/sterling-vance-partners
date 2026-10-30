"""
Sterling & Vance Partners — Real Multi-Channel B2B Email Outreach Engine (Python 3.12)
Supports 3 $0 Free-Tier Email Transports (Zero Domain Cost Required):
  1. Gmail / Google Workspace SMTP (smtplib.SMTP_SSL — up to 500 real emails/day for $0)
  2. Brevo Transactional API (api.brevo.com — up to 300 real emails/day for $0, no custom domain required)
  3. Resend API (api.resend.com — 3,000 emails/month free tier)
"""

import os
import json
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from engine.ai_core import load_env_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_outreach_credentials() -> dict:
    env_path = os.path.join(BASE_DIR, ".env")
    cfg = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                cfg[k.strip()] = v.strip()
    return {
        "sender_name": cfg.get("OUTREACH_SENDER_NAME", "Sterling & Vance Partners"),
        "sender_email": cfg.get("OUTREACH_SENDER_EMAIL", ""),
        "smtp_password": cfg.get("GMAIL_APP_PASSWORD", ""),
        "brevo_api_key": cfg.get("BREVO_API_KEY", ""),
        "resend_api_key": cfg.get("RESEND_API_KEY", ""),
        "public_base_url": cfg.get("PUBLIC_BASE_URL", "http://localhost:4000").rstrip("/"),
    }


def save_outreach_credentials(updates: dict):
    env_path = os.path.join(BASE_DIR, ".env")
    existing = {}
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            for line in lines:
                s = line.strip()
                if s and not s.startswith("#") and "=" in s:
                    k, v = s.split("=", 1)
                    existing[k.strip()] = v.strip()

    existing.update({k: v for k, v in updates.items() if v is not None})

    out_lines = [
        "# Sterling & Vance Partners — Python 3.12 Autonomous Enterprise Configuration",
        f"GEMINI_API_KEY={existing.get('GEMINI_API_KEY', '')}",
        f"GEMINI_FREE_MODEL={existing.get('GEMINI_FREE_MODEL', 'gemini-3.8-flash')}",
        f"PORT={existing.get('PORT', '4000')}",
        f"PAYSTACK_NGN_URL={existing.get('PAYSTACK_NGN_URL', 'https://paystack.com/pay/sterling-vance-ngn')}",
        f"GLOBAL_USD_URL={existing.get('GLOBAL_USD_URL', 'https://sterlingvance.lemonsqueezy.com/buy/complete-package')}",
        f"PUBLIC_BASE_URL={existing.get('PUBLIC_BASE_URL', 'http://localhost:4000')}",
        f"OUTREACH_SENDER_NAME={existing.get('OUTREACH_SENDER_NAME', 'Sterling & Vance Partners')}",
        f"OUTREACH_SENDER_EMAIL={existing.get('OUTREACH_SENDER_EMAIL', '')}",
        f"GMAIL_APP_PASSWORD={existing.get('GMAIL_APP_PASSWORD', '')}",
        f"BREVO_API_KEY={existing.get('BREVO_API_KEY', '')}",
        f"RESEND_API_KEY={existing.get('RESEND_API_KEY', '')}",
    ]
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")


def build_executive_email_payload(prospect: dict, live_workspace_url: str) -> tuple[str, str, str]:
    bname = prospect["business_name"]
    loc = prospect["location"]
    cat = prospect["category"]

    subject = f"We built a live booking portal & unlocked 10 {loc.split(',')[0]} buyer leads for {bname}"

    plain_text = f"""Hi {bname} Team,

While reviewing top {cat} providers in {loc}, our engineering team at Sterling & Vance Partners noticed two immediate revenue gaps on your current digital footprint:
1. {prospect['pain_detected']}
2. Missing /llms.txt & Schema.org structured citations for ChatGPT, Perplexity, and Google local search.

Instead of sending a cold pitch, we went ahead and built your complete 4-in-1 Executive Growth Workspace upfront so you can test it free of charge right now:

-> Open Your Live Workspace: {live_workspace_url}

Inside your live link above (no login required):
- Tab 1: Your upgraded interactive production website with live price estimation, time-slot scheduling, and a 24/7 automated client desk.
- Tab 2: Your ready-to-copy /llms.txt and Schema.org JSON-LD patches.
- Tab 3: 10 verified commercial & local buyer leads in {loc} unlocked free (with 1-click CSV export).
- Tab 4: Your missed-call and abandoned-quote revenue recovery simulator.

You can test the live booking calculator and export your 10 free leads immediately. If you'd like us to bind this system to your domain and deliver 60+ fresh verified leads every week, simply click "Unlock Complete Package — $49" in the top workspace bar.

Best regards,
Client Engineering Desk
Sterling & Vance Partners (US • UK • EU)
---
To opt out of future workspace previews, reply with "unsubscribe"."""

    html_body = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #0f172a; max-width: 620px; line-height: 1.6; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
      <div style="font-size: 12px; font-weight: 700; color: #059669; text-transform: uppercase; letter-spacing: 0.05em;">
        Sterling &amp; Vance Partners • Action-First Executive Preview
      </div>
      <h2 style="color: #0f172a; margin: 10px 0 14px; font-size: 20px;">
        We built a live booking system &amp; unlocked 10 {loc.split(',')[0]} buyer leads for {bname}
      </h2>
      <p>Hi <strong>{bname}</strong> Team,</p>
      <p>
        While reviewing <strong>{cat}</strong> providers in <strong>{loc}</strong>, our engineering team noticed that your current online setup is leaking high-intent clients (<em>{prospect['pain_detected']}</em>).
      </p>
      <p>
        Instead of pitching you, we went ahead and built your complete <strong>4-in-1 Executive Growth Workspace</strong> upfront so you can test-drive it free of charge:
      </p>
      <div style="margin: 22px 0;">
        <a href="{live_workspace_url}" style="background: #10b981; color: #042f1e; font-weight: 800; padding: 13px 22px; border-radius: 8px; text-decoration: none; display: inline-block;">
          ⚡ Open Your Live 4-Tab Workspace &amp; 10 Free Leads →
        </a>
      </div>
      <ul style="background: #f8fafc; padding: 16px 20px 16px 34px; border-radius: 8px; border: 1px solid #e2e8f0; font-size: 14px;">
        <li><strong>Tab 1 (Interactive Production Website):</strong> Live price estimator, local time-slot picker, and 24/7 automated client desk built for {bname}.</li>
        <li><strong>Tab 2 (SEO &amp; AI-Search Fixes):</strong> Ready-to-copy <code>/llms.txt</code> and <code>Schema.org JSON-LD</code> code.</li>
        <li><strong>Tab 3 (10 Free Verified Leads):</strong> 10 active buyer leads in {loc} unlocked free with 1-click <code>.CSV</code> export.</li>
        <li><strong>Tab 4 (Customer Recovery Hub):</strong> Automated missed-call &amp; abandoned-quote recovery sequence.</li>
      </ul>
      <p style="font-size: 14px; color: #475569; margin-top: 16px;">
        Test your live site and export the 10 free buyer leads right now. If you want to keep it live on your custom domain and receive 60+ fresh verified leads every week, click <strong>"Unlock Complete Package — $49"</strong> inside the top bar of your workspace.
      </p>
      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
      <div style="font-size: 12px; color: #64748b;">
        <strong>Sterling &amp; Vance Partners</strong> • Turnkey B2B Growth Infrastructure (US • UK • EU)<br/>
        Don't want custom workspace previews? Reply "unsubscribe" to opt out immediately.
      </div>
    </div>
    """
    return subject, plain_text, html_body


def dispatch_real_outreach_email(to_email: str, prospect: dict) -> dict:
    """
    Dispatches a real HTML + plain-text email via:
      1. Gmail / SMTP_SSL (if OUTREACH_SENDER_EMAIL + GMAIL_APP_PASSWORD configured)
      2. Brevo API (if BREVO_API_KEY configured)
      3. Resend API (if RESEND_API_KEY configured)
    Returns exact delivery status and transport used.
    """
    creds = get_outreach_credentials()
    live_url = f"{creds['public_base_url']}{prospect['preview_url']}"
    subject, plain_text, html_body = build_executive_email_payload(prospect, live_url)

    # Check if recipient is a valid email address
    if "@" not in to_email or to_email.startswith("@"):
        return {
            "sent": False,
            "transport": "SOCIAL_HANDLE_QUEUED",
            "detail": f"Target contact '{to_email}' is a social/phone handle; payload queued in Outreach Vault.",
            "live_url": live_url,
        }

    # 1. Try Gmail / Standard SMTP_SSL (100% Free, 500 emails/day, works with any recipient)
    if creds["sender_email"] and creds["smtp_password"]:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{creds['sender_name']} <{creds['sender_email']}>"
            msg["To"] = to_email
            msg.attach(MIMEText(plain_text, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            clean_pass = creds["smtp_password"].replace(" ", "")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(creds["sender_email"], clean_pass)
                server.sendmail(creds["sender_email"], [to_email], msg.as_string())

            return {
                "sent": True,
                "transport": "GMAIL_SMTP_SSL",
                "detail": f"Real email delivered via Gmail SMTP to {to_email} with link {live_url}",
                "live_url": live_url,
            }
        except Exception as e:
            smtp_err = str(e)
        else:
            smtp_err = ""
    else:
        smtp_err = ""

    # 2. Try Brevo Free Transactional API (300 emails/day free, no custom domain required)
    if creds["brevo_api_key"] and creds["sender_email"]:
        try:
            payload = {
                "sender": {"name": creds["sender_name"], "email": creds["sender_email"]},
                "to": [{"email": to_email, "name": prospect["business_name"]}],
                "subject": subject,
                "htmlContent": html_body,
                "textContent": plain_text,
            }
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "api-key": creds["brevo_api_key"],
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {
                    "sent": True,
                    "transport": "BREVO_API",
                    "detail": f"Real email delivered via Brevo API ({resp.status}) to {to_email}",
                    "live_url": live_url,
                }
        except Exception as e:
            pass

    # 3. Try Resend API (3,000 emails/mo free tier)
    if creds["resend_api_key"]:
        try:
            from_addr = creds["sender_email"] if (creds["sender_email"] and not creds["sender_email"].endswith("@gmail.com")) else "Sterling & Vance <onboarding@resend.dev>"
            payload = {
                "from": from_addr,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": plain_text,
            }
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {creds['resend_api_key']}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {
                    "sent": True,
                    "transport": "RESEND_API",
                    "detail": f"Real email delivered via Resend API ({resp.status}) to {to_email}",
                    "live_url": live_url,
                }
        except Exception as e:
            pass

    return {
        "sent": False,
        "transport": "READY_AWAITING_SMTP_OR_API_KEY",
        "detail": (
            f"Email payload compiled for {to_email} ({live_url}). "
            + (f"SMTP Notice: {smtp_err}. " if smtp_err else "")
            + "Add your free Gmail App Password or Brevo/Resend key in the Vault Outreach Panel to transmit live."
        ),
        "live_url": live_url,
    }
