import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from ..database import get_db
from ..utils.decorators import role_required
from ..utils.helpers import notify

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_companies = db.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    pending_companies = db.execute("SELECT COUNT(*) FROM companies WHERE is_approved=0").fetchone()[0]
    total_jobs = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    pending_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE is_approved=0").fetchone()[0]
    total_apps = db.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    total_hired = db.execute("SELECT COUNT(*) FROM applications WHERE status='Hired'").fetchone()[0]

    recent_students = db.execute("SELECT * FROM students ORDER BY created_at DESC LIMIT 5").fetchall()
    recent_companies = db.execute("SELECT * FROM companies ORDER BY created_at DESC LIMIT 5").fetchall()
    pending_co_list = db.execute("SELECT * FROM companies WHERE is_approved=0 ORDER BY created_at DESC").fetchall()
    pending_job_list = db.execute("""
        SELECT j.*, c.name as company_name FROM jobs j
        JOIN companies c ON j.company_id=c.id
        WHERE j.is_approved=0 ORDER BY j.created_at DESC
    """).fetchall()

    return render_template("admin/dashboard.html",
        total_students=total_students, total_companies=total_companies,
        pending_companies=pending_companies, total_jobs=total_jobs,
        pending_jobs=pending_jobs, total_apps=total_apps, total_hired=total_hired,
        recent_students=recent_students, recent_companies=recent_companies,
        pending_co_list=pending_co_list, pending_job_list=pending_job_list)


@admin_bp.route("/companies")
@role_required("admin")
def manage_companies():
    db = get_db()
    status = request.args.get("status", "all")
    if status == "pending":
        companies = db.execute("SELECT * FROM companies WHERE is_approved=0 ORDER BY created_at DESC").fetchall()
    elif status == "approved":
        companies = db.execute("SELECT * FROM companies WHERE is_approved=1 ORDER BY created_at DESC").fetchall()
    else:
        companies = db.execute("SELECT * FROM companies ORDER BY created_at DESC").fetchall()
    return render_template("admin/companies.html", companies=companies, status=status)


@admin_bp.route("/companies/<int:cid>/approve", methods=["POST"])
@role_required("admin")
def approve_company(cid):
    db = get_db()
    db.execute("UPDATE companies SET is_approved=1 WHERE id=?", (cid,))
    db.commit()
    company = db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    notify(db, cid, "company", "Your company account has been approved! You can now post jobs.")
    flash(f"Company '{company['name']}' approved.", "success")
    return redirect(url_for("admin.manage_companies"))


@admin_bp.route("/companies/<int:cid>/reject", methods=["POST"])
@role_required("admin")
def reject_company(cid):
    db = get_db()
    company = db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    db.execute("DELETE FROM companies WHERE id=?", (cid,))
    db.commit()
    flash(f"Company '{company['name']}' rejected and removed.", "info")
    return redirect(url_for("admin.manage_companies"))


@admin_bp.route("/jobs")
@role_required("admin")
def manage_jobs():
    db = get_db()
    status = request.args.get("status", "all")
    if status == "pending":
        jobs = db.execute("""
            SELECT j.*, c.name as company_name FROM jobs j
            JOIN companies c ON j.company_id=c.id
            WHERE j.is_approved=0 ORDER BY j.created_at DESC
        """).fetchall()
    elif status == "approved":
        jobs = db.execute("""
            SELECT j.*, c.name as company_name FROM jobs j
            JOIN companies c ON j.company_id=c.id
            WHERE j.is_approved=1 ORDER BY j.created_at DESC
        """).fetchall()
    else:
        jobs = db.execute("""
            SELECT j.*, c.name as company_name FROM jobs j
            JOIN companies c ON j.company_id=c.id
            ORDER BY j.created_at DESC
        """).fetchall()
    return render_template("admin/jobs.html", jobs=jobs, status=status)


@admin_bp.route("/jobs/<int:jid>/approve", methods=["POST"])
@role_required("admin")
def approve_job(jid):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    db.execute("UPDATE jobs SET is_approved=1 WHERE id=?", (jid,))
    db.commit()
    notify(db, job["company_id"], "company", f"Your job '{job['title']}' has been approved and is now live.")
    flash(f"Job '{job['title']}' approved.", "success")
    return redirect(url_for("admin.manage_jobs"))


@admin_bp.route("/jobs/<int:jid>/reject", methods=["POST"])
@role_required("admin")
def reject_job(jid):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
    notify(db, job["company_id"], "company", f"Your job '{job['title']}' was rejected by admin.")
    db.execute("DELETE FROM jobs WHERE id=?", (jid,))
    db.commit()
    flash(f"Job '{job['title']}' rejected.", "info")
    return redirect(url_for("admin.manage_jobs"))


@admin_bp.route("/students")
@role_required("admin")
def manage_students():
    db = get_db()
    students = db.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    return render_template("admin/students.html", students=students)


@admin_bp.route("/students/<int:sid>/delete", methods=["POST"])
@role_required("admin")
def delete_student(sid):
    db = get_db()
    db.execute("DELETE FROM applications WHERE student_id=?", (sid,))
    db.execute("DELETE FROM notifications WHERE user_id=? AND user_role='student'", (sid,))
    db.execute("DELETE FROM students WHERE id=?", (sid,))
    db.commit()
    flash("Student deleted.", "info")
    return redirect(url_for("admin.manage_students"))


@admin_bp.route("/reports")
@role_required("admin")
def reports():
    db = get_db()
    # Applications per status
    status_data = db.execute("""
        SELECT status, COUNT(*) as count FROM applications GROUP BY status
    """).fetchall()
    # Jobs by type
    type_data = db.execute("""
        SELECT job_type, COUNT(*) as count FROM jobs WHERE is_approved=1 GROUP BY job_type
    """).fetchall()
    # Monthly registrations
    monthly_students = db.execute("""
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM students GROUP BY month ORDER BY month DESC LIMIT 12
    """).fetchall()
    return render_template("admin/reports.html",
        status_data=status_data, type_data=type_data, monthly_students=monthly_students)


@admin_bp.route("/reports/export")
@role_required("admin")
def export_report():
    db = get_db()
    rows = db.execute("""
        SELECT s.name, s.email, j.title as job, c.name as company, a.status, a.applied_at
        FROM applications a
        JOIN students s ON a.student_id=s.id
        JOIN jobs j ON a.job_id=j.id
        JOIN companies c ON j.company_id=c.id
        ORDER BY a.applied_at DESC
    """).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Email", "Job Title", "Company", "Status", "Applied At"])
    for row in rows:
        writer.writerow(list(row))

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications_report.csv"}
    )
