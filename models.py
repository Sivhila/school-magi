"""
models.py — Multi-tenant SaaS schema
Every resource table carries school_id so one database serves many schools.
""" 
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ══════════════════════════════════════════════════════════════════
#  SAAS LAYER
# ══════════════════════════════════════════════════════════════════

class School(db.Model):
        """One row = one paying/trialling customer (a school)."""
        __tablename__ = "schools"

        id           = db.Column(db.Integer, primary_key=True)
        name         = db.Column(db.String(150), nullable=False)
        subdomain    = db.Column(db.String(50), unique=True, nullable=False)  # stmarys → stmarys.yoursaas.com
        email        = db.Column(db.String(150), nullable=False)              # admin contact email
        phone        = db.Column(db.String(30))
        address      = db.Column(db.Text)
        logo_url     = db.Column(db.String(300))

        # Billing
        plan                   = db.Column(db.String(20), default="free")    # free/starter/growth/enterprise
        stripe_customer_id     = db.Column(db.String(100))
        stripe_subscription_id = db.Column(db.String(100))
        billing_cycle          = db.Column(db.String(10), default="monthly") # monthly/yearly
        trial_ends_at          = db.Column(db.DateTime)
        subscription_ends_at   = db.Column(db.DateTime)

        # Status
        is_active        = db.Column(db.Boolean, default=True)
        is_email_verified= db.Column(db.Boolean, default=False)
        created_at       = db.Column(db.DateTime, default=datetime.utcnow)
        def get_url(self, protocol="https", base_domain="yoursaas.com"):
            return f"{protocol}://{self.subdomain}.{base_domain}"

        def is_on_trial(self):
            return self.trial_ends_at and datetime.utcnow() < self.trial_ends_at

        def subscription_active(self):
            if self.plan == "free":
                return True
            if self.is_on_trial():
                return True
            if self.subscription_ends_at and datetime.utcnow() < self.subscription_ends_at:
                return True
            return False


class Subscription(db.Model):
    """Stripe subscription history for a school."""
     __tablename__ = "subscriptions"

     id                     = db.Column(db.Integer, primary_key=True)
     school_id              = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
     stripe_subscription_id = db.Column(db.String(100))
     stripe_invoice_id      = db.Column(db.String(100))
     plan                   = db.Column(db.String(20))
     billing_cycle          = db.Column(db.String(10))
     amount                 = db.Column(db.Float)
     currency               = db.Column(db.String(10), default="usd")
     status                 = db.Column(db.String(30))   # active/canceled/past_due
     period_start           = db.Column(db.DateTime)
     period_end             = db.Column(db.DateTime)
     created_at             = db.Column(db.DateTime, default=datetime.utcnow)

     school = db.relationship("School", backref="subscriptions")


# ══════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    school_id     = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)  # NULL = superadmin
    username      = db.Column(db.String(50), nullable=False)
    email         = db.Column(db.String(150))
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # superadmin/admin/teacher/student/parent
    student_id    = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)
    is_verified   = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
            db.UniqueConstraint("school_id", "username", name="uq_school_username"),

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_superadmin(self):
        return self.role == "superadmin"

    school = db.relationship("School", backref="users", foreign_keys=[school_id])


# ══════════════════════════════════════════════════════════════════
#  SCHOOL DATA  (all carry school_id)
# ══════════════════════════════════════════════════════════════════

class SchoolClass(db.Model):
    __tablename__ = "classes"

    id               = db.Column(db.Integer, primary_key=True)
    school_id        = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name             = db.Column(db.String(50), nullable=False)
    capacity         = db.Column(db.Integer)
    class_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))

    students = db.relationship("Student", backref="school_class", cascade="all, delete", lazy=True)
    school   = db.relationship("School", backref="classes")


class Student(db.Model):
    __tablename__ = "students"

    id           = db.Column(db.Integer, primary_key=True)
    school_id    = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id"))
    admission_no = db.Column(db.String(50), nullable=False)
    first_name   = db.Column(db.String(50), nullable=False)
    last_name    = db.Column(db.String(50), nullable=False)
    dob          = db.Column(db.Date)
    gender       = db.Column(db.String(10))
    address      = db.Column(db.Text)
    parent_id    = db.Column(db.Integer, db.ForeignKey("parents.id"))
    class_id     = db.Column(db.Integer, db.ForeignKey("classes.id"))
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("school_id", "admission_no", name="uq_school_admission"),
        )

    attendance_records = db.relationship("Attendance", backref="student", lazy=True)

    results            = db.relationship("Result",     backref="student", lazy=True)

    school             = db.relationship("School",     backref="students")


class Teacher(db.Model):
    __tablename__ = "teachers"

    id                     = db.Column(db.Integer, primary_key=True)
    school_id              = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    user_id                = db.Column(db.Integer, db.ForeignKey("users.id"))
    staff_no               = db.Column(db.String(20), nullable=False)
    first_name             = db.Column(db.String(50), nullable=False)
    last_name              = db.Column(db.String(50), nullable=False)
    subject_specialization = db.Column(db.String(100))
    phone                  = db.Column(db.String(20))
    hire_date              = db.Column(db.Date)

    school = db.relationship("School", backref="teachers")


class Parent(db.Model):
    __tablename__ = "parents"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    first_name = db.Column(db.String(50), nullable=False)
    last_name  = db.Column(db.String(50), nullable=False)
    phone      = db.Column(db.String(20))
    email      = db.Column(db.String(100))
    address    = db.Column(db.Text)
    
    school = db.relationship("School", backref="parents")


class ParentStudent(db.Model):
    __tablename__ = "parent_students"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    parent_id  = db.Column(db.Integer, db.ForeignKey("parents.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    
    parent  = db.relationship("Parent")
    student = db.relationship("Student")


class Subject(db.Model):
    __tablename__ = "subjects"

    id        = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name      = db.Column(db.String(100), nullable=False)
    code      = db.Column(db.String(20))
    school = db.relationship("School", backref="subjects")


class Attendance(db.Model):
    __tablename__ = "attendance"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    class_id   = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    status     = db.Column(db.String(20), nullable=False)

    __table_args__ = (
            db.UniqueConstraint("school_id", "student_id", "date", name="uq_school_attendance"),
            )


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"

    id        = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id  = db.Column(db.Integer, db.ForeignKey("classes.id"))
    term_id   = db.Column(db.Integer, db.ForeignKey("terms.id"))
    amount    = db.Column(db.Float, nullable=False)
    
    school_class = db.relationship("SchoolClass")
    term         = db.relationship("Term")


class Payment(db.Model):
    __tablename__ = "payments"

    id             = db.Column(db.Integer, primary_key=True)
    school_id      = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id     = db.Column(db.Integer, db.ForeignKey("students.id"))
    term_id        = db.Column(db.Integer, db.ForeignKey("terms.id"))
    amount_paid    = db.Column(db.Float)
    payment_date   = db.Column(db.DateTime, default=datetime.utcnow)
    reference      = db.Column(db.String(100))
    bank_reference = db.Column(db.String(100))

    student = db.relationship("Student")
    term    = db.relationship("Term")


class Material(db.Model):
    __tablename__ = "materials"

    id          = db.Column(db.Integer, primary_key=True)
    school_id   = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    title       = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename    = db.Column(db.String(255), nullable=False)
    class_id    = db.Column(db.Integer, db.ForeignKey("classes.id"))
    subject_id  = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    teacher_id  = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class Announcement(db.Model):
    __tablename__ = "announcements"

    id          = db.Column(db.Integer, primary_key=True)
    school_id   = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    message     = db.Column(db.Text, nullable=False)
    class_id    = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"))
    priority    = db.Column(db.String(20), default="Normal")
    expiry_date = db.Column(db.Date)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    school_class = db.relationship("SchoolClass")


class Assignment(db.Model):
    __tablename__ = "assignments"

    id          = db.Column(db.Integer, primary_key=True)
    school_id   = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    title       = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    teacher_id  = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    subject_id  = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    class_id    = db.Column(db.Integer, db.ForeignKey("classes.id"))
    deadline    = db.Column(db.DateTime)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    subject = db.relationship("Subject")


class Submission(db.Model):
    __tablename__ = "submissions"

    id            = db.Column(db.Integer, primary_key=True)
    school_id     = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    student_id    = db.Column(db.Integer, db.ForeignKey("students.id"))
    file_path     = db.Column(db.String(300))
    submitted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    marks         = db.Column(db.Float)
    feedback      = db.Column(db.Text)
    
    assignment = db.relationship("Assignment")
    student    = db.relationship("Student")


class AcademicYear(db.Model):
    __tablename__ = "academic_years"

    id        = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    year      = db.Column(db.String(20), nullable=False)
    


class Term(db.Model):
    __tablename__ = "terms"

    id               = db.Column(db.Integer, primary_key=True)
    school_id        = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name             = db.Column(db.String(50), nullable=False)
    start_date       = db.Column(db.Date, nullable=False)
    end_date         = db.Column(db.Date, nullable=False)
    is_active        = db.Column(db.Boolean, default=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"))
    academic_year = db.relationship("AcademicYear")


class Exam(db.Model):
    __tablename__ = "exams"

    id        = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    name      = db.Column(db.String(100), nullable=False)
    term_id   = db.Column(db.Integer, db.ForeignKey("terms.id"))
    date      = db.Column(db.Date)
    term = db.relationship("Term")


class Result(db.Model):
    __tablename__ = "results"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    exam_id    = db.Column(db.Integer, db.ForeignKey("exams.id"))
    marks      = db.Column(db.Float, nullable=False)
    
    subject = db.relationship("Subject")
    exam    = db.relationship("Exam")


class Timetable(db.Model):
    __tablename__ = "timetables"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    class_id   = db.Column(db.Integer, db.ForeignKey("classes.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    day        = db.Column(db.String(20))
    start_time = db.Column(db.String(10))
    end_time   = db.Column(db.String(10))
    
    subject      = db.relationship("Subject")
    teacher      = db.relationship("Teacher")
    school_class = db.relationship("SchoolClass")


class Notification(db.Model):
    __tablename__ = "notifications"

    id         = db.Column(db.Integer, primary_key=True)
    school_id  = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"))
    message    = db.Column(db.Text, nullable=False)
    type       = db.Column(db.String(50))
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
