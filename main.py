from flask import Blueprint, render_template, session, redirect, url_for
from ..database import get_db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    db = get_db()
    total_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE is_approved=1 AND is_active=1").fetchone()[0]
    total_companies = db.execute("SELECT COUNT(*) FROM companies WHERE is_approved=1").fetchone()[0]
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_placed = db.execute("SELECT COUNT(*) FROM applications WHERE status='Hired'").fetchone()[0]
    recent_jobs = db.execute("""
        SELECT j.*, c.name as company_name, c.logo_path
        FROM jobs j JOIN companies c ON j.company_id = c.id
        WHERE j.is_approved=1 AND j.is_active=1
        ORDER BY j.created_at DESC LIMIT 6
    """).fetchall()
    return render_template(
        "landing.html",
        total_jobs=total_jobs,
        total_companies=total_companies,
        total_students=total_students,
        total_placed=total_placed,
        recent_jobs=recent_jobs,
    )


@main_bp.route("/dashboard")
def dashboard_redirect():
    role = session.get("role")
    if role == "student":
        return redirect(url_for("student.dashboard"))
    elif role == "company":
        return redirect(url_for("company.dashboard"))
    elif role == "admin":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("main.index"))
