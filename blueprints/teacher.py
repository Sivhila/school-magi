"""
blueprints/teacher.py — All teacher routes
"""
import os
import datetime
from flask import (Blueprint, render_template, request, redirect,
                           url_for, flash, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import (db, Student, SchoolClass, Subject, Teacher,
                            Attendance, Material, Assignment, Submission,
                                                Result, Exam, Announcement, Notification, User)
from utils import (teacher_required, calculate_grade, send_notification,
                           allowed_file)

teacher = Blueprint("teacher", __name__, url_prefix="/teacher")


# ── Dashboard ──────────────────────────────────────────────────────────────────
@teacher.route("/dashboard")
@login_required
@teacher_required
def dashboard():
    materials      = Material.query.count()
    announcements  = Announcement.query.count()
    return render_template(
            "teacher/teacher_dashboard.html",
            materials=materials,
            announcements=announcements,
            )


# ── Attendance ─────────────────────────────────────────────────────────────────
@teacher.route("/attendance", methods=["GET", "POST"])
@login_required
@teacher_required
def attendance():
    classes = SchoolClass.query.all()

    if request.method == "POST":
        class_id = request.form.get("class_id")

        if not class_id:
            flash("Missing field required", "danger")
            return redirect(url_for("teacher.attendance"))

        try:
            class_id = int(class_id)
        except (ValueError, TypeError):
            flash("Invalid input", "danger")
            return redirect(url_for("teacher.attendance"))
        return redirect(url_for("teacher.mark_attendance", class_id=class_id))
    
    return render_template("teacher/select_class.html", classes=classes)


@teacher.route("/attendance/<int:class_id>", methods=["GET", "POST"])
@login_required
@teacher_required
def mark_attendance(class_id):
    students = Student.query.filter_by(class_id=class_id).all()
    
    if request.method == "POST":
        date_str = request.form.get("date")

        if not date_str:
            flash("Date is required", "danger")
            return redirect(url_for("teacher.mark_attendance", class_id=class_id))

        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            flash("Invalid date format", "danger")
            return redirect(url_for("teacher.mark_attendance", class_id=class_id))

        for student in students:
            status = request.form.get(f"status_{student.id}")

            if not status:
                flash("All students must have attendance marked", "danger")
                return redirect(
                        url_for("teacher.mark_attendance", class_id=class_id)
                        )

                existing = Attendance.query.filter_by(
                        student_id=student.id, date=date_obj
                        ).first()

                if existing:
                    existing.status = status
                else:
                    record = Attendance(
                            student_id=student.id,
                            class_id=class_id,
                            date=date_obj,
                            status=status,
                            )
                    db.session.add(record)
                    db.session.commit()
                    flash("Attendance marked successfully!", "success")
                    return redirect(url_for("teacher.dashboard"))
                
                return render_template(
                        "teacher/mark_attendance.html",
                        students=students,
                        class_id=class_id,
                        )


# ── Upload Material ────────────────────────────────────────────────────────────
@teacher.route("/materials/upload", methods=["GET", "POST"])
@login_required
@teacher_required
def upload_material():
    classes  = SchoolClass.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":
        title       = request.form.get("title")
        description = request.form.get("description")
        class_id    = request.form.get("class_id")
        subject_id  = request.form.get("subject_id")
        file        = request.files.get("file")

        if not all([title, description, class_id, subject_id, file]):
            flash("Please fill all fields and upload a file", "danger")
            return redirect(url_for("teacher.upload_material"))

        if file.filename == "":
            flash("No file selected", "danger")
            return redirect(url_for("teacher.upload_material"))

        if not allowed_file(file.filename):
            flash("File type not allowed", "danger")
            return redirect(url_for("teacher.upload_material"))

        try:
            class_id   = int(class_id)
            subject_id = int(subject_id)
        except (ValueError, TypeError):
            flash("Invalid inputs", "danger")
            return redirect(url_for("teacher.upload_material"))
        
        filename = secure_filename(file.filename)
        file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))
        teacher_record = Teacher.query.filter_by(user_id=current_user.id).first()

        material = Material(
                title=title,
                description=description,
                filename=filename,
                teacher_id=teacher_record.id if teacher_record else None,
                class_id=class_id,
                subject_id=subject_id,
                )
        db.session.add(material)
        
        # Notify students
        students = Student.query.filter_by(class_id=class_id).all()
        for student in students:
            user = User.query.filter_by(username=student.admission_no).first()
            if user:
                send_notification(
                        user.id,
                        f"New material uploaded: {title}",
                        "material",
                        )
                db.session.commit()
                flash("Material uploaded successfully!", "success")
                return redirect(url_for("teacher.dashboard"))

            return render_template(
                    "teacher/upload_materials.html",
                    classes=classes,
                    subjects=subjects,
                    )


# ── Create Assignment ──────────────────────────────────────────────────────────
@teacher.route("/create-assignment", methods=["GET", "POST"])
@login_required
@teacher_required
def create_assignment():
    classes  = SchoolClass.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":
        title       = request.form.get("title")
        description = request.form.get("description")
        class_id    = request.form.get("class_id")
        subject_id  = request.form.get("subject_id")
        due_date    = request.form.get("due_date")
        
        if not all([title, description, class_id, subject_id, due_date]):
            flash("All fields are required", "danger")
            return redirect(url_for("teacher.create_assignment"))

        try:
            due_date = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format", "danger")
            return redirect(url_for("teacher.create_assignment"))

        teacher_record = Teacher.query.filter_by(user_id=current_user.id).first()
        assignment = Assignment(
                title=title,
                description=description,
                class_id=int(class_id),
                subject_id=int(subject_id),
                teacher_id=teacher_record.id if teacher_record else None,
                deadline=due_date,
                )
        db.session.add(assignment)
        db.session.commit()
        flash("Assignment created!", "success")
        return redirect(url_for("teacher.create_assignment"))
    
    return render_template(
            "teacher/create_assignment.html",
            classes=classes,
            subjects=subjects,
            )


# ── View Submissions ───────────────────────────────────────────────────────────
@teacher.route("/submissions/<int:assignment_id>")
@login_required
@teacher_required
def view_submissions(assignment_id):
    submissions = Submission.query.filter_by(assignment_id=assignment_id).all()
    return render_template(
            "teacher/submissions.html", submissions=submissions
            )


# ── Grade Submission ───────────────────────────────────────────────────────────
@teacher.route("/grade/<int:submission_id>", methods=["GET", "POST"])
@login_required
@teacher_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)

    if request.method == "POST":
        marks    = request.form.get("marks")
        feedback = request.form.get("feedback")

        if not marks or not feedback:
            flash("All fields are required", "danger")
            return redirect(url_for("teacher.grade_submission", submission_id=submission_id))

        submission.marks    = float(marks)
        submission.feedback = feedback
        db.session.commit()

        flash("Assignment graded!", "success")
        return redirect(
                url_for("teacher.view_submissions", assignment_id=submission.assignment_id)
                )

    return render_template(
            "teacher/grade_submission.html", submission=submission
            )


# ── Enter Results ──────────────────────────────────────────────────────────────
@teacher.route("/enter-results", methods=["GET", "POST"])
@login_required
@teacher_required
def enter_results():
    classes  = SchoolClass.query.all()
    subjects = Subject.query.all()
    exams    = Exam.query.all()

    if request.method == "POST":
        class_id   = request.form.get("class_id")
        subject_id = request.form.get("subject_id")
        exam_id    = request.form.get("exam_id")

        if not all([class_id, subject_id, exam_id]):
            flash("All fields required", "danger")
            return redirect(url_for("teacher.enter_results"))

        try:
            class_id   = int(class_id)
            subject_id = int(subject_id)
            exam_id    = int(exam_id)
        except ValueError:
            flash("Invalid input", "danger")
            return redirect(url_for("teacher.enter_results"))

        students = Student.query.filter_by(class_id=class_id).all()
        return render_template(
                "teacher/enter_marks.html",
                students=students,
                class_id=class_id,
                subject_id=subject_id,
                exam_id=exam_id,
                )

    return render_template(
            "teacher/select_results.html",
            classes=classes,
            subjects=subjects,
            exams=exams,
            )


@teacher.route(
        "/enter-results/<int:class_id>/<int:subject_id>/<int:exam_id>",
        methods=["GET", "POST"],
        )
@login_required
@teacher_required
def enter_marks(class_id, subject_id, exam_id):
    students = Student.query.filter_by(class_id=class_id).all()
    subject  = Subject.query.get(subject_id)

    if request.method == "POST":
        for student in students:
            marks = request.form.get(f"marks_{student.id}")

            if not marks:
                flash("Marks required", "danger")
                return redirect(url_for("teacher.enter_results"))

            if marks:
                existing = Result.query.filter_by(
                        student_id=student.id,
                        subject_id=subject_id,
                        exam_id=exam_id,
                        ).first()

                if existing:
                    existing.marks = float(marks)
                else:
                    result = Result(
                            student_id=student.id,
                            subject_id=subject_id,
                            exam_id=exam_id,
                            marks=float(marks),
                            )
                    db.session.add(result)

                # Notify student
                user = User.query.filter_by(username=student.admission_no).first()
                if user and subject:
                    send_notification(
                            user.id,
                            f"Your {subject.name} results have been uploaded",
                            "result",
                            )

        db.session.commit()
        flash("Marks saved successfully", "success")
        return redirect(url_for("teacher.dashboard"))

    return render_template(
            "teacher/enter_marks.html", students=students
            )
