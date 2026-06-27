"""
app.py — SaaS application factory
"""
import os
from flask import Flask
from config import Config
from extensions import db, login_manager, csrf, limiter, mail
from models import User, School
from tenant import init_tenant
from werkzeug.security import generate_password_hash


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)


    # ── Extensions ────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
    return User.query.get(int(user_id))

    
    # ── Multi-tenant middleware ────────────────────────────────────
    init_tenant(app)

    
    # ── Blueprints ────────────────────────────────────────────────
    from blueprints.onboarding import onboarding
    from blueprints.billing    import billing
    from blueprints.superadmin import superadmin
    from blueprints.auth       import auth
    from blueprints.admin      import admin
    from blueprints.teacher    import teacher
    from blueprints.student    import student
    from blueprints.parent     import parent

    app.register_blueprint(onboarding)   # public routes + registration
    app.register_blueprint(billing)
    app.register_blueprint(superadmin)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(teacher)
    app.register_blueprint(student)
    app.register_blueprint(parent)

    
    # ── Upload directories ─────────────────────────────────────────
    for folder in [
            app.config["UPLOAD_FOLDER"],
            app.config["ASSIGNMENT_UPLOAD"],
            app.config["ANNOUNCEMENT_UPLOAD"],
            ]:
        os.makedirs(folder, exist_ok=True)


    # ── DB init + superadmin ───────────────────────────────────────
    with app.app_context():
        db.create_all()
        _create_superadmin(app)


    # ── Scheduler ─────────────────────────────────────────────────
    _start_scheduler(app)

    return app


def _create_superadmin(app):
    sa_email = app.config["SUPERADMIN_EMAIL"]
    if not User.query.filter_by(role="superadmin").first():
        password = os.environ.get("ADMIN_PASSWORD", "SuperAdmin123!")
        sa = User(
                school_id=None,
                username="superadmin",
                email=sa_email,
                password_hash=generate_password_hash(password),
                role="superadmin",
                is_verified=True,
                )
        db.session.add(sa)
        db.session.commit()
        print(f"✅ Superadmin created: {sa_email}")


def _start_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler


        def run_fee_reminders():
            with app.app_context():
                from utils import check_fee_reminders
                # check_fee_reminders iterates all schools
                from models import School
                for school in School.query.filter_by(is_active=True).all():
                    _run_reminders_for_school(school)


        def _run_reminders_for_school(school):
            from models import Student, User, Term
            from utils import calculate_balance, send_notification
            students = Student.query.filter_by(school_id=school.id).all()
            terms    = Term.query.filter_by(school_id=school.id, is_active=True).all()
            for student in students:
                user = User.query.filter_by(school_id=school.id,
                        username=student.admission_no).first()
                if not user:
                    continue
                for term in terms:
                    balance = calculate_balance(student.id, term.id, school.id)
                    if balance > 0:
                        send_notification(
                                user.id, school.id,
                                f"Outstanding balance of K{balance:.2f} for {term.name}",
                                "fee"
                                )
        db.session.commit()


    scheduler = BackgroundScheduler()
    scheduler.add_job(run_fee_reminders, "interval", weeks=1)
    scheduler.start()
    print("✅ Fee reminder scheduler started.")
    except ImportError:
        print("⚠️  APScheduler not installed.")



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
