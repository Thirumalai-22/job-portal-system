from flask import Blueprint, jsonify, session
from ..database import get_db
from ..utils.decorators import login_required

api_bp = Blueprint("api", __name__)


@api_bp.route("/stats/admin")
def admin_stats():
    db = get_db()
    # Application status distribution
    status_rows = db.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall()
    status_labels = [r["status"] for r in status_rows]
    status_data = [r["cnt"] for r in status_rows]

    # Daily registrations last 30 days
    daily = db.execute("""
        SELECT strftime('%Y-%m-%d', created_at) as day, COUNT(*) as cnt
        FROM students GROUP BY day ORDER BY day DESC LIMIT 30
    """).fetchall()
    daily_labels = [r["day"] for r in reversed(daily)]
    daily_data = [r["cnt"] for r in reversed(daily)]

    # Job type distribution
    jtype = db.execute("""
        SELECT job_type, COUNT(*) as cnt FROM jobs WHERE is_approved=1 GROUP BY job_type
    """).fetchall()
    jtype_labels = [r["job_type"] for r in jtype]
    jtype_data = [r["cnt"] for r in jtype]

    return jsonify({
        "status": {"labels": status_labels, "data": status_data},
        "daily_reg": {"labels": daily_labels, "data": daily_data},
        "job_types": {"labels": jtype_labels, "data": jtype_data},
    })


@api_bp.route("/stats/student")
def student_stats():
    if "user_id" not in session or session.get("role") != "student":
        return jsonify({"error": "unauthorized"}), 401
    db = get_db()
    sid = session["user_id"]
    rows = db.execute("SELECT status, COUNT(*) as cnt FROM applications WHERE student_id=? GROUP BY status", (sid,)).fetchall()
    return jsonify({
        "labels": [r["status"] for r in rows],
        "data": [r["cnt"] for r in rows],
    })


@api_bp.route("/stats/company")
def company_stats():
    if "user_id" not in session or session.get("role") != "company":
        return jsonify({"error": "unauthorized"}), 401
    db = get_db()
    cid = session["user_id"]
    rows = db.execute("""
        SELECT a.status, COUNT(*) as cnt
        FROM applications a JOIN jobs j ON a.job_id=j.id
        WHERE j.company_id=? GROUP BY a.status
    """, (cid,)).fetchall()
    # Apps per job
    job_rows = db.execute("""
        SELECT j.title, COUNT(a.id) as cnt
        FROM jobs j LEFT JOIN applications a ON a.job_id=j.id
        WHERE j.company_id=? GROUP BY j.id ORDER BY cnt DESC LIMIT 6
    """, (cid,)).fetchall()
    return jsonify({
        "status": {"labels": [r["status"] for r in rows], "data": [r["cnt"] for r in rows]},
        "per_job": {"labels": [r["title"] for r in job_rows], "data": [r["cnt"] for r in job_rows]},
    })
