"""
blueprints/onboarding.py
School self-registration, subdomain setup, email verification.
"""
import re
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash
from extensions import db
from models import School, User
from utils import send_verification_email, verify_email_token

onboarding = Blueprint("onboarding", __name__)

SUBDOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

RESERVED = {
            "www", "app", "api", "admin", "superadmin", "mail", "smtp",
                "ftp", "cdn", "static", "assets", "docs", "help", "support", "billing",
                }


# ── Landing / public home ─────────────────────────────────────────
@onboarding.route("/")
def landing():
    return render_template("public/landing.html")


@onboarding.route("/pricing")
def pricing():
    plans = current_app.config["PLAN_LIMITS"]
    features = current_app.config["PLAN_FEATURES"]
    prices = current_app.config["STRIPE_PRICES"]
    return render_template("public/pricing.html",
            plans=plans, features=features, prices=prices)


# ── School Registration ───────────────────────────────────────────
@onboarding.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        school_name = request.form.get("school_name", "").strip()
        subdomain   = request.form.get("subdomain", "").strip().lower()
        email       = request.form.get("email", "").strip().lower()
        password    = request.form.get("password", "")
        confirm_pw  = request.form.get("confirm_password", "")


        # ── Validation ──────────────────────────────────────
        errors = []
        if not all([school_name, subdomain, email, password]):
            errors.append("All fields are required.")
        if password != confirm_pw:
            errors.append("Passwords do not match.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if subdomain in RESERVED:
            errors.append(f"'{subdomain}' is a reserved name. Please choose another.")
        if not SUBDOMAIN_RE.match(subdomain):
            errors.append("Subdomain can only contain lowercase letters, numbers, and hyphens.")
        if School.query.filter_by(subdomain=subdomain).first():
            errors.append("That subdomain is already taken. Please choose another.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with that email already exists.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("onboarding/register.html",
                    form=request.form)

            # ── Create school ────────────────────────────────────
            school = School(
                    name=school_name,
                    subdomain=subdomain,
                    email=email,
                    plan="free",
                    trial_ends_at=datetime.utcnow() + timedelta(days=14),
                    )
            db.session.add(school)
            db.session.flush()  # get school.id

            # ── Create admin user ────────────────────────────────
            admin = User(
                    school_id=school.id,
                    username="admin",
                    email=email,
                    password_hash=generate_password_hash(password),
                    role="admin",
                    is_verified=False,
                    )
            db.session.add(admin)
            db.session.commit()

            # ── Send verification email ──────────────────────────
            try:
                send_verification_email(admin)
                flash("School registered! Check your email to verify your account.", "success")
            except Exception:
                flash("School registered! (Email sending failed — please contact support to verify.)", "warning")
                base   = current_app.config["BASE_DOMAIN"]
                proto  = current_app.config["APP_PROTOCOL"]
                school_url = f"{proto}://{subdomain}.{base}/login"
                return render_template("onboarding/registered.html",
                        school=school,
                        school_url=school_url)
                return render_template("onboarding/register.html", form={})


# ── Email Verification ───────────────────────────────────────────
@onboarding.route("/verify/<token>")
def verify_email(token):
    email = verify_email_token(token)
    if not email:
        flash("Verification link is invalid or has expired.", "danger")
        return redirect(url_for("onboarding.register"))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("onboarding.register"))

    if user.is_verified:
        flash("Email already verified. You can log in.", "info")
    else:
        user.is_verified = True
        # Also mark the school verified
        if user.school_id:
            school = School.query.get(user.school_id)
            if school:
                school.is_email_verified = True
        db.session.commit()
        flash("Email verified! You can now log in.", "success")


    # Redirect to their school's login page
    if user.school_id:
        school = School.query.get(user.school_id)
        if school:
            base  = current_app.config["BASE_DOMAIN"]
            proto = current_app.config["APP_PROTOCOL"]
            return redirect(f"{proto}://{school.subdomain}.{base}/login")
    return redirect(url_for("auth.login"))



# ── Resend Verification ───────────────────────────────────────────
@onboarding.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user  = User.query.filter_by(email=email).first()
        if user and not user.is_verified:
            try:
                send_verification_email(user)
                flash("Verification email resent! Check your inbox.", "success")
            except Exception:
                flash("Failed to send email. Please contact support.", "danger")
        else:
            flash("Email not found or already verified.", "info")
            return redirect(url_for("onboarding.resend_verification"))

        return render_template("onboarding/resend_verification.html")
