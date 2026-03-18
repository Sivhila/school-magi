from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

CREATE DATABASE school_db;


#Users

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


#Classes

class SchoolClass(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    students = db.relationship(
            "Student",
            backref="school_class",
            cascade="all, delete",
            lazy=True
            )

#Students

class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    admission_no = db.Column(db.String(50), unique=True, nullable=False)
    gender = db.Column(db.String(10))
    parent_phone = db.Column(db.String(20))

    class_id = db.Column(
            db.Integer,
            db.ForeignKey("classes.id", ondelete="SET NULL")
            )

    attendence_records = db.relationship("Attendance", backref="student", lazy=True)
    results = db.relationship("Result", backref="student", lazy=True)
    fees = db.relationship("Fee", backref="student", lazy=True)

#Teachers

class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    subject = db.Column(db.string(100))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#Subjects

class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


#Attendance

class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
            db.Integer,
            db.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False
            )

    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(10), nullable=False)

    __table_args__ = (
            db.UniqueConstraint('student_id', 'date', name='unique_daily_attendance'),
            )


#Exam Results

class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
            db.Integer,
            db.ForegnKey("students.id", ondelete="CASCADE")
            )
    subject_id = db.Column(
            db.Integer,
            db.ForeignKey("subjects.id", ondelete="CASCADE")
            )

    marks = db.Column(db.Float, nullable=False)


#Fees

class Fee(db.Model):
    __tablename__ = "fees"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
            db.Integer,
            db.ForeignKey("students.id", ondelete="CASCADE")
            )

    amount_paid = db.Column(db.Numeric(10,2), nullable=False)
    date_paid = db.Column(db.Date, default=datetime.utcnow)


# Materials

class Material(db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200, nullable=False))
    file_path = db.Column(db.String(300, nullable=False))

    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))

    class_id = db.Column(
            db.Integer,
            db.ForeignKey("classes.id", ondelete="CASCADE")
            )

    subject_id = db.Column(
            db.Integer,
            db.ForeignKey("subjects.id", ondelete="CASCADE")
            )

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


#Announcements

class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)

    message = db.Column(db.Text, nullable=False)

    class_id = db.Column(
            db.Integer,
            db.ForeignKey("classes.id" ondelete="CASCADE")
            )
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


#Assignment

class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"))
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"))

    due_date = db.Column(db.Date)

    subject = db.relationship("Subject")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Academic Year

class AcademicYear(db.Model):
    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True)

    year = db.Column(db.String(20), unique=True, nullable=False)



# Term

class Term(db.Model):
    __tablename__ = "terms"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    academic_year_id = db.Column(
            db.Integer,
            db.ForeignKey("academic_year.id")
            )

    academic_year = db.relationship("AcademicYear")


# Exam

class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    term_id = db.Column(
            db.Integer,
            db.ForeignKey("terms.id")
            )
    
    term = db.relationship("Term")



# Result

class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
            db.Integer,
            db.ForeignKey("students.id")
            )

    subject_id = db.Column(
            db.Integer,
            db.ForeignKey("subjects.id")
            )

    exam_id = db.Column(
            db.Integer,
            db.ForeignKey("exams.id")
            )

    marks = db.Column(db.Float, nullable=False)

    student = db.relationship("Student")
    subject = db.relationship("Subject")
    exam = db.relationship("Exam")



# Grade

class Grade(db.Model):
    __tablename__ = "grades"

    id = db.Column(db.Integer, primary_key=True)
    grade = db.Column(db.String(5))
    min_score = db.Column(db.Integer)
    max_score = db.Column(db.Integer)


class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)

    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))

    file_path = db.Column(db.String(300))

    submitted_at = db.Column(db.Datetime, default=datetime.utcnow)

    marks = db.Column(db.Float)
    feedback = db.Column(db.Text)

    assignment = db.relationship("Assignment")
    student = db.relationship("Student")


