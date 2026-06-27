"""
blueprints/parent.py — All parent-facing routes
"""
import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import (db, Parent, ParentStudent, Student, Result,
                            Attendance, Term, Announcement, Notification)
from utils import parent_required, calculate_balance

parent = Blueprint("parent", __name__, url_prefix="/parent")


# ── Dashboard ──────────────────────────────────────────────────────────────────
@parent.route("/dashboard")
@login_required
@parent_required
def dashboard():
    p = Parent.query.filter_by(user_id=current_user.id).first()

    links    = ParentStudent.query.filter_by(parent_id=p.id).all()
    students = [link.student for link in links]

    return render_template("parent/parent_dashboard.html", students=students)


# ── Child Results ──────────────────────────────────────────────────────────────
@parent.route("/results/<int:student_id>")
@login_required
@parent_required
def results(student_id):
    results = Result.query.filter_by(student_id=student_id).all()
    return render_template("parent/results.html", results=results)


# ── Child Attendance ───────────────────────────────────────────────────────────
@parent.route("/attendance/<int:student_id>")
@login_required
@parent_required
def attendance(student_id):
    records = Attendance.query.filter_by(student_id=student_id).all()
    return render_template("parent/attendance.html", records=records)


# ── Child Fees ─────────────────────────────────────────────────────────────────
@parent.route("/fees/<int:student_id>")
@login_required
@parent_required
def fees(student_id):
    terms = Term.query.all()
    data  = []
    for term in terms:
        balance = calculate_balance(student_id, term.id)
        data.append({"term": term.name, "balance": balance})
    return render_template("parent/fees.html", data=data)


# ── Announcements ──────────────────────────────────────────────────────────────
@parent.route("/announcements")
@login_required
@parent_required
def announcement():
    p = Parent.query.filter_by(user_id=current_user.id).first()

    links       = ParentStudent.query.filter_by(parent_id=p.id).all()
    student_ids = [l.student_id for l in links]
    students    = Student.query.filter(Student.id.in_(student_ids)).all()
    class_ids   = [s.class_id for s in students]

    announcements = Announcement.query.filter(
            db.or_(
                Announcement.class_id.in_(class_ids),
                Announcement.class_id == None,
                )
            ).all()
    return render_template(
            "parent/announcements.html", announcements=announcements
            )


# ── Notifications ──────────────────────────────────────────────────────────────
@parent.route("/notifications")
@login_required
@parent_required
def notifications():
    notifs = (
            Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .all()
            )
    return render_template("parent/notifications.html", notifications=notifs)


@parent.route("/notifications/read/<int:id>")
@login_required
@parent_required
def mark_read(id):
    note = Notification.query.get_or_404(id)

    # Ownership check
    if note.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("parent.dashboard"))
    note.is_read = True
    db.session.commit()
    return redirect(url_for("parent.notifications"))

