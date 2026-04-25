from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..database import get_db
from ..utils.decorators import role_required
from ..utils.helpers import notify

company_bp = Blueprint("company", __name__)


@company_bp.route("/dashboard")
@role_required("company")
def dashboard():
    db = get_db()
    cid = session["user_id"]
    company = db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    total_jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE company_id=?", (cid,)).fetchone()[0]
    total_apps = db.execute("""
        SELECT COUNT(*) FROM applications a
        JOIN jobs j ON a.job_id=j.id WHERE j.company_id=?
    """, (cid,)).fetchone()[0]
    shortlisted = db.execute("""
        SELECT COUNT(*) FROM applications a
        JOIN jobs j ON a.job_id=j.id WHERE j.company_id=? AND a.status='Shortlisted'
    """, (cid,)).fetchone()[0]
    hired = db.execute("""
        SELECT COUNT(*) FROM applications a
        JOIN jobs j ON a.job_id=j.id WHERE j.company_id=? AND a.status='Hired'
    """, (cid,)).fetchone()[0]
    recent_apps = db.execute("""
        SELECT a.*, j.title, s.name as student_name, s.email as student_email
        FROM applications a
        JOIN jobs j ON a.job_id=j.id
        JOIN students s ON a.student_id=s.id
        WHERE j.company_id=?
        ORDER BY a.applied_at DESC LIMIT 5
    """, (cid,)).fetchall()
    jobs = db.execute("SELECT * FROM jobs WHERE company_id=? ORDER BY created_at DESC LIMIT 5", (cid,)).fetchall()
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id=? AND user_role='company' ORDER BY created_at DESC LIMIT 5",
        (cid,)
    ).fetchall()
    unread_count = db.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND user_role='company' AND is_read=0",
        (cid,)
    ).fetchone()[0]

    return render_template("company/dashboard.html",
        company=company, total_jobs=total_jobs, total_apps=total_apps,
        shortlisted=shortlisted, hired=hired, recent_apps=recent_apps,
        jobs=jobs, notifications=notifications, unread_count=unread_count)


@company_bp.route("/post-job", methods=["GET", "POST"])
@role_required("company")
def post_job():
    db = get_db()
    cid = session["user_id"]
    company = db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    if not company["is_approved"]:
        flash("Your company must be approved by admin before posting jobs.", "warning")
        return redirect(url_for("company.dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        requirements = request.form.get("requirements", "").strip()
        skills_required = request.form.get("skills_required", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-Time")
        salary = request.form.get("salary", "").strip()
        deadline = request.form.get("deadline", "").strip() or None

        if not all([title, description]):
            flash("Title and description are required.", "danger")
            return render_template("company/post_job.html")

        db.execute("""
            INSERT INTO jobs (company_id, title, description, requirements, skills_required,
                              location, job_type, salary, deadline)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (cid, title, description, requirements, skills_required, location, job_type, salary, deadline))
        db.commit()
        flash("Job posted! Awaiting admin approval.", "success")
        return redirect(url_for("company.my_jobs"))

    return render_template("company/post_job.html")


@company_bp.route("/jobs")
@role_required("company")
def my_jobs():
    db = get_db()
    cid = session["user_id"]
    jobs = db.execute("""
        SELECT j.*, (SELECT COUNT(*) FROM applications a WHERE a.job_id=j.id) as app_count
        FROM jobs j WHERE j.company_id=? ORDER BY j.created_at DESC
    """, (cid,)).fetchall()
    return render_template("company/my_jobs.html", jobs=jobs)


@company_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@role_required("company")
def edit_job(job_id):
    db = get_db()
    cid = session["user_id"]
    job = db.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, cid)).fetchone()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("company.my_jobs"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        requirements = request.form.get("requirements", "").strip()
        skills_required = request.form.get("skills_required", "").strip()
        location = request.form.get("location", "").strip()
        job_type = request.form.get("job_type", "Full-Time")
        salary = request.form.get("salary", "").strip()
        deadline = request.form.get("deadline", "").strip() or None
        is_active = 1 if request.form.get("is_active") else 0

        db.execute("""
            UPDATE jobs SET title=?, description=?, requirements=?, skills_required=?,
            location=?, job_type=?, salary=?, deadline=?, is_active=?, is_approved=0
            WHERE id=? AND company_id=?
        """, (title, description, requirements, skills_required, location, job_type, salary, deadline, is_active, job_id, cid))
        db.commit()
        flash("Job updated! It will require re-approval.", "info")
        return redirect(url_for("company.my_jobs"))

    return render_template("company/post_job.html", job=job, editing=True)


@company_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@role_required("company")
def delete_job(job_id):
    db = get_db()
    cid = session["user_id"]
    db.execute("DELETE FROM jobs WHERE id=? AND company_id=?", (job_id, cid))
    db.commit()
    flash("Job deleted.", "info")
    return redirect(url_for("company.my_jobs"))


@company_bp.route("/applicants/<int:job_id>")
@role_required("company")
def applicants(job_id):
    db = get_db()
    cid = session["user_id"]
    job = db.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, cid)).fetchone()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("company.my_jobs"))
    apps = db.execute("""
        SELECT a.*, s.name as student_name, s.email as student_email, s.phone, s.skills,
               s.education, s.resume_path, s.profile_score
        FROM applications a JOIN students s ON a.student_id=s.id
        WHERE a.job_id=?
        ORDER BY a.applied_at DESC
    """, (job_id,)).fetchall()
    return render_template("company/applicants.html", job=job, applicants=apps)


@company_bp.route("/applicants/<int:app_id>/status", methods=["POST"])
@role_required("company")
def update_status(app_id):
    db = get_db()
    status = request.form.get("status")
    allowed = ["Applied", "Shortlisted", "Rejected", "Hired"]
    if status not in allowed:
        flash("Invalid status.", "danger")
        return redirect(request.referrer or url_for("company.dashboard"))

    app = db.execute("""
        SELECT a.*, j.title, j.company_id, s.id as student_id
        FROM applications a JOIN jobs j ON a.job_id=j.id JOIN students s ON a.student_id=s.id
        WHERE a.id=?
    """, (app_id,)).fetchone()
    if not app or app["company_id"] != session["user_id"]:
        flash("Not found.", "danger")
        return redirect(url_for("company.dashboard"))

    db.execute("UPDATE applications SET status=? WHERE id=?", (status, app_id))
    db.commit()
    notify(db, app["student_id"], "student",
           f"Your application for '{app['title']}' has been updated to: {status}.")
    flash(f"Status updated to {status}.", "success")
    return redirect(request.referrer or url_for("company.dashboard"))


@company_bp.route("/applicants/<int:app_id>/interview", methods=["GET", "POST"])
@role_required("company")
def schedule_interview(app_id):
    db = get_db()
    app_row = db.execute("""
        SELECT a.*, j.title, j.company_id, s.name as student_name, s.email as student_email
        FROM applications a JOIN jobs j ON a.job_id=j.id JOIN students s ON a.student_id=s.id
        WHERE a.id=?
    """, (app_id,)).fetchone()
    if not app_row or app_row["company_id"] != session["user_id"]:
        flash("Not found.", "danger")
        return redirect(url_for("company.dashboard"))

    if request.method == "POST":
        scheduled_at = request.form.get("scheduled_at")
        mode = request.form.get("mode", "Online")
        location_link = request.form.get("location_link", "").strip()
        notes = request.form.get("notes", "").strip()

        existing = db.execute("SELECT id FROM interviews WHERE application_id=?", (app_id,)).fetchone()
        if existing:
            db.execute("""
                UPDATE interviews SET scheduled_at=?, mode=?, location_link=?, notes=?
                WHERE application_id=?
            """, (scheduled_at, mode, location_link, notes, app_id))
        else:
            db.execute("""
                INSERT INTO interviews (application_id, scheduled_at, mode, location_link, notes)
                VALUES (?,?,?,?,?)
            """, (app_id, scheduled_at, mode, location_link, notes))
        db.commit()
        notify(db, app_row["student_id"], "student",
               f"Interview scheduled for '{app_row['title']}' on {scheduled_at} ({mode}).")
        db.execute("UPDATE applications SET status='Shortlisted' WHERE id=?", (app_id,))
        db.commit()
        flash("Interview scheduled!", "success")
        return redirect(url_for("company.applicants", job_id=app_row["job_id"]))

    existing_interview = db.execute("SELECT * FROM interviews WHERE application_id=?", (app_id,)).fetchone()
    return render_template("company/interview.html", application=app_row, interview=existing_interview)


@company_bp.route("/profile", methods=["GET", "POST"])
@role_required("company")
def profile():
    db = get_db()
    cid = session["user_id"]
    company = db.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()

    if request.method == "POST":
        industry = request.form.get("industry", "").strip()
        location = request.form.get("location", "").strip()
        website = request.form.get("website", "").strip()
        about = request.form.get("about", "").strip()
        db.execute("""
            UPDATE companies SET industry=?, location=?, website=?, about=? WHERE id=?
        """, (industry, location, website, about, cid))
        db.commit()
        flash("Profile updated!", "success")
        return redirect(url_for("company.profile"))

    return render_template("company/profile.html", company=company)


@company_bp.route("/notifications")
@role_required("company")
def notifications():
    db = get_db()
    cid = session["user_id"]
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND user_role='company'", (cid,))
    db.commit()
    notifs = db.execute(
        "SELECT * FROM notifications WHERE user_id=? AND user_role='company' ORDER BY created_at DESC",
        (cid,)
    ).fetchall()
    return render_template("company/notifications.html", notifications=notifs)
