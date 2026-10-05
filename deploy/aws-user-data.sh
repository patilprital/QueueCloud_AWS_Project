#!/bin/bash
# QueueCloud EC2 setup helper for Amazon Linux 2023.
# Upload/copy the project to /opt/queuecloud separately.

set -e

dnf update -y
dnf install -y python3.11

mkdir -p /opt/queuecloud
cd /opt/queuecloud

python3.11 -m venv venv
source venv/bin/activate

# After uploading the project files:
# pip install -r requirements.txt
# export SECRET_KEY="replace-with-a-long-random-secret"
# export DATABASE_URL="mysql+pymysql://queuecloud_user:PASSWORD@RDS_ENDPOINT:3306/queuecloud"
# gunicorn -w 3 -b 0.0.0.0:5000 run:app
