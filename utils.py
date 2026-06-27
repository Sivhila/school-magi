"""
utils.py — Helpers, decorators, plan enforcement
"""
import os, random
from datetime import datetime
from functools import wraps
from flask import redirect, url_for, flash, g, current_app, abort
from flask_login import current_user
from extensions import db


# ── Grade / Balance helpers ────────────────────────────────────────
def calculate_grade(marks):
    if marks >= 80: return "A"
    if marks >= 70: return "B"
    if marks >= 60: return "C"
    if marks >= 50: return "D"
    return "F"


def calculate_balance(student_id, term_id, school_id):
    from models import Student, FeeStructure, Payment
    student = Student.query.get(student_id)
    if not student:
        return 0
    fee = FeeStructure.query.filter_by(
            school_id=school_id, class_id=student.class_id, term_id=term_id
            ).first()
    total_paid = (
            db.session.query(db.func.sum(Payment.amount_paid))
            .filter_by(school_id=school_id, student_id=student_id, term_id=term_id)
            .scalar() or 0
            )
    return (fee.amount - total_paid) if fee else 0


def generate_unique_reference(school_id):
    from models import Payment
    while True:
        ref = "RCT-" + str(random.randint(10000, 99999))
        if not Payment.query.filter_by(school_id=school_id, reference=ref).first():
            return ref


def allowed_file(filename):
    exts = current_app.config.get("ALLOWED_EXTENSIONS", set())
    return "." in filename and filename.rsplit(".", 1)[1].lower() in exts


def send_notification(user_id, school_id, message, notif_type):
    """Queue a notification (caller must commit)."""
    from models import Notification
    n = Notification(user_id=user_id, school_id=school_id,
            message=message, type=notif_type)
    db.session.add(n)


# ── Email helpers ─────────────────────────────────────────────────
def send_verification_email(user):
    """Send email verification link."""
    from extensions import mail
    from flask_mail import Message
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = s.dumps(user.email, salt="email-verify")
    link = url_for("onboarding.verify_email", token=token, _external=True)
    msg = Message(
            subject="Verify your EduManage account",
            recipients=[user.email],
            html=f"""
            <h2>Welcome to EduManage!</h2>
            <p>Click the link below to verify your email address:</p>
            <a href="{link}" style="background:#0f1f3d;color:#fff;padding:12px 24px;
            border-radius:8px;text-decoration:none;font-weight:bold;">
            Verify Email
            </a>
            <p>This link expires in 24 hours.</p>
            """
            )
    mail.send(msg)


def verify_email_token(token, max_age=86400):
    from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = s.loads(token, salt="email-verify", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None



# ── Plan limit enforcement ─────────────────────────────────────────
def check_plan_limit(resource: str):
    """
    Check whether the current school has hit its plan limit.
    resource: 'students' | 'teachers'
    Returns True if allowed, False if at limit.
    """
    from models import Student, Teacher
    school = getattr(g, "school", None)
    if not school:
        return True
    
    limits = current_app.config["PLAN_LIMITS"]
    plan_limits = limits.get(school.plan, limits["free"])
    limit = plan_limits.get(resource, 0)

    if resource == "students":
        count = Student.query.filter_by(school_id=school.id).count()
    elif resource == "teachers":
        count = Teacher.query.filter_by(school_id=school.id).count()
    else:
        return True

    return count < limit


def plan_feature_required(min_plan: str):
    """
    Decorator: blocks a route if the school's plan is below min_plan.
    Order: free < starter < growth < enterprise
    """
    plan_order = ["free", "starter", "growth", "enterprise"]


def decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        school = getattr(g, "school", None)
        if not school:
            abort(403)
        current_idx = plan_order.index(school.plan) if school.plan in plan_order else 0
        
        required_idx = plan_order.index(min_plan) if min_plan in plan_order else 0

        if current_idx < required_idx:
            flash(f"This feature requires the {min_plan.title()} plan or higher.", "warning")
            return redirect(url_for("billing.plans"))

        return f(*args, **kwargs)

    return wrapper
return decorator



# ── Role decorators ───────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ("admin", "superadmin"):
            flash("Admin access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "teacher":
            flash("Teacher access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "student":
            flash("Student access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def parent_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "parent":
            flash("Parent access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superadmin:
            abort(403)
        return f(*args, **kwargs)
    return decorated
