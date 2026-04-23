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
BASE_URL = os.environ.get("BLOG_BASE_URL", "https://yourdomain.github.io/social-hotspot-daily")

# Setup Jinja2 for email templates
template_dir = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)))


def send_verification_email(email: str, token: str) -> bool:
    """Send verification email to a new subscriber."""
    if not RESEND_API_KEY:
        print("[Mailer] RESEND_API_KEY not configured")
        return False

    verify_url = f"{BASE_URL}/verify.html?token={token}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Subscription</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                   background: #0a0a0f; color: #e2e2f0; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #12121a;
                         border: 1px solid #252535; border-radius: 12px; padding: 40px; }}
            h1 {{ color: #6366f1; font-size: 24px; margin-bottom: 20px; }}
            .button {{ display: inline-block; background: #6366f1; color: white;
                      padding: 14px 32px; border-radius: 8px; text-decoration: none;
                      font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #252535;
                      color: #8b8ba7; font-size: 12px; }}
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
    </html>
    """

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
            timeout=30,
        )
        resp.raise_for_status()
        print(f"[Mailer] Verification email sent to {email}")
        return True
    except Exception as e:
        print(f"[Mailer] Failed to send verification to {email}: {e}")
        return False


def generate_newsletter_html(items: List[Dict], date_str: str) -> str:
    """Generate newsletter HTML from news items."""
    template = env.get_template("email.html")
    return template.render(
        date=date_str,
        items=items,
        base_url=BASE_URL,
    )


def send_newsletter(subject: str, html_content: str, test_mode: bool = False) -> Dict:
    """Send newsletter to all verified subscribers."""
    if not RESEND_API_KEY:
        print("[Mailer] RESEND_API_KEY not configured")
        return {"sent": 0, "failed": 0, "errors": []}

    subscribers = get_verified_subscribers()

    if test_mode:
        # Only send to first subscriber for testing
        subscribers = subscribers[:1]
        print(f"[Mailer] TEST MODE: Sending to {subscribers[0]['email'] if subscribers else 'no one'}")

    sent = 0
    failed = 0
    errors = []

    for sub in subscribers:
        email = sub["email"]

        # Add unsubscribe link
        unsubscribe_url = f"{BASE_URL}/unsubscribe.html?email={email}"
        personalized_html = html_content.replace(
            "{{UNSUBSCRIBE_URL}}",
            unsubscribe_url
        )

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
                    "html": personalized_html,
                },
                timeout=30,
            )
            resp.raise_for_status()
            log_send(email, "sent")
            sent += 1
            print(f"[Mailer] Sent to {email}")

        except Exception as e:
            error_msg = str(e)
            log_send(email, "failed", error_msg)
            errors.append({"email": email, "error": error_msg})
            failed += 1
            print(f"[Mailer] Failed to send to {email}: {error_msg}")

    return {
        "sent": sent,
        "failed": failed,
        "total": len(subscribers),
        "errors": errors,
    }