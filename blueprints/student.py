"""
blueprints/student.py — All student-facing routes
"""
import os
import datetime
from flask import (Blueprint, render_template, request, redirect,
                           url_for, flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from weasyprint import HTML
from flask import make_response
from models import (db, Student, Result, Material, Assignment,
                            Submission, Announcement, Payment, Term,
                                                Notification, Timetable, Exam, Subject)
from utils import (student_required, calculate_balance, calculate_grade,
                           allowed_file)

student = Blueprint("student", __name__, url_prefix="/student")


# ── Dashboard ──────────────────────────────────────────────────────────────────
@student.route("/dashboard")
@login_required
@student_required
def dashboard():
    s         = Student.query.get(current_user.student_id)
    results   = Result.query.filter_by(student_id=s.id).all()
    materials = Material.query.filter_by(class_id=s.class_id).all()
    return render_template(
            "student/student_dashboard.html",
            student=s,
            results=results,
            materials=materials,
            )


# ── Announcements ──────────────────────────────────────────────────────────────
@student.route("/announcements")
@login_required
@student_required
def announcements():
    s     = Student.query.filter_by(
            admission_no=current_user.username
            ).first()
    today = datetime.date.today()

    # FIX: paginate() was called with no args — must provide page & per_page
    page  = request.args.get("page", 1, type=int)
    announcements_q = Announcement.query.filter(
            db.or_(
                Announcement.class_id == s.class_id,
                Announcement.class_id == None,
                ),
            db.or_(
                Announcement.expiry_date == None,
                Announcement.expiry_date >= today,
                ),
            ).order_by(Announcement.created_at.desc()).paginate(
                    page=page, per_page=10
                    )
            return render_template(
                    "student/announcements.html", announcements=announcements_q
                    )


# ── Fees ───────────────────────────────────────────────────────────────────────
@student.route("/fees")
@login_required
@student_required
def fees():
    s     = Student.query.filter_by(
            admission_no=current_user.username
            ).first()
    terms = Term.query.all()
    data  = []

    for term in terms:
        balance = calculate_balance(s.id, term.id)
        data.append({"term": term.name, "balance": balance})
    return render_template("student/fees.html", data=data)


# ── Assignments ────────────────────────────────────────────────────────────────
@student.route("/assignments")
@login_required
@student_required
def assignments():
    s = Student.query.filter_by(
            admission_no=current_user.username
            ).first()

    all_assignments = Assignment.query.filter_by(class_id=s.class_id).all()
    return render_template(
            "student/assignments.html", assignments=all_assignments
            )


# ── Submit Assignment ──────────────────────────────────────────────────────────
@student.route("/submit/<int:id>", methods=["GET", "POST"])
@login_required
@student_required
def submit_assignment(id):
    assignment = Assignment.query.get_or_404(id)

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            flash("File required", "danger")
            return redirect(url_for("student.submit_assignment", id=id))

        if not allowed_file(file.filename):
            flash("File type not allowed", "danger")
            return redirect(url_for("student.submit_assignment", id=id))

        filename = secure_filename(file.filename)
        file.save(
                os.path.join(current_app.config["ASSIGNMENT_UPLOAD"], filename)
                )

        submission = Submission(
                assignment_id=id,
                student_id=current_user.student_id,
                file_path=filename,
                )
        db.session.add(submission)
        db.session.commit()
        flash("Assignment submitted", "success")
        return redirect(url_for("student.dashboard")

    return render_template(
        "student/submit_assignment.html", assignment=assignment
        )


# ── Materials ──────────────────────────────────────────────────────────────────
@student.route("/materials")
@login_required
@student_required
def materials():
    s = Student.query.filter_by(
        admission_no=current_user.username
        ).first()
    all_materials = Material.query.filter_by(class_id=s.class_id).all()
    return render_template("student/materials.html", materials=all_materials)


# ── Report Card PDF ────────────────────────────────────────────────────────────
@student.route("/report-card/<int:student_id>/<int:term_id>")
@login_required
def report_card_pdf(student_id, term_id):
    s = Student.query.get_or_404(student_id)

    # FIX: ownership check — students can only view their own report card
    if current_user.role == "student":
        own = Student.query.filter_by(
            admission_no=current_user.username
            ).first()
        if not own or own.id != student_id:
            flash("Unauthorized", "danger")
            return redirect(url_for("student.dashboard"))

    results = (
        Result.query
        .join(Exam)
        .join(Term)
        .filter(
            Result.student_id == student_id,
            Term.id == term_id,
            )
        .all()
        )

    report      = []
    total_marks = 0

    for r in results:
    grade = calculate_grade(r.marks)
    report.append({
        "subject": r.subject.name,
        "marks":   r.marks,
        "grade":   grade,
        })
    total_marks += r.marks

    average     = 0
    final_grade = "N/A"
    if results:
        average     = total_marks / len(results)
        final_grade = calculate_grade(average)

    html = render_template(
            "student/report_card_pdf.html",
            student=s,
            report=report,
            total=total_marks,
            average=round(average, 2),
            final_grade=final_grade,
            )

    pdf      = HTML(string=html).write_pdf()
    response = make_response(pdf)
    response.headers["Content-Type"]        = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=report_card.pdf"
    return response


# ── Notifications ──────────────────────────────────────────────────────────────
@student.route("/notifications")
@login_required
@student_required
def notifications():
    notifs = (
            Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .all()
            )
    return render_template("student/notifications.html", notifications=notifs)


@student.route("/notifications/read/<int:id>")
@login_required
@student_required
def mark_read(id):
    note = Notification.query.get_or_404(id)
    # FIX: ownership check added
    if note.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("student.dashboard"))
    note.is_read = True
    db.session.commit()
    return redirect(url_for("student.notifications"))
