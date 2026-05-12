"""Email sending service using Resend API."""
import os
import json
from typing import List, Dict, Optional
import requests
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from .db import get_verified_subscribers, log_send

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("NEWSLETTER_FROM_EMAIL", "newsletter@yourdomain.com")
BASE_URL = os.environ.get("BLOG_BASE_URL", "https://hotspot.edgesoft.org")

# --- Subscriber source ---
# Subscribers are stored in the Cloudflare Worker's D1 database.
# GitHub Actions fetches them via the Worker's API endpoint.
WORKER_SUBSCRIBERS_API = os.environ.get("WORKER_SUBSCRIBERS_API", "")
WORKER_API_KEY = os.environ.get("WORKER_API_KEY", "")

def _fetch_subscribers_from_worker() -> List[Dict]:
    """Fetch verified subscribers from the Cloudflare Worker API."""
    if not WORKER_SUBSCRIBERS_API or not WORKER_API_KEY:
        return []  # Fall back to local DB if not configured
    try:
        resp = requests.get(
            WORKER_SUBSCRIBERS_API,
            headers={"Authorization": f"Bearer {WORKER_API_KEY}"},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("subscribers", [])
        else:
            print(f"[Mailer] Worker API error ({resp.status_code}): {resp.text}")
            return []
    except Exception as e:
        print(f"[Mailer] Failed to fetch subscribers from Worker: {e}")
        return []

# Setup Jinja2 for email templates
template_dir = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)))


def generate_newsletter_html(items: list, date_str: str) -> str:
    """Generate HTML newsletter from items list."""
    items_html = ""
    for item in items[:15]:
        items_html += f"""
    <div style="background:#1a1a25;border-radius:8px;padding:16px;margin-bottom:12px;border:1px solid #252535;">
        <h3 style="margin:0 0 8px;font-size:16px;"><a href="{item["url"]}" style="color:#6366f1;text-decoration:none;">{item["title"]}</a></h3>
        <p style="margin:0 0 4px;color:#8b8ba7;font-size:13px;">{item["source"]} · <strong>{item["category"]}</strong></p>
        <p style="margin:0;color:#e2e2f0;font-size:14px;line-height:1.5;">{item["summary"]}</p>
        <p style="margin:8px 0 0;color:#10b981;font-size:13px;font-style:italic;">{item.get("insight", "")}</p>
    </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Tech Hotspot Daily - {date_str}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e2f0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; }}
  </style>
</head>
<body>
  <div class="container">
    <h1 style="color:#6366f1;font-size:24px;">📰 Tech Hotspot Daily</h1>
    <p style="color:#8b8ba7;font-size:14px;margin-bottom:24px;">{date_str}</p>
    {items_html}
    <div style="margin-top:24px;padding-top:16px;border-top:1px solid #252535;color:#8b8ba7;font-size:12px;">
      <p>You received this because you subscribed to Tech Hotspot Daily.</p>
      <p><a href="{os.environ.get("BLOG_BASE_URL", "https://hotspot.edgesoft.org")}/unsubscribe.html" style="color:#6366f1;">Unsubscribe</a></p>
    </div>
  </div>
</body>
</html>"""


def send_verification_email(email: str, token: str) -> bool:
    """Send verification email to a new subscriber."""
    if not RESEND_API_KEY:
        print("[Mailer] RESEND_API_KEY not configured")
        return False

    verify_url = f"{BASE_URL}/verify.html?token={token}"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Your Subscription</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e2e2f0; padding: 40px 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #12121a; border: 1px solid #252535; border-radius: 12px; padding: 40px; }}
    h1 {{ color: #6366f1; font-size: 24px; margin-bottom: 20px; }}
    .button {{ display: inline-block; background: #6366f1; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #252535; color: #8b8ba7; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📧 Verify Your Subscription</h1>
    <p>Thank you for subscribing to <strong>Tech Hotspot Daily</strong>!</p>
    <p>Click the button below to verify your email and start receiving daily tech news.</p>
    <a href="{verify_url}" class="button">Verify Email</a>
    <p style="font-size: 13px; color: #8b8ba7;">Or copy this link: {verify_url}</p>
    <div class="footer">
      <p>If you didn't request this, you can safely ignore this email.</p>
      <p>Tech Hotspot Daily — Curated for IT professionals</p>
    </div>
  </div>
</body>
</html>"""

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"Tech Hotspot Daily <{FROM_EMAIL}>",
                "to": [email],
                "subject": "Verify your subscription to Tech Hotspot Daily",
                "html": html_content,
            },
        )

        if resp.status_code != 200:
            print(f"[Mailer] Resend API error ({resp.status_code}): {resp.text}")
            return False

        print(f"[Mailer] Verification email sent to {email}")
        return True

    except Exception as e:
        print(f"[Mailer] Failed to send verification email: {e}")
        return False


def send_newsletter(subject: str, html_content: str, test_mode: bool = False) -> Dict:
    """Send newsletter to all verified subscribers."""
    if not RESEND_API_KEY:
        print("[Mailer] RESEND_API_KEY not configured")
        return {"sent": 0, "failed": 0, "errors": []}

    # Get subscribers — prefer Worker API, fall back to local SQLite
    subscribers = _fetch_subscribers_from_worker()
    if not subscribers:
        subscribers = get_verified_subscribers()
    if not subscribers:
        print("[Mailer] No verified subscribers found. Skipping newsletter.")
        return {"sent": 0, "failed": 0, "errors": []}

    if test_mode:
        subscribers = subscribers[:1]  # Only send to first subscriber in test mode
        print(f"[Mailer] Test mode: sending to 1 subscriber ({subscribers[0]['email']})")
    else:
        print(f"[Mailer] Sending newsletter to {len(subscribers)} subscribers")

    results = {"sent": 0, "failed": 0, "errors": []}

    for sub in subscribers:
        email = sub["email"]
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"Tech Hotspot Daily <{FROM_EMAIL}>",
                    "to": [email],
                    "subject": subject,
                    "html": html_content,
                },
            )

            if resp.status_code == 200:
                results["sent"] += 1
                log_send(email, "newsletter", subject, "sent")
                print(f"[Mailer] Sent to {email}")
            else:
                results["failed"] += 1
                error_msg = f"Resend API error ({resp.status_code}): {resp.text}"
                results["errors"].append({"email": email, "error": error_msg})
                log_send(email, "newsletter", subject, "failed", error_msg)
                print(f"[Mailer] Failed to send to {email}: {error_msg}")

        except Exception as e:
            results["failed"] += 1
            error_msg = str(e)
            results["errors"].append({"email": email, "error": error_msg})
            log_send(email, "newsletter", subject, "failed", error_msg)
            print(f"[Mailer] Exception sending to {email}: {error_msg}")

    print(f"[Mailer] Newsletter complete: {results['sent']} sent, {results['failed']} failed")
    return results
