from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.extensions import db
from app.models import Doctor, Appointment, User
import app.aws_services as aws


admin_bp = Blueprint("admin", __name__)


def is_admin():
    return session.get("user_id") and session.get("role") == "admin"


def parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return None


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_bp.route("/dashboard")
def dashboard():

    if not is_admin():
        return redirect(url_for("auth.login"))

    today = date.today()

    appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc(),
        Appointment.appointment_time.asc(),
        Appointment.token.asc(),
        Appointment.id.asc(),
    ).all()

    doctors = Doctor.query.order_by(
        Doctor.active.desc(),
        Doctor.name
    ).all()

    # --------------------------------------------------------
    # DOCTOR-WISE QUEUE
    # --------------------------------------------------------

    doctor_queues = []

    for doctor in doctors:

        current = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "Serving",
            Appointment.appointment_date == today,
        ).order_by(
            Appointment.id.desc()
        ).first()

        waiting = Appointment.query.filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "Waiting",
            Appointment.appointment_date <= today,
        ).count()

        doctor_queues.append({
            "doctor": doctor,
            "current": current,
            "waiting": waiting,
        })

    # Overall current serving patient
    current = Appointment.query.filter(
        Appointment.status == "Serving",
        Appointment.appointment_date == today,
    ).order_by(
        Appointment.id.desc()
    ).first()

    # Overall waiting patients
    waiting_today = Appointment.query.filter(
        Appointment.status == "Waiting",
        Appointment.appointment_date <= today,
    ).count()

    return render_template(
        "admin/dashboard.html",
        appointments=appointments,
        doctors=doctors,
        doctor_queues=doctor_queues,
        current=current,
        waiting_today=waiting_today,
        today=today,
    )


# ============================================================
# ADD DOCTOR
# ============================================================

@admin_bp.route("/doctor/add", methods=["POST"])
def add_doctor():

    if not is_admin():
        return redirect(url_for("auth.login"))

    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    department = request.form.get("department", "").strip()
    available_from = request.form.get("available_from", "")
    available_to = request.form.get("available_to", "")

    from_time = parse_time(available_from)
    to_time = parse_time(available_to)

    if (
        not name
        or len(name) > 100
        or not specialization
        or len(specialization) > 100
        or not department
        or len(department) > 100
    ):
        flash(
            "Doctor details are required and must be within 100 characters.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    if not from_time or not to_time or from_time >= to_time:
        flash(
            "Doctor availability time is invalid.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    doctor = Doctor(
        name=name,
        specialization=specialization,
        department=department,
        available_from=available_from,
        available_to=available_to,
        active=True,
    )

    db.session.add(doctor)
    db.session.commit()

    flash(
        "Doctor added successfully.",
        "success",
    )

    return redirect(url_for("admin.dashboard"))


# ============================================================
# EDIT DOCTOR
# ============================================================

@admin_bp.route("/doctor/<int:doctor_id>/edit", methods=["POST"])
def edit_doctor(doctor_id):

    if not is_admin():
        return redirect(url_for("auth.login"))

    doctor = db.session.get(Doctor, doctor_id)

    if not doctor:
        flash(
            "Doctor not found.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    name = request.form.get("name", "").strip()
    specialization = request.form.get("specialization", "").strip()
    department = request.form.get("department", "").strip()
    available_from = request.form.get("available_from", "")
    available_to = request.form.get("available_to", "")

    from_time = parse_time(available_from)
    to_time = parse_time(available_to)

    if (
        not name
        or len(name) > 100
        or not specialization
        or len(specialization) > 100
        or not department
        or len(department) > 100
    ):
        flash(
            "Doctor details are required and must be within 100 characters.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    if not from_time or not to_time or from_time >= to_time:
        flash(
            "Doctor availability time is invalid.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    doctor.name = name
    doctor.specialization = specialization
    doctor.department = department
    doctor.available_from = available_from
    doctor.available_to = available_to

    db.session.commit()

    flash(
        "Doctor information updated successfully.",
        "success",
    )

    return redirect(url_for("admin.dashboard"))


# ============================================================
# REMOVE / DEACTIVATE DOCTOR
# ============================================================

@admin_bp.route("/doctor/<int:doctor_id>/remove", methods=["POST"])
def remove_doctor(doctor_id):

    if not is_admin():
        return redirect(url_for("auth.login"))

    doctor = db.session.get(Doctor, doctor_id)

    if not doctor:
        flash(
            "Doctor not found.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    doctor.active = False

    db.session.commit()

    flash(
        f"{doctor.name} has been removed from active doctors.",
        "success",
    )

    return redirect(url_for("admin.dashboard"))


# ============================================================
# RESTORE DOCTOR
# ============================================================

@admin_bp.route("/doctor/<int:doctor_id>/restore", methods=["POST"])
def restore_doctor(doctor_id):

    if not is_admin():
        return redirect(url_for("auth.login"))

    doctor = db.session.get(Doctor, doctor_id)

    if not doctor:
        flash(
            "Doctor not found.",
            "danger",
        )
        return redirect(url_for("admin.dashboard"))

    doctor.active = True

    db.session.commit()

    flash(
        f"{doctor.name} is active again.",
        "success",
    )

    return redirect(url_for("admin.dashboard"))


# ============================================================
# UPDATE APPOINTMENT STATUS
# ============================================================

@admin_bp.route(
    "/appointment/<int:appointment_id>/status/<status>",
    methods=["POST"]
)
def update_status(appointment_id, status):

    if not is_admin():
        return redirect(url_for("auth.login"))

    appointment = db.session.get(
        Appointment,
        appointment_id
    )

    if not appointment:
        flash(
            "Appointment not found.",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))

    today = date.today()

    # --------------------------------------------------------
    # WAITING -> SERVING
    # --------------------------------------------------------

    if status == "Serving":

        if appointment.status != "Waiting":
            flash(
                "Only waiting appointments can be served.",
                "warning"
            )
            return redirect(url_for("admin.dashboard"))

        if appointment.appointment_date > today:
            flash(
                "A future appointment cannot be served yet.",
                "warning"
            )
            return redirect(url_for("admin.dashboard"))

        current = Appointment.query.filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.status == "Serving",
            Appointment.appointment_date == today,
        ).first()

        if current and current.id != appointment.id:
            current.status = "Completed"

        appointment.status = "Serving"

        db.session.commit()

        # ── AWS SES: Notify patient that it is their turn ──
        patient = db.session.get(User, appointment.patient_id)
        if patient:
            aws.send_now_serving_email(
                patient_email=patient.email,
                patient_name=patient.name,
                doctor_name=appointment.doctor.name,
                token=appointment.token,
            )

        flash(
            f"Token {appointment.token} "
            f"({appointment.doctor.name}) is now serving.",
            "success"
        )

    # --------------------------------------------------------
    # SERVING -> COMPLETED
    # --------------------------------------------------------

    elif status == "Completed":

        if appointment.status != "Serving":
            flash(
                "Only the currently serving appointment can be completed.",
                "warning"
            )
            return redirect(url_for("admin.dashboard"))

        appointment.status = "Completed"

        db.session.commit()

        flash(
            f"Token {appointment.token} completed.",
            "success"
        )

    # --------------------------------------------------------
    # SERVING -> WAITING
    # --------------------------------------------------------

    elif status == "Waiting":

        if appointment.status != "Serving":
            flash(
                "Only a serving appointment can be returned to waiting.",
                "warning"
            )
            return redirect(url_for("admin.dashboard"))

        appointment.status = "Waiting"

        db.session.commit()

        flash(
            f"Token {appointment.token} returned to waiting.",
            "success"
        )

    else:
        flash(
            "Invalid appointment status.",
            "danger"
        )

    return redirect(url_for("admin.dashboard"))


# ============================================================
# DOCTOR-WISE CALL NEXT PATIENT
# ============================================================

@admin_bp.route(
    "/queue/next/<int:doctor_id>",
    methods=["POST"]
)
def next_patient(doctor_id):

    if not is_admin():
        return redirect(url_for("auth.login"))

    doctor = db.session.get(
        Doctor,
        doctor_id
    )

    if not doctor:
        flash(
            "Doctor not found.",
            "danger"
        )
        return redirect(url_for("admin.dashboard"))

    if not doctor.active:
        flash(
            f"{doctor.name} is not an active doctor.",
            "warning"
        )
        return redirect(url_for("admin.dashboard"))

    today = date.today()

    # --------------------------------------------------------
    # COMPLETE CURRENT PATIENT FOR THIS DOCTOR
    # --------------------------------------------------------

    current = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "Serving",
        Appointment.appointment_date == today,
    ).order_by(
        Appointment.id.desc()
    ).first()

    if current:
        current.status = "Completed"

    # --------------------------------------------------------
    # FIND NEXT WAITING PATIENT FOR THIS DOCTOR
    # --------------------------------------------------------

    nxt = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.status == "Waiting",
        Appointment.appointment_date <= today,
    ).order_by(
        Appointment.appointment_date.asc(),
        Appointment.appointment_time.asc(),
        Appointment.token.asc(),
        Appointment.id.asc(),
    ).first()

    if nxt:

        nxt.status = "Serving"

        db.session.commit()

        # ── AWS SES: Notify patient that it is their turn ──
        patient = db.session.get(User, nxt.patient_id)
        if patient:
            aws.send_now_serving_email(
                patient_email=patient.email,
                patient_name=patient.name,
                doctor_name=doctor.name,
                token=nxt.token,
            )

        flash(
            f"Token {nxt.token} "
            f"({doctor.name}) is now serving.",
            "success"
        )

    else:

        # If there was a current patient but no next patient,
        # the current one has already been completed above.
        db.session.commit()

        flash(
            f"No waiting appointments are available for {doctor.name}.",
            "info"
        )

    return redirect(url_for("admin.dashboard"))