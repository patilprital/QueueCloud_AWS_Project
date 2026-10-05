from datetime import date, datetime
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import db
from app.models import Doctor, Appointment, User
import app.aws_services as aws


patient_bp = Blueprint("patient", __name__)


def logged_patient():
    return session.get("user_id") and session.get("role") == "patient"


def queue_position(appointment):
    if appointment.status != "Waiting":
        return None

    ahead = Appointment.query.filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.appointment_date == appointment.appointment_date,
        Appointment.status == "Waiting",
        Appointment.token < appointment.token,
    ).count()

    return ahead + 1


def now_serving(doctor_id, appointment_date):
    current = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == "Serving",
    ).order_by(
        Appointment.token.desc(),
        Appointment.id.desc(),
    ).first()

    return current


@patient_bp.route("/dashboard")
def dashboard():

    if not logged_patient():
        return redirect(url_for("auth.login"))

    appointments = Appointment.query.filter_by(
        patient_id=session["user_id"]
    ).order_by(
        Appointment.appointment_date.desc(),
        Appointment.id.desc()
    ).all()

    queue_positions = {}
    serving_tokens = {}

    for a in appointments:

        queue_positions[a.id] = queue_position(a)

        current = now_serving(
            a.doctor_id,
            a.appointment_date
        )

        serving_tokens[a.id] = current.token if current else None

    return render_template(
        "patient/dashboard.html",
        appointments=appointments,
        queue_positions=queue_positions,
        serving_tokens=serving_tokens,
        today=date.today(),
    )


# ============================================================
# BOOK APPOINTMENT
# ============================================================

@patient_bp.route("/book", methods=["GET", "POST"])
def book():

    if not logged_patient():
        return redirect(url_for("auth.login"))

    doctors = Doctor.query.filter_by(
        active=True
    ).order_by(
        Doctor.name
    ).all()

    if request.method == "POST":

        try:
            doctor_id = int(
                request.form.get("doctor_id", "")
            )
        except (TypeError, ValueError):
            doctor_id = 0

        appointment_date_raw = request.form.get(
            "appointment_date",
            ""
        )

        try:
            appointment_date = date.fromisoformat(
                appointment_date_raw
            )
        except (TypeError, ValueError):
            appointment_date = None

        doctor = db.session.get(
            Doctor,
            doctor_id
        )

        # ----------------------------------------------------
        # VALIDATE DOCTOR
        # ----------------------------------------------------

        if not doctor or not doctor.active:

            flash(
                "Please select a valid active doctor.",
                "danger"
            )

            return redirect(
                url_for("patient.book")
            )

        # ----------------------------------------------------
        # VALIDATE DATE
        # ----------------------------------------------------

        if not appointment_date:

            flash(
                "Please select a valid appointment date.",
                "danger"
            )

            return redirect(
                url_for("patient.book")
            )

        if appointment_date < date.today():

            flash(
                "Appointment date cannot be in the past.",
                "danger"
            )

            return redirect(
                url_for("patient.book")
            )

        # ----------------------------------------------------
        # CHECK DUPLICATE ACTIVE APPOINTMENT
        # ----------------------------------------------------

        duplicate = Appointment.query.filter(
            Appointment.patient_id == session["user_id"],
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.in_(["Waiting", "Serving"]),
        ).first()

        if duplicate:

            flash(
                "You already have an active appointment with this doctor on the selected date.",
                "danger"
            )

            return redirect(
                url_for("patient.book")
            )

        # ----------------------------------------------------
        # GENERATE TOKEN
        # Token is separate for each doctor and date
        # ----------------------------------------------------

        for _ in range(5):

            latest = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == appointment_date,
            ).order_by(
                Appointment.token.desc()
            ).first()

            token = (
                latest.token + 1
                if latest
                else 1
            )

            appointment = Appointment(
                patient_id=session["user_id"],
                doctor_id=doctor_id,
                appointment_date=appointment_date,

                # Time is NOT selected by patient.
                # This value is only stored because
                # appointment_time is required by the database.
                appointment_time="00:00",

                token=token,
                status="Waiting",
            )

            db.session.add(appointment)

            try:

                db.session.commit()

                flash(
                    f"Appointment booked successfully. Your token is {token}.",
                    "success"
                )

                # ── AWS SES: Send booking confirmation email ──
                patient = db.session.get(User, session["user_id"])
                if patient:
                    aws.send_booking_confirmation(
                        patient_email=patient.email,
                        patient_name=patient.name,
                        doctor_name=doctor.name,
                        specialization=doctor.specialization,
                        appointment_date=str(appointment_date),
                        token=token,
                    )

                return redirect(
                    url_for("patient.dashboard")
                )

            except IntegrityError:

                db.session.rollback()

        flash(
            "Could not generate a unique token. Please try again.",
            "danger"
        )

        return redirect(
            url_for("patient.book")
        )

    return render_template(
        "patient/book.html",
        doctors=doctors,
        today=date.today().isoformat()
    )


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@patient_bp.route(
    "/cancel/<int:appointment_id>",
    methods=["POST"]
)
def cancel(appointment_id):

    if not logged_patient():
        return redirect(url_for("auth.login"))

    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=session["user_id"]
    ).first_or_404()

    if appointment.status == "Waiting":

        # Snapshot details before commit for the email
        doctor_name = appointment.doctor.name
        appt_date = str(appointment.appointment_date)
        token = appointment.token
        patient_name = session.get("name", "")
        patient_email_obj = db.session.get(User, session["user_id"])

        appointment.status = "Cancelled"

        db.session.commit()

        # ── AWS SES: Send cancellation email ──
        if patient_email_obj:
            aws.send_cancellation_email(
                patient_email=patient_email_obj.email,
                patient_name=patient_name,
                doctor_name=doctor_name,
                appointment_date=appt_date,
                token=token,
            )

        flash(
            "Appointment cancelled.",
            "success"
        )

    else:

        flash(
            "Only waiting appointments can be cancelled.",
            "warning"
        )

    return redirect(
        url_for("patient.dashboard")
    )