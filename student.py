import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..database import get_db
from ..utils.decorators import role_required
from ..utils.helpers import save_resume, calculate_profile_score, notify
from ..services.resume_analyzer import analyze_resume, recommend_jobs

student_bp = Blueprint("student", __name__)


@student_bp.route("/dashboard")
@role_required("student")
def dashboard():
    db = get_db()
    sid = session["user_id"]
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    applications = db.execute("""
        SELECT a.*, j.title, j.location, j.job_type, c.name as company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE a.student_id=?
        ORDER BY a.applied_at DESC LIMIT 5
    """, (sid,)).fetchall()
    notifications = db.execute(
        "SELECT * FROM notifications WHERE user_id=? AND user_role='student' ORDER BY created_at DESC LIMIT 5",
        (sid,)
    ).fetchall()
    unread_count = db.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND user_role='student' AND is_read=0",
        (sid,)
    ).fetchone()[0]

    # Stats
    total_applied = db.execute("SELECT COUNT(*) FROM applications WHERE student_id=?", (sid,)).fetchone()[0]
    shortlisted = db.execute("SELECT COUNT(*) FROM applications WHERE student_id=? AND status='Shortlisted'", (sid,)).fetchone()[0]
    hired = db.execute("SELECT COUNT(*) FROM applications WHERE student_id=? AND status='Hired'", (sid,)).fetchone()[0]

    # Recommendations
    all_jobs = db.execute("""
        SELECT j.*, c.name as company_name FROM jobs j
        JOIN companies c ON j.company_id = c.id
        WHERE j.is_approved=1 AND j.is_active=1
    """).fetchall()
    recommended = recommend_jobs(student["skills"], all_jobs)[:4]

    return render_template(
        "student/dashboard.html",
        student=student,
        applications=applications,
        notifications=notifications,
        unread_count=unread_count,
        total_applied=total_applied,
        shortlisted=shortlisted,
        hired=hired,
        recommended=recommended,
        profile_score=student["profile_score"] or calculate_profile_score(student),
    )


@student_bp.route("/profile", methods=["GET", "POST"])
@role_required("student")
def profile():
    db = get_db()
    sid = session["user_id"]
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "").strip()
        education = request.form.get("education", "").strip()
        bio = request.form.get("bio", "").strip()

        resume_file = request.files.get("resume")
        resume_path = student["resume_path"]
        if resume_file and resume_file.filename:
            saved = save_resume(resume_file)
            if saved:
                resume_path = saved
            else:
                flash("Invalid file type. Only PDF/DOC/DOCX allowed.", "danger")

        # Calculate score for updated profile
        mock = {"name": name, "email": student["email"], "phone": phone,
                "skills": skills, "education": education, "bio": bio, "resume_path": resume_path}
        score = calculate_profile_score(mock)

        db.execute("""
            UPDATE students SET name=?, phone=?, skills=?, education=?, bio=?, resume_path=?, profile_score=?
            WHERE id=?
        """, (name, phone, skills, education, bio, resume_path, score, sid))
        db.commit()
        session["name"] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=student)


@student_bp.route("/jobs")
@role_required("student")
def browse_jobs():
    db = get_db()
    sid = session["user_id"]
    search = request.args.get("q", "").strip()
    job_type = request.args.get("type", "")
    location = request.args.get("location", "").strip()

    query = """
        SELECT j.*, c.name as company_name, c.logo_path
        FROM jobs j JOIN companies c ON j.company_id = c.id
        WHERE j.is_approved=1 AND j.is_active=1
    """
    params = []
    if search:
        query += " AND (j.title LIKE ? OR j.skills_required LIKE ? OR c.name LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if job_type:
        query += " AND j.job_type=?"
        params.append(job_type)
    if location:
        query += " AND j.location LIKE ?"
        params.append(f"%{location}%")
    query += " ORDER BY j.created_at DESC"

    jobs = db.execute(query, params).fetchall()
    applied_ids = {r["job_id"] for r in db.execute("SELECT job_id FROM applications WHERE student_id=?", (sid,)).fetchall()}

    return render_template("student/jobs.html", jobs=jobs, applied_ids=applied_ids,
                           search=search, job_type=job_type, location=location)


@student_bp.route("/apply/<int:job_id>", methods=["GET", "POST"])
@role_required("student")
def apply(job_id):
    db = get_db()
    sid = session["user_id"]
    job = db.execute("""
        SELECT j.*, c.name as company_name FROM jobs j
        JOIN companies c ON j.company_id=c.id
        WHERE j.id=? AND j.is_approved=1
    """, (job_id,)).fetchone()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("student.browse_jobs"))

    already = db.execute("SELECT id FROM applications WHERE student_id=? AND job_id=?", (sid, job_id)).fetchone()
    if already:
        flash("You've already applied to this job.", "info")
        return redirect(url_for("student.browse_jobs"))

    if request.method == "POST":
        cover_letter = request.form.get("cover_letter", "").strip()
        db.execute(
            "INSERT INTO applications (student_id, job_id, cover_letter) VALUES (?,?,?)",
            (sid, job_id, cover_letter),
        )
        db.commit()
        # Notify company
        notify(db, job["company_id"], "company", f"New application for '{job['title']}' from {session['name']}.")
        flash("Application submitted successfully!", "success")
        return redirect(url_for("student.my_applications"))

    return render_template("student/apply.html", job=job)


@student_bp.route("/applications")
@role_required("student")
def my_applications():
    db = get_db()
    sid = session["user_id"]
    applications = db.execute("""
        SELECT a.*, j.title, j.location, j.job_type, j.skills_required, c.name as company_name
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE a.student_id=?
        ORDER BY a.applied_at DESC
    """, (sid,)).fetchall()
    return render_template("student/applications.html", applications=applications)


@student_bp.route("/resume-analyzer/<int:job_id>")
@role_required("student")
def resume_analyzer(job_id):
    db = get_db()
    sid = session["user_id"]
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    job = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("student.browse_jobs"))
    result = analyze_resume(student["resume_path"], job["skills_required"])
    return render_template("student/resume_analyzer.html", student=student, job=job, result=result)


@student_bp.route("/notifications")
@role_required("student")
def notifications():
    db = get_db()
    sid = session["user_id"]
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND user_role='student'", (sid,))
    db.commit()
    notifs = db.execute(
        "SELECT * FROM notifications WHERE user_id=? AND user_role='student' ORDER BY created_at DESC",
        (sid,)
    ).fetchall()
    return render_template("student/notifications.html", notifications=notifs)
