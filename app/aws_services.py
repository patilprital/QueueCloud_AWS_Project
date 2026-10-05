"""
aws_services.py
---------------
Centralised AWS helpers for QueueCloud.

Services used:
  - AWS SES  : transactional email (appointment booked / cancelled / served)
  - AWS S3   : static-asset hosting (CSS, JS, images)

Both services fall under the AWS Free Tier:
  - SES  : 62 000 outbound messages / month when sent from an EC2 instance
           (or 200 / day in the SES sandbox for development)
  - S3   : 5 GB storage, 20 000 GET, 2 000 PUT requests / month for 12 months

Environment variables required (add to .env / EC2 env):
  AWS_REGION              e.g. us-east-1
  AWS_ACCESS_KEY_ID       IAM user key (needs ses:SendEmail + s3:PutObject)
  AWS_SECRET_ACCESS_KEY   IAM user secret
  SES_SENDER_EMAIL        Verified sender address in SES
  S3_BUCKET_NAME          S3 bucket name for static assets
  S3_BUCKET_URL           Public base URL of the bucket
"""

import os
import logging
import re
import mimetypes
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# SHARED SESSION
# ─────────────────────────────────────────────────────────────

def _session():
    """Return a boto3 session using env-var credentials."""
    return boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


# ═════════════════════════════════════════════════════════════
# SES – EMAIL NOTIFICATIONS
# ═════════════════════════════════════════════════════════════

SENDER = os.getenv("SES_SENDER_EMAIL", "noreply@queuecloud.example.com")


def _ses_client():
    return _session().client("ses")


def send_email(to_address, subject, html_body, text_body=""):
    """
    Send a single transactional email via AWS SES.

    Returns True on success, False on failure (logs the error).
    Silently skips if AWS credentials are not configured.
    """
    if not all([os.getenv("AWS_ACCESS_KEY_ID"), os.getenv("SES_SENDER_EMAIL")]):
        logger.warning("SES not configured – skipping email to %s", to_address)
        return False

    try:
        client = _ses_client()
        client.send_email(
            Source=SENDER,
            Destination={"ToAddresses": [to_address]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                    "Text": {"Data": text_body or _strip_html(html_body), "Charset": "UTF-8"},
                },
            },
        )
        logger.info("SES email sent to %s – subject: %s", to_address, subject)
        return True

    except (BotoCoreError, ClientError) as exc:
        logger.error("SES send_email failed for %s: %s", to_address, exc)
        return False


# ─────────────────────────────────────────────────────────────
# HTML email wrapper template
# ─────────────────────────────────────────────────────────────

_EMAIL_WRAPPER = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body{{font-family:Arial,sans-serif;background:#f4f6f9;margin:0;padding:0}}
    .container{{max-width:560px;margin:32px auto;background:#fff;border-radius:10px;
                overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08)}}
    .header{{background:linear-gradient(135deg,#1a73e8,#0d47a1);padding:28px 32px;color:#fff}}
    .header h1{{margin:0;font-size:22px;letter-spacing:.5px}}
    .header p{{margin:4px 0 0;font-size:13px;opacity:.85}}
    .body{{padding:28px 32px;color:#333;line-height:1.65}}
    .token-box{{background:#e8f0fe;border-left:4px solid #1a73e8;border-radius:6px;
                padding:16px 20px;margin:20px 0}}
    .token-num{{font-size:36px;font-weight:700;color:#1a73e8;letter-spacing:2px}}
    .status-badge{{display:inline-block;padding:4px 12px;border-radius:20px;
                   font-size:12px;font-weight:600;text-transform:uppercase}}
    .badge-success{{background:#e6f4ea;color:#1e8e3e}}
    .badge-warning{{background:#fce8b2;color:#f29900}}
    .badge-danger{{background:#fce8e8;color:#d93025}}
    .info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}}
    .info-cell{{background:#f8f9fa;border-radius:8px;padding:12px 16px}}
    .label{{font-size:11px;color:#666;text-transform:uppercase;
            letter-spacing:.5px;margin-bottom:4px}}
    .value{{font-size:15px;font-weight:600;color:#1a1a2e}}
    .footer{{background:#f8f9fa;padding:16px 32px;font-size:12px;
             color:#888;text-align:center;border-top:1px solid #eee}}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>&#127973; QueueCloud</h1>
      <p>Appointment &amp; Queue Management</p>
    </div>
    <div class="body">{content}</div>
    <div class="footer">
      This is an automated message from QueueCloud. Please do not reply.<br>
      &copy; 2024 QueueCloud. All rights reserved.
    </div>
  </div>
</body>
</html>"""


def send_booking_confirmation(patient_email, patient_name,
                               doctor_name, specialization,
                               appointment_date, token):
    """Send appointment booking confirmation email to patient."""
    content = """
      <p>Dear <strong>{patient_name}</strong>,</p>
      <p>Your appointment has been booked successfully!</p>
      <div class="token-box">
        <div class="label">Your Queue Token</div>
        <div class="token-num">#{token}</div>
      </div>
      <div class="info-grid">
        <div class="info-cell"><div class="label">Doctor</div>
          <div class="value">{doctor_name}</div></div>
        <div class="info-cell"><div class="label">Specialization</div>
          <div class="value">{specialization}</div></div>
        <div class="info-cell"><div class="label">Date</div>
          <div class="value">{appointment_date}</div></div>
        <div class="info-cell"><div class="label">Status</div>
          <div class="value"><span class="status-badge badge-success">&#10003; Confirmed</span></div></div>
      </div>
      <p style="font-size:14px;color:#555;">
        Please arrive a few minutes early and keep your token number handy.
        You can check your live queue position on the QueueCloud patient dashboard.
      </p>
    """.format(patient_name=patient_name, token=token, doctor_name=doctor_name,
               specialization=specialization, appointment_date=appointment_date)

    html = _EMAIL_WRAPPER.format(content=content)
    text = (
        "Dear {pn},\n\nYour appointment with {dn} ({sp}) on {dt} "
        "has been confirmed. Your queue token is #{tk}.\n\n"
        "Please arrive on time. - QueueCloud"
    ).format(pn=patient_name, dn=doctor_name, sp=specialization,
             dt=appointment_date, tk=token)

    return send_email(
        to_address=patient_email,
        subject="Appointment Confirmed - Token #{} | QueueCloud".format(token),
        html_body=html,
        text_body=text,
    )


def send_cancellation_email(patient_email, patient_name,
                             doctor_name, appointment_date, token):
    """Send appointment cancellation confirmation email to patient."""
    content = """
      <p>Dear <strong>{patient_name}</strong>,</p>
      <p>Your appointment has been <strong>cancelled</strong> as requested.</p>
      <div class="token-box" style="background:#fce8e8;border-left-color:#d93025;">
        <div class="label" style="color:#d93025;">Cancelled Token</div>
        <div class="token-num" style="color:#d93025;">#{token}</div>
      </div>
      <div class="info-grid">
        <div class="info-cell"><div class="label">Doctor</div>
          <div class="value">{doctor_name}</div></div>
        <div class="info-cell"><div class="label">Date</div>
          <div class="value">{appointment_date}</div></div>
        <div class="info-cell"><div class="label">Status</div>
          <div class="value"><span class="status-badge badge-danger">&#10007; Cancelled</span></div></div>
      </div>
      <p style="font-size:14px;color:#555;">
        If you did not request this cancellation or need to rebook,
        please visit the QueueCloud patient dashboard.
      </p>
    """.format(patient_name=patient_name, token=token,
               doctor_name=doctor_name, appointment_date=appointment_date)

    html = _EMAIL_WRAPPER.format(content=content)
    text = (
        "Dear {pn},\n\nYour appointment with {dn} on {dt} (Token #{tk}) "
        "has been cancelled.\n\nVisit QueueCloud to rebook. - QueueCloud"
    ).format(pn=patient_name, dn=doctor_name, dt=appointment_date, tk=token)

    return send_email(
        to_address=patient_email,
        subject="Appointment Cancelled - Token #{} | QueueCloud".format(token),
        html_body=html,
        text_body=text,
    )


def send_now_serving_email(patient_email, patient_name, doctor_name, token):
    """Notify a patient that they are now being called to be served."""
    content = """
      <p>Dear <strong>{patient_name}</strong>,</p>
      <p><strong style="color:#1a73e8;font-size:18px;">
        &#128276; It's your turn! You are now being called.
      </strong></p>
      <div class="token-box">
        <div class="label">Now Serving</div>
        <div class="token-num">#{token}</div>
      </div>
      <div class="info-grid">
        <div class="info-cell"><div class="label">Doctor</div>
          <div class="value">{doctor_name}</div></div>
        <div class="info-cell"><div class="label">Status</div>
          <div class="value"><span class="status-badge badge-warning">&#8987; Serving Now</span></div></div>
      </div>
      <p style="font-size:14px;color:#555;">
        Please proceed to the doctor's room immediately.
        If you are not present, your token may be skipped.
      </p>
    """.format(patient_name=patient_name, token=token, doctor_name=doctor_name)

    html = _EMAIL_WRAPPER.format(content=content)
    text = (
        "Dear {pn},\n\nToken #{tk} - you are now being called by {dn}. "
        "Please proceed to the doctor's room immediately.\n\n- QueueCloud"
    ).format(pn=patient_name, tk=token, dn=doctor_name)

    return send_email(
        to_address=patient_email,
        subject="Your Turn! Token #{} is Being Called | QueueCloud".format(token),
        html_body=html,
        text_body=text,
    )


# ═════════════════════════════════════════════════════════════
# S3 – STATIC ASSET HOSTING
# ═════════════════════════════════════════════════════════════

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "")
S3_BASE_URL = os.getenv("S3_BUCKET_URL", "").rstrip("/")


def _s3_client():
    return _session().client("s3")


def upload_static_file(local_path, s3_key, content_type="application/octet-stream"):
    """
    Upload a local static file to the configured S3 bucket.

    Returns the public URL string on success, or None on failure.
    """
    if not S3_BUCKET:
        logger.warning("S3_BUCKET_NAME not set – skipping upload of %s", local_path)
        return None

    try:
        client = _s3_client()
        client.upload_file(
            Filename=local_path,
            Bucket=S3_BUCKET,
            Key=s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "max-age=86400",
            },
        )
        url = (
            "{}/{}".format(S3_BASE_URL, s3_key)
            if S3_BASE_URL
            else "https://{}.s3.amazonaws.com/{}".format(S3_BUCKET, s3_key)
        )
        logger.info("Uploaded %s to %s", local_path, url)
        return url

    except (BotoCoreError, ClientError, FileNotFoundError) as exc:
        logger.error("S3 upload failed for %s: %s", local_path, exc)
        return None


def get_static_url(s3_key):
    """
    Return the public S3 URL for a static asset key.
    Falls back gracefully to a local path if S3 is not configured.

    Register as a Jinja2 global in create_app() so templates can call:
        {{ s3_url('static/css/style.css') }}
    """
    if S3_BASE_URL and S3_BUCKET:
        return "{}/{}".format(S3_BASE_URL, s3_key)
    return "/{}".format(s3_key)


def upload_all_static_assets(static_folder):
    """
    Walk the Flask static folder and upload every file to S3.
    Returns a dict mapping s3_key -> public URL.

    Call once from a management CLI script or CI/CD pipeline.
    """
    results = {}
    root = Path(static_folder)

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root.parent)
        s3_key = relative.as_posix()
        mime, _ = mimetypes.guess_type(str(file_path))
        content_type = mime or "application/octet-stream"
        url = upload_static_file(str(file_path), s3_key, content_type)
        if url:
            results[s3_key] = url

    return results


# ─────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────

def _strip_html(html):
    """Very simple HTML tag stripper for plain-text email fallback."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
