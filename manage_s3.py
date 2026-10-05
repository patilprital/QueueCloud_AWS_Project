"""
manage_s3.py
------------
One-shot CLI script to upload QueueCloud's static assets to AWS S3.

Usage:
    python manage_s3.py

Required environment variables (set before running):
    AWS_REGION            e.g. us-east-1
    AWS_ACCESS_KEY_ID     IAM user key
    AWS_SECRET_ACCESS_KEY IAM user secret
    S3_BUCKET_NAME        Target S3 bucket name
    S3_BUCKET_URL         Public base URL (optional, auto-generated if omitted)

What it does:
    1. Walks the app/static/ directory
    2. Uploads each file to S3 with the correct Content-Type
    3. Sets Cache-Control: max-age=86400 (1 day)
    4. Prints a result table
"""

import os
import sys
from pathlib import Path

# ── Make sure project root is on sys.path ──────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── Load .env file automatically ───────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def main():
    from app.aws_services import upload_all_static_assets, S3_BUCKET

    static_folder = ROOT / "app" / "static"

    if not static_folder.exists():
        print("[ERROR] Static folder not found:", static_folder)
        sys.exit(1)

    if not S3_BUCKET:
        print("[ERROR] S3_BUCKET_NAME environment variable is not set.")
        print("        Set it before running this script.")
        sys.exit(1)

    print("=" * 60)
    print(" QueueCloud – S3 Static Asset Uploader")
    print("=" * 60)
    print(f" Bucket : {S3_BUCKET}")
    print(f" Source : {static_folder}")
    print("=" * 60)

    results = upload_all_static_assets(str(static_folder))

    if not results:
        print("[WARN] No files were uploaded. Check credentials and bucket name.")
        sys.exit(1)

    print(f"\n{'FILE':<45} {'STATUS'}")
    print("-" * 60)
    for key, url in sorted(results.items()):
        short_key = key if len(key) <= 43 else "..." + key[-40:]
        print(f"  {short_key:<43} OK")

    print("-" * 60)
    print(f"\n  {len(results)} file(s) uploaded successfully.\n")
    print("  TIP: Set S3_BUCKET_URL in your .env to enable S3 serving.")
    print("       Templates use {{ s3_url('static/css/style.css') }}")
    print()


if __name__ == "__main__":
    main()
