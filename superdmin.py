
"""
blueprints owner dashboard - see all schools, usage, revenue.
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from sqlalchemy import func
from extensions import db
from models import School, User, Student, Teacher, Subscription, Notification
from utils import superadmin_required

superadmin = Blueprint("superadmin", __name__, url_prefix="/superadmin")


# ── Dashboard ─────────────────────────────────────────────────────
@superadmin.route("/")
@login_required
@superadmin_required
def dashboard():
    total_schools  = School.query.count()
    active_schools = School.query.filter_by(is_active=True).count()
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()

    # Revenue (paid plans)
    paid_schools = School.query.filter(School.plan != "free").all()
    mrr = sum(_school_mrr(s) for s in paid_schools)

    # Recent signups (last 30 days)
    cutoff = datetime.utcnow() - timedelta(days=30)
    recent_schools = School.query.filter(School.created_at >= cutoff)\
            .order_by(School.created_at.desc()).all()

    # Plan breakdown
    plan_counts = db.session.query(School.plan, func.count(School.id))\
            .group_by(School.plan).all()

    # Recent subscriptions
    recent_subs = Subscription.query.order_by(Subscription.created_at.desc()).limit(10).all()
    
    return render_template("superadmin/dashboard.html",
            total_schools=total_schools,
            active_schools=active_schools,
            total_students=total_students,
            total_teachers=total_teachers,
            mrr=mrr,
            recent_schools=recent_schools,
            plan_counts=dict(plan_counts),
            recent_subs=recent_subs,
            )


# ── All Schools ───────────────────────────────────────────────────
@superadmin.route("/schools")
@login_required
@superadmin_required
def schools():
    q      = request.args.get("q", "")
    plan   = request.args.get("plan", "")
    status = request.args.get("status", "")
    
    query = School.query
    if q:
        query = query.filter(School.name.ilike(f"%{q}%") | School.subdomain.ilike(f"%{q}%"))
    if plan:
        query = query.filter_by(plan=plan)
    if status == "active":
        query = query.filter_by(is_active=True)
    elif status == "inactive":
        query = query.filter_by(is_active=False)

    all_schools = query.order_by(School.created_at.desc()).all()
    
    return render_template("superadmin/schools.html",
            schools=all_schools, q=q, plan=plan, status=status)


# ── School Detail ─────────────────────────────────────────────────
@superadmin.route("/schools/<int:school_id>")
@login_required
@superadmin_required
def school_detail(school_id):
    school   = School.query.get_or_404(school_id)
    students = Student.query.filter_by(school_id=school_id).count()
    teachers = Teacher.query.filter_by(school_id=school_id).count()
    subs     = Subscription.query.filter_by(school_id=school_id)\
            .order_by(Subscription.created_at.desc()).all()
    users    = User.query.filter_by(school_id=school_id).all()
    return render_template("superadmin/school_detail.html",
            school=school, students=students,
            teachers=teachers, subs=subs, users=users)


# ── Activate / Deactivate School ─────────────────────────────────
@superadmin.route("/schools/<int:school_id>/toggle", methods=["POST"])
@login_required
@superadmin_required
def toggle_school(school_id):
    school = School.query.get_or_404(school_id)
    school.is_active = not school.is_active
    db.session.commit()
    status = "activated" if school.is_active else "deactivated"
    flash(f"School '{school.name}' has been {status}.", "success")
    return redirect(url_for("superadmin.school_detail", school_id=school_id))



# ── Override Plan ─────────────────────────────────────────────────
@superadmin.route("/schools/<int:school_id>/plan", methods=["POST"])
@login_required
@superadmin_required
def override_plan(school_id):
    school   = School.query.get_or_404(school_id)
    new_plan = request.form.get("plan")
    valid    = {"free", "starter", "growth", "enterprise"}
    if new_plan not in valid:
        flash("Invalid plan.", "danger")
    else:
        school.plan = new_plan
        db.session.commit()
        flash(f"Plan updated to {new_plan.title()}.", "success")
    return redirect(url_for("superadmin.school_detail", school_id=school_id))


# ── Usage Analytics ───────────────────────────────────────────────
@superadmin.route("/analytics")
@login_required
@superadmin_required
def analytics():
    # Signups over last 12 months
    months, signup_counts = _monthly_signups(12)

    # Revenue over last 12 months
    _, revenue_counts = _monthly_revenue(12)

    # Plan distribution
    plan_data = db.session.query(School.plan, func.count(School.id))\
            .group_by(School.plan).all()


    return render_template("superadmin/analytics.html",
            months=months,
            signup_counts=signup_counts,
            revenue_counts=revenue_counts,
            plan_data=dict(plan_data))



# ── API: Stats JSON (for live dashboard refresh) ──────────────────
@superadmin.route("/api/stats")
@login_required
@superadmin_required
def api_stats():
    return jsonify({
        "schools":  School.query.count(),
        "students": Student.query.count(),
        "teachers": Teacher.query.count(),
        "paid":     School.query.filter(School.plan != "free").count(),
        })


# ── Helpers ───────────────────────────────────────────────────────
def _school_mrr(school):
    """Estimate MRR from a school's plan."""
    from flask import current_app
    prices = current_app.config["STRIPE_PRICES"]
    info   = prices.get(school.plan, {})
    if school.billing_cycle == "yearly":
        return info.get("amount_yearly", 0) / 12
    return info.get("amount_monthly", 0)


def _monthly_signups(n_months):
    months, counts = [], []
    now = datetime.utcnow()
    for i in range(n_months - 1, -1, -1):
        start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        end   = (start + timedelta(days=32)).replace(day=1)
        c     = School.query.filter(School.created_at >= start,
                School.created_at < end).count()
        months.append(start.strftime("%b %Y"))
        counts.append(c)
    return months, counts


def _monthly_revenue(n_months):
    months, amounts = [], []
    now = datetime.utcnow()
    for i in range(n_months - 1, -1, -1):
        start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        end   = (start + timedelta(days=32)).replace(day=1)
        total = db.session.query(func.sum(Subscription.amount))\
                .filter(Subscription.created_at >= start,
                        Subscription.created_at < end,
                        Subscription.status == "active").scalar() or 0
        months.append(start.strftime("%b %Y"))
        amounts.append(round(total, 2))
        return months, amounts
