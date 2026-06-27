"""
blueprints/admin.py — All admin routes
"""
import os
import random
import datetime
from flask import (Blueprint, render_template, request, redirect,
                           url_for, flash, send_file)
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from models import (db, Student, Teacher, SchoolClass, User, Term, Exam,
                            Subject, FeeStructure, Payment, TeacherAssignment,
                                                Timetable, Announcement, Notification)
from utils import (admin_required, calculate_balance, send_notification,
                           generate_unique_reference, allowed_file)
from extensions import csrf

admin = Blueprint("admin", __name__, url_prefix="/admin")


# ── Dashboard ──────────────────────────────────────────────────────────────────
@admin.route("/dashboard")
@login_required
@admin_required
def dashboard():
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_classes  = SchoolClass.query.count()
    return render_template(
            "admin/admin_dashboard.html",
            total_students=total_students,
            total_teachers=total_teachers,
            total_classes=total_classes,
            )


# ── Student Registration ───────────────────────────────────────────────────────
@admin.route("/register-student", methods=["GET", "POST"])
@login_required
@admin_required
def register_student():
    classes = SchoolClass.query.all()

    if request.method == "POST":
        first_name   = request.form.get("first_name")
        last_name    = request.form.get("last_name")
        admission_no = request.form.get("admission_no")
        gender       = request.form.get("gender")
        class_id     = request.form.get("class_id")

        if not all([first_name, last_name, admission_no, gender, class_id]):
            flash("All fields are required", "danger")
            return redirect(url_for("admin.register_student"))

        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            flash("Invalid class selected", "danger")
            return redirect(url_for("admin.register_student"))

        if Student.query.filter_by(admission_no=admission_no).first():
            flash("Admission number already exists", "danger")
            return redirect(url_for("admin.register_student"))

        student = Student(
                first_name=first_name,
                last_name=last_name,
                admission_no=admission_no,
                gender=gender,
                class_id=class_id,
                )
        db.session.add(student)
        db.session.flush()  # get student.id before commit

        user = User(
                username=admission_no,
                role="student",
                student_id=student.id,
                password_hash=generate_password_hash("student123"),
                )
        db.session.add(user)
        db.session.commit()
        flash("Student registered successfully!", "success")
        return redirect(url_for("admin.students_list"))

    return render_template("admin/register_student.html", classes=classes)


# ── Students List ─────────────────────────────────────────────────────────────
@admin.route("/students")
@login_required
@admin_required
def students_list():
    students = Student.query.all()
    return render_template("admin/students_list.html", students=students)


# ── Create Class ───────────────────────────────────────────────────────────────
@admin.route("/create-class", methods=["GET", "POST"])
@login_required
@admin_required
def create_class():
    classes = SchoolClass.query.all()

    if request.method == "POST":
        name     = request.form.get("name")
        capacity = request.form.get("capacity")

        # FIX: was showing "Capacity must be greater than 0" for missing fields
        if not name or not capacity:
            flash("All fields are required", "danger")
            return redirect(url_for("admin.create_class"))

        try:
            capacity = int(capacity)
            if capacity <= 0:
                flash("Capacity must be greater than 0", "danger")
                return redirect(url_for("admin.create_class"))
            except (ValueError, TypeError):
                flash("Capacity must be a valid integer", "danger")
                return redirect(url_for("admin.create_class"))
            if SchoolClass.query.filter_by(name=name).first():
                flash("Class already exists", "danger")
                return redirect(url_for("admin.create_class"))

            new_class = SchoolClass(name=name, capacity=capacity)
            db.session.add(new_class)
            db.session.commit()
            flash("Class created successfully!", "success")
            return redirect(url_for("admin.dashboard"))

        return render_template("admin/create_class.html", classes=classes)


# ── Register Teacher ───────────────────────────────────────────────────────────
@admin.route("/register-teacher", methods=["GET", "POST"])
@login_required
@admin_required
def register_teacher():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name  = request.form.get("last_name")
        phone      = request.form.get("phone")

        if not first_name or not last_name or not phone:
            flash("All fields are required", "danger")
            return redirect(url_for("admin.register_teacher"))

        # FIX: was crashing with AttributeError if phone was None
        if not phone or not phone.isdigit():
            flash("Phone must be numbers only", "danger")
            return redirect(url_for("admin.register_teacher"))

        teacher = Teacher(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                staff_no="ST" + str(random.randint(1000, 9999)),
                )
        db.session.add(teacher)
        db.session.commit()
        flash("Teacher registered successfully!", "success")
        return redirect(url_for("admin.teachers_list"))

    return render_template("admin/register_teacher.html")


# ── Teachers List ─────────────────────────────────────────────────────────────
@admin.route("/teachers")
@login_required
@admin_required
def teachers_list():
    teachers = Teacher.query.all()
    return render_template("admin/teachers_list.html", teachers=teachers)


# ── Manage Terms ───────────────────────────────────────────────────────────────
@admin.route("/manage-terms", methods=["GET", "POST"])
@login_required
@admin_required
def manage_terms():
    if request.method == "POST":
        if "add_term" in request.form:
            name           = request.form.get("name")
            start_date_str = request.form.get("start_date")
            end_date_str   = request.form.get("end_date")

            if not all([name, start_date_str, end_date_str]):
                flash("All fields are required", "danger")
                return redirect(url_for("admin.manage_terms"))

            try:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date   = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
                # FIX: was only catching ValueError, not TypeError
            except (ValueError, TypeError):
                flash("Invalid date format", "danger")
                return redirect(url_for("admin.manage_terms"))

            new_term = Term(name=name, start_date=start_date, end_date=end_date)
            db.session.add(new_term)
            db.session.commit()
            flash("Term added successfully!", "success")
            return redirect(url_for("admin.manage_terms"))

        elif "add_exam" in request.form:
            name    = request.form.get("name")
            term_id = request.form.get("term_id")

            if not name or not term_id:
                flash("All fields are required", "danger")
                return redirect(url_for("admin.manage_terms"))

            try:
                term_id = int(term_id)
            # FIX: was only catching ValueError
            except (ValueError, TypeError):
                flash("Invalid term selected", "danger")
                return redirect(url_for("admin.manage_terms"))

            exam = Exam(name=name, term_id=term_id)
            db.session.add(exam)
            db.session.commit()
            flash("Exam added successfully!", "success")
            return redirect(url_for("admin.manage_terms"))
    
    terms = Term.query.all()
    exams = Exam.query.all()
    return render_template(
            "admin/manage_terms.html", terms=terms, exams=exams
            )


# ── Add Subject ────────────────────────────────────────────────────────────────
@admin.route("/add-subject", methods=["GET", "POST"])
@login_required
@admin_required
def add_subject():
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")

        if not name or not code:
            flash("All fields are required", "danger")
            return redirect(url_for("admin.add_subject"))

        if Subject.query.filter_by(code=code).first():
            flash("Subject code already exists", "danger")
            return redirect(url_for("admin.add_subject"))

        new_subject = Subject(name=name, code=code)
        # FIX: was doing db.session.add(subject) — 'subject' undefined
        db.session.add(new_subject)
        db.session.commit()
        flash("Subject added successfully!", "success")
        return redirect(url_for("admin.add_subject"))

    subjects = Subject.query.all()
    return render_template("admin/add_subject.html", subjects=subjects)


# ── Set Fees ───────────────────────────────────────────────────────────────────
@admin.route("/set-fees", methods=["GET", "POST"])
@login_required
@admin_required
def set_fees():
    classes = SchoolClass.query.all()
    terms   = Term.query.all()

    if request.method == "POST":
        class_id = request.form.get("class_id")
        term_id  = request.form.get("term_id")
        amount   = request.form.get("amount")

        if not all([class_id, term_id, amount]):
            flash("All fields are required", "danger")
            return redirect(url_for("admin.set_fees"))

        try:
            class_id = int(class_id)
            term_id  = int(term_id)
            amount   = float(amount)
        except (ValueError, TypeError):
            flash("Invalid input values", "danger")
            return redirect(url_for("admin.set_fees"))

        existing = FeeStructure.query.filter_by(
                class_id=class_id, term_id=term_id
                ).first()
        if existing:
            flash("Fees already set for this class and term", "warning")
            return redirect(url_for("admin.set_fees"))

        fee = FeeStructure(class_id=class_id, term_id=term_id, amount=amount)
        db.session.add(fee)
        db.session.commit()
        flash("Fees set successfully!", "success")

    return render_template(
            "admin/set_fees.html", classes=classes, terms=terms
            )


# ── Pay Fees ───────────────────────────────────────────────────────────────────
@admin.route("/pay-fees/<int:student_id>", methods=["GET", "POST"])
@login_required
@admin_required
def pay_fees(student_id):
    student = Student.query.get_or_404(student_id)
    terms   = Term.query.all()

    if request.method == "POST":
        term_id          = request.form.get("term_id")
        amount           = request.form.get("amount")
        bank_reference   = request.form.get("bank_reference")
        payment_date_str = request.form.get("payment_date")

        if not all([term_id, amount, bank_reference, payment_date_str]):
            flash("All fields are required", "danger")
            return redirect(url_for("admin.pay_fees", student_id=student.id))

        try:
            term_id      = int(term_id)
            amount       = float(amount)
            payment_date = datetime.datetime.strptime(
                    payment_date_str, "%Y-%m-%d"
                    ).date()
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return redirect(url_for("admin.pay_fees", student_id=student.id))
        
        if Payment.query.filter_by(bank_reference=bank_reference).first():
            flash("This bank reference already exists", "danger")
            return redirect(url_for("admin.pay_fees", student_id=student.id))
        # FIX: generate unique reference with loop, not random then check
        reference = generate_unique_reference()
        payment = Payment(
                student_id=student.id,
                term_id=term_id,
                amount_paid=amount,
                reference=reference,
                bank_reference=bank_reference,
                payment_date=payment_date,
                )
        db.session.add(payment)
        db.session.commit()
        flash("Payment recorded successfully!", "success")
        return redirect(url_for("admin.receipt", payment_id=payment.id))
    return render_template(
            "admin/pay_fees.html", student=student, terms=terms
            )


# ── Receipt ────────────────────────────────────────────────────────────────────
@admin.route("/receipt/<int:payment_id>")
@login_required
def receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    return render_template("admin/receipt.html", payment=payment)


# ── Create Timetable ───────────────────────────────────────────────────────────
@admin.route("/create-timetable", methods=["GET", "POST"])
@login_required
@admin_required
def create_timetable():
    classes  = SchoolClass.query.all()
    subjects = Subject.query.all()
    teachers = Teacher.query.all()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    if request.method == "POST":
        class_id   = request.form.get("class_id")
        subject_id = request.form.get("subject_id")
        teacher_id = request.form.get("teacher_id")
        day        = request.form.get("day")
        start_time = request.form.get("start_time")
        end_time   = request.form.get("end_time")

        if not all([class_id, subject_id, teacher_id, day, start_time, end_time]):
            flash("All fields are required", "danger")
            return redirect(url_for("admin.create_timetable"))
        
        try:
            class_id   = int(class_id)
            subject_id = int(subject_id)
            teacher_id = int(teacher_id)
        except (ValueError, TypeError):
            flash("Invalid selection", "danger")
            return redirect(url_for("admin.create_timetable"))

        # FIX: improved conflict detection — checks for any time overlap
        conflict = Timetable.query.filter(
                Timetable.teacher_id == teacher_id,
                Timetable.day == day,
                Timetable.start_time < end_time,
                Timetable.end_time > start_time,
                ).first()
        
        if conflict:
            flash("Teacher already assigned at this time", "danger")
            return redirect(url_for("admin.create_timetable"))

        timetable = Timetable(
                class_id=class_id,
                subject_id=subject_id,
                teacher_id=teacher_id,
                day=day,
                start_time=start_time,
                end_time=end_time,
                )
        db.session.add(timetable)
        db.session.commit()
        flash("Timetable entry added!", "success")
        return redirect(url_for("admin.create_timetable"))

    return render_template(
            "admin/create_timetable.html",
            classes=classes,
            subjects=subjects,
            teachers=teachers,
            days=days,
            )


# ── Announcements ──────────────────────────────────────────────────────────────
@admin.route("/announcements/new", methods=["GET", "POST"])
@login_required
@admin_required
def create_announcement():
    classes = SchoolClass.query.all()
    
    if request.method == "POST":
        title    = request.form.get("title")
        content  = request.form.get("content")
        class_id = request.form.get("class_id")

        if not title or not content or not class_id:
            flash("All fields are required", "danger")
            return redirect(url_for("admin.create_announcement"))

        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return redirect(url_for("admin.create_announcement"))

        announcement = Announcement(
                title=title,
                message=content,
                class_id=class_id,
                user_id=current_user.id,
                )
        db.session.add(announcement)


        # Notify students in that class
        students = Student.query.filter_by(class_id=class_id).all()
        for student in students:
            user = User.query.filter_by(username=student.admission_no).first()
            if user:
                send_notification(user.id, f"New announcement: {title}", "announcement")

        db.session.commit()
        flash("Announcement posted successfully!", "success")
        return redirect(url_for("auth.index"))

    return render_template("admin/create_announcement.html", classes=classes)


@admin.route("/announcement/delete/<int:id>")
@login_required
@admin_required
def delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    flash("Announcement deleted", "success")
    return redirect(url_for("auth.index"))


# ── Analytics ──────────────────────────────────────────────────────────────────
@admin.route("/analytics")
@login_required
@admin_required
def analytics():
    from models import Result, Attendance
    subjects         = Subject.query.all()
    subject_names    = []
    subject_averages = []

    for subject in subjects:
        results = Result.query.filter_by(subject_id=subject.id).all()
        avg = (sum(r.marks for r in results) / len(results)) if results else 0
        subject_names.append(subject.name)
        subject_averages.append(round(avg, 2))

        all_results = Result.query.all()
        pass_count  = sum(1 for r in all_results if r.marks >= 50)
        fail_count  = sum(1 for r in all_results if r.marks < 50)

        attendance = Attendance.query.all()
        present = sum(1 for a in attendance if a.status == "Present")
        absent  = sum(1 for a in attendance if a.status == "Absent")

        return render_template(
                "admin/analytics.html",
                subject_names=subject_names,
                subject_averages=subject_averages,
                pass_count=pass_count,
                fail_count=fail_count,
                present=present,
                absent=absent,
                )


# ── Timetable View ─────────────────────────────────────────────────────────────
@admin.route("/timetable/<int:class_id>")
@login_required
def view_timetable(class_id):
    timetable = Timetable.query.filter_by(class_id=class_id).all()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    return render_template(
            "timetable.html", timetable=timetable, days=days
            )


# ── Notifications ──────────────────────────────────────────────────────────────
@admin.route("/notifications")
@login_required
def get_notifications():
    notifications = (
            Notification.query
            .filter_by(user_id=current_user.id)
            .order_by(Notification.created_at.desc())
            .all()
            )
    
    return render_template(
            "notifications.html", notifications=notifications
            )


@admin.route("/notifications/read/<int:id>")
@login_required
def mark_read(id):
    note = Notification.query.get_or_404(id)
    # FIX: added ownership check — users can only mark their own notifications

    if note.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("auth.index"))
    note.is_read = True
    db.session.commit()
    return redirect(url_for("admin.get_notifications"))


# ── File Download ──────────────────────────────────────────────────────────────
@admin.route("/download/<path:filename>")
@login_required
def download_file(filename):
    from flask import current_app
    return send_file(
            os.path.join(current_app.config["UPLOAD_FOLDER"], filename),
            as_attachment=True,
            )
