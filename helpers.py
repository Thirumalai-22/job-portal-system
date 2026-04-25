import os
from werkzeug.utils import secure_filename
from flask import current_app


ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_resume(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_path, exist_ok=True)
        filepath = os.path.join(upload_path, filename)
        file.save(filepath)
        return filename
    return None


def calculate_profile_score(student):
    """Return a 0-100 profile completeness score."""
    score = 0
    if student["name"]: score += 15
    if student["email"]: score += 10
    if student["phone"]: score += 10
    if student["skills"]: score += 20
    if student["education"]: score += 20
    if student["bio"]: score += 10
    if student["resume_path"]: score += 15
    return score


def notify(db, user_id, user_role, message):
    db.execute(
        "INSERT INTO notifications (user_id, user_role, message) VALUES (?,?,?)",
        (user_id, user_role, message),
    )
    db.commit()
