# QueueCloud – Cloud-Based Appointment & Queue Management Platform

## Tech Stack
- Python Flask
- MySQL / AWS RDS MySQL
- HTML/CSS
- Bootstrap 5
- AWS EC2
- Gunicorn

## 1. Requirements

- Python 3.11+
- MySQL 8+
- VS Code (optional)

## 2. Create the database

Open MySQL Workbench and run:

    database/schema.sql

This creates the `queuecloud` database and sample doctors. The script avoids duplicating the sample doctors when run again.

If you already have an older QueueCloud database, run `database/update_existing.sql` once before using the updated application.

## 3. Install Python packages

Windows:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

## 4. Configure the database

Default local configuration:

    mysql+pymysql://root:root@localhost/queuecloud

If your MySQL username/password are different, set `DATABASE_URL`.

PowerShell example:

    $env:DATABASE_URL="mysql+pymysql://root:YOUR_PASSWORD@localhost/queuecloud"

For AWS RDS:

    $env:DATABASE_URL="mysql+pymysql://queuecloud_user:PASSWORD@RDS_ENDPOINT:3306/queuecloud"

Also set a strong secret key:

    $env:SECRET_KEY="replace-with-a-long-random-secret"

## 5. Run locally

    python run.py

Open:

    http://127.0.0.1:5000

`python app.py` is also supported.

## 6. Create an admin account

1. Register a normal account.
2. Open MySQL Workbench.
3. Run:

    USE queuecloud;
    UPDATE users SET role='admin' WHERE email='your-email@example.com';

4. Log out and log in again.

## 7. Main functionality

### Patient
- Register and login
- Select an active doctor
- Select appointment date and time
- Server-side validation of doctor, date and working hours
- Automatic token generation per doctor/date
- Prevent duplicate active bookings for the same doctor/date/time
- View appointment status and queue position
- Cancel waiting appointments

### Admin / Receptionist
- View all appointments and doctors
- Add doctors with validated working hours
- Call the next eligible patient
- Serve an individual waiting appointment
- Complete the current serving appointment
- Prevent serving future appointments
- Only one appointment can remain in `Serving` state at a time

## 8. AWS deployment

Recommended architecture:

    Internet
       |
      EC2
       |
    Flask + Gunicorn
       |
    RDS MySQL

On RDS:
- Create the `queuecloud` database.
- Allow inbound MySQL port 3306 only from the EC2 security group.
- Do NOT open port 3306 to the whole internet.

On EC2:

    sudo dnf update -y
    sudo dnf install -y python3.11
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Set environment variables:

    export SECRET_KEY="replace-with-a-long-random-secret"
    export DATABASE_URL="mysql+pymysql://queuecloud_user:PASSWORD@RDS_ENDPOINT:3306/queuecloud"

Run:

    gunicorn -w 3 -b 0.0.0.0:5000 run:app

For a production deployment, place Nginx/ALB in front of Gunicorn and use HTTPS.

## Important

This is an academic project. Before production use, add CSRF protection, stronger authorization, HTTPS, production session-cookie settings, logging, monitoring and backups.
