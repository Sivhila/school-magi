from flask_login import LoginManager, login_User, login_required, logout_user, current_user
from models import User
import os
from werkzeuf.utils import secure_filename


UPLOAD_FOLDER = "uploads/materials"
ASSIGNMENT_UPLOAD = "uploads/assignments"

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        identifier = request.form["identifier"]
        password = request.form["password"]

        user = User.query.filter_by(username=identifier).first()

        if not user:
            student = Student.query.filter_by(admission_no=identifier).first()
            if student:
                user = User.query.filter_by(student_id=student.id).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid login details")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard()

if current_user.role == "admin":
    return redirect(url_for("admin_dashboard"))

elif current_user.role == "teacher":
    return redirect(url_for("teacher_dashboard"))

elif current_user.role == "student":
    return redirect(url_for("student_dashboard"))



@app.route("/admin/dashboard")
@login_required
def admin_dashboard():

    if current_user.role != "admin":
        return "Unauthorized", 403

    students = Student.query.count()
    teachers = Teacher.query.count()
    classes = SchoolClass.query.count()

    return render_template(
            "admin/dashboard.html",
            students=students,
            teachers=teachers,
            classes=classes
            )


@app.route("/teacher/dashboard")
@login_required
def teacher_dashboard():

    if current_user.role != "teacher":
        return "Unauthorized", 403

    materials = Material.query.count()
    announcement = Announcement.query.count()

    return render_template(
            "teacher/dashboard.html",
            materials=materials,
            announcements=announcements
            )


@app.route("/student/dashboard")
@login_required
def student_dashboard():

    if current_user.role != "student":
        return "Unauthorized", 403

    student = Student.query.get(current_user.student_id)

    results = Result.query.filter_by(student_id=student.id).all()
    materials = Material.query.filter_by(class_id=student.class_id).all()

    return render_template(
            "student/dashboard.html",
            student=student,
            results=results,
            materials=materials
            )


@app.route("/logout")
@login_required
def logout():

    logout_user()
    return redirect(url_for("login"))


@app.route("/students/register", methods=["GET", "POST"])
@login_required
def register_student():

    if current_user.role != "admin":
        return "Unauthorized", 403

    classes = SchoolClass.query.all()

    if request.method == "POST"

    full_name = request.form["full_name"]
    admission_no = request.form["admission_no"]
    gender = request.form["gender"]
    parent_phone = request.form["parent_phone"]
    class_id = request.form["class_id"]

    student = Student(
            full_name=full_name,
            admission_no=admission_no,
            gender=gender,
            parent_phone=parent_phone,
            class_id=class_id
            )
    db.session.add(student)
    db.session.commit()

    user = User(
            username=admission_no,
            role="student",
            student_id=student.id,
            password=generate_password_hash("student123")
            )
    db.sessio.add(user)
    db.session.commit()

    flash("Student registered successfuly")
    return redirect(url_for("students_list"))

return render_template("admin/register_student.html", classes=classes)



@app.route("/students")
@login_required
def students_list():

    if current_user.role != "admin":
        return "Unauthorized", 403

    students = Student.query.all()

    return render_template("admin/students_list.html", students=students)


@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():

    if current_user.role != "teacher":
        return "Unauthorized", 403

    classes = SchoolClass.query.all()

    if request.method == "POST":

        class_id = request.form["class_id"]

        return redirect(url_for("mark_attendance", class_id=class_id))

    return render_template("teacher/select_class.html", classes=classes)


@app.route("/attendance/<int:class_id>", methods=["GET", "POST"])
@login_required
def mark_attendance(class_id):

    if current_user.role != "teacher":
        return "Unauthorized", 403

    students = Student.query.filter_by(class_id=class_id).all()

    if request.method == "POST":

        for student in students:

            existing = Attendance.query.filter_by(
                    student_id=student.id,
                    date=datatime.utcnow().date()
                    ).first()

            if not existing:
                attendance = Attendance(
                        student_id=student.id
                        status=status
                        )
                db.session.add(attendance)
                db.session.commit()

            flash("Attendance saved successfully")

            return redirect(url_for("attendance"))

        return render_template(
                "teacher/mark_attendance.html",
                students=students
                )


@app.route("/classes", methods=["GET", "POST"])
@login_required
def manage_classes():

    if current_user.role != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        name = request.form["name"]

        new_class = SchoolClass(name=name)

        db.session.add(new_class)
        db.session.commit()

        flash("Class created successfully")
        return redirect(url_for("manage_classes"))

    classes = SchoolClass.query.all()

    return render_template("admin/classes.html", classes=classes)


@app.route("/teachers/register", methods=["GET", "POST"])
@login_required
def register_teacher():

    if current_user.role != "admin":
        return "Unauthorized", 403

    if request.method == "POST":

        full_name = request.form["full_name"]
        phone = request.form["phone"]

        teacher = Teacher(
                full_name=full_name,
                phone=phone
                )
        db.session.add(teacher)
        db.session.commit()

        flash("Teacher registered")
        return redirect(url_for("teachers_list"))

    return render_template("admin/register_teacher.html")


@app.route("/teachers")
@login_required
def teachers_list():

    if current_user.role != "admin":
        return "Unauthorized", 403

    teachers = Teacher.query.all()

    return render_template("admin/teachers_list.html", teachers=teachers)


@app.route("/assign-teacher", methods=["GET", "POST"])
@login_required
def assign_teacher():

    if current_user.role != "admin":
        return "Unauthorized", 403

    teachers = Teacher.query.all()
    subjects = Subject.query.all()
    classes = SchoolClass.query.all()

    if request.method == "POST":

        teacher_id = request.form["teacher_id"]
        subject_id = request.form["subject_id"]
        class_id = request.form["class_id"]

        assignment = TeacherAssignment(
                teacher_id=teacher_id,
                subject_id=subject_id,
                class_id=class_id
                )
        db.session.add(assignment)
        db.session.commit()

        flash("Teacher assigned successfully")

    assignments = TeacherAssignment.query.all()

    return render_template(
            "admin/assign_teacher.html",
            teachers=teachers,
            subjects=subjects,
            classes=classes,
            assignments=assignments
            )


@app.route("/enter-results", methods=["GET", "POST"])
@login_required
def enter_results():

    if current_user.role != "teacher":
        return "Unauthorized", 403

    classes = SchoolClass.query.all()
    subjects = Subject.query.all()
    exams = Exam.query.all()

    if request.method == "POST":

        class_id = request.form["class_id"]
        subject_id = request.form["subject_id"]
        exam_id = request.form["exam_id"]

        students = Student.query.filter_by(class_id=class_id).all()

        for student in students:
            marks = request.form.get(f"marks_{student.id")

            if marks:
                result = Result(
                        student_id=student.id,
                        subject_id=subject_id,
                        exam_id=exam_id,
                        marks=float(marks)
                        )
                
                db.session.commit()

                flash("Results saved successfully")

                return redirect(url_for("enter_results"))

            return render_template(
                    "teacher/select_results.html",
                    classes=classes,
                    subjects=subjects,
                    exams=exams
                    )


@app.route("/enter-results/<int:class_id>/<int:subject_id>/<int:exam_id>", methods=["GET", "POST"])
@login_required
def enter_marks(class_id, subject_id, exam_id):

    students = Student.query.filter_by(class_id=class_id).all()

    if request.method == "POST":

        for student in students:
            marks = request.form.get(f"marks_{student.id}")

            if marks:

                existing = Result.query.filter_by(
                        student_id=student.id,
                        subject_id=subject_id,
                        exam_id=exam_id
                        ).first()
                
                if not existing:
                     result = Result(
                             student_id=student.id,
                             subject_id=subject_id,
                             exam_id=exam_id,
                             marks=float(marks)
                             )

                db.session.add(result)

            db.session.commit()
            flash("Marks saved")

            return redirect(url_for("dashboard"))

        return render_template(
                "teacher/enter_marks.html",
                students=students
                )


@app.route("/report-card/<int:student_id>/<int:term_id>")
@login_required
def report_card(student_id, term_id):

    student = Student.query.get_or_404(student_id)

    results = Result.query.join(Exam)\
            .join(Term)\
            .filter(
                    Result.student_id == student_id,
                    Term.id == term_id
                    ).all()

            report = []
            total_marks = 0

            for r in results:
                grade = calculate_grade(r.marks)

                report.append({
                    "subject": r.subject.name,
                    "marks": r.marks,
                    "grade": grade
                    })

                total_marks += r.marks

            average = 0
            final_grade = "N/A"

            if results:
                average = total_marks / len(results)
                final_grade = calculate_grade(average)

            return render_template(
                    "report_card.html",
                    student=student,
                    report=report,
                    total=total_marks,
                    average=round(average,2),
                    final_grade=final_grade
                    )



@app.route("/report-card/pdf/<int:student_id>/<int:term_id>")
@login_required
def report_card_pdf(student_id, term_id):

        student = Student.query.get_or_404(student_id)

            results = Result.query.join(Exam)\
                    .join(Term)\
                    .filter(
                            Result.student_id == student_id,
                            Term.id == term_id
                            ).all()
                    
            report = []
            total_marks = 0

            for r in results:
                grade = calculate_grade(r.marks)

                report.append({
                    "subject": r.subject.name,
                    "marks": r.marks,
                    "grade": grade
                    })

                total_marks += r.marks

            average = 0
            final_grade = "N/A"

            if results:

                average = total_marks / len(results)
                final_grade = calculate_grade(average)

            html = render_template(
                    "report_card_pdf.html",
                    student=student,
                    report=report,
                    total=total_marks,
                    average=round(average,2),
                    final_grade=final_grade
                    )

            pdf = HTML(string=html).write_pdf()

            response = make_response(pdf)
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = "inline; filename=report_card.pdf"

            return response


@app.route("/teacher/upload-material", methods=["GET", "POST"])
@login_required
def upload_material():

    if current_user.role != "teacher":
        return "Unauthorized", 403

    classes = SchoolClass.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":

        title = request.form["title"]
        class_id = request.form["class_id"]
        subject_id = request.form["subject_id"]

        file = request.files["file"]
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        material = Material(
                title=title,
                file_path=path,
                teacher_id=current_user.id,
                class_id=class_id,
                subject_id=subject_id
                )

        db.session.add(material)
        db.session.commit()

        flash("Material uploaded successfully")

    return render_template(
            "teacher/upload_material.html",
            classes=classes,
            subjects=subjects
            )


@app.route("/student/materials")
@login_required
def student_materials():

    if current_user.role != "student":
        return "Unauthorized", 403

    student = Student.query.filter_by(
            admission_no=current_user.username
            ).first()

    materials = Material.query.filter_by(
            class_id=student.class_id
            ).all()

    return render_template(
            "student/materials.html",
            materials=materials
            )


@app.route("/teacher/create-assignment", methods=["GET", "POST"])
@login_required
def create_assignment():

    classes = SchoolClass.query.all()
    subjects = Subject.query.all()

    if request.method == "POST":

        assignment = Assignment(
                title=request.form["title"],
                description=request.form["description"],
                class_id=request.form["class_id"],
                subject_id=request.form["subject_id"],
                teacher_id=current_user.id,
                due_date=request.form["due_date"]
                )

        db.session.add(assignment)
        db.session.commit()

        flash("Assignment created")

    return render_template(
            "teacher/create_assignment.html",
            classes=classes,
            subjects=subjects
            )


@app.route("/student/assignments")
@login_required
def student_assignments():

    student = Student.query.filter_by(
            admission_no=current_user.username
            ).first()

    assignments = Assignment.query.filter_by(
            class_id=student.class_id
            ).all()

    return render_template(
            "student/assignments.html",
            assignments=assignments
            )


@app.route("/student/submit/<int:assignment_id>", methods=["GET", "POST"])
@login_required
def submit_assignment(assignment_id):

    assignment = Assignment.query.get_or_404(assignment_id)

    student = Student.query.filter_by(
            admission_no=current_user.username
            ).first()

    if request.method == "POST":

        file = request.files["file"]
        filename = secure_filename(file.filename)
        path = os.path.join(ASSIGNMENT_UPLOAD, filename)
        file.save(path)

        submission = Submission(
                assignment_id=assignment.id,
                student_id=student.id,
                file_path=path
                )

        db.session.add(submission)
        db.session.commit()

        flash("Assignment submitted successfully")
        return redirect(url_for("student_assignments"))

    return render_template(
            "student/submit_assignment.html",
            assignment=assignment
            )


@app.route("/teacher/submissions/<int:assignment_id>")
@login_required
def view_submissions(assignment_id):

    submissions = Submission.query.filter_by(
            assignment_id=assignment_id
            ).all()

    return render_template(
            "teacher/submissions.html",
            submissions=submissions
            )
        

