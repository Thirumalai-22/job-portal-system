from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from ..database import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("auth/register_student.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register_student.html")

        db = get_db()
        existing = db.execute("SELECT id FROM students WHERE email=?", (email,)).fetchone()
        if existing:
            flash("Email already registered.", "warning")
            return render_template("auth/register_student.html")

        db.execute(
            "INSERT INTO students (name, email, password_hash) VALUES (?,?,?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_student.html")


@auth_bp.route("/register/company", methods=["GET", "POST"])
def register_company():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        industry = request.form.get("industry", "").strip()

        if not all([name, email, password]):
            flash("All fields are required.", "danger")
            return render_template("auth/register_company.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register_company.html")

        db = get_db()
        existing = db.execute("SELECT id FROM companies WHERE email=?", (email,)).fetchone()
        if existing:
            flash("Email already registered.", "warning")
            return render_template("auth/register_company.html")

        db.execute(
            "INSERT INTO companies (name, email, password_hash, industry) VALUES (?,?,?,?)",
            (name, email, generate_password_hash(password), industry),
        )
        db.commit()
        flash("Company registered! Awaiting admin approval.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_company.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("main.dashboard_redirect"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "student")

        db = get_db()

        if role == "student":
            user = db.execute("SELECT * FROM students WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["role"] = "student"
                session["name"] = user["name"]
                session["email"] = user["email"]
                return redirect(url_for("student.dashboard"))
            flash("Invalid credentials.", "danger")

        elif role == "company":
            user = db.execute("SELECT * FROM companies WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                if not user["is_approved"]:
                    flash("Your company account is pending admin approval.", "warning")
                    return render_template("auth/login.html")
                session.clear()
                session["user_id"] = user["id"]
                session["role"] = "company"
                session["name"] = user["name"]
                session["email"] = user["email"]
                return redirect(url_for("company.dashboard"))
            flash("Invalid credentials.", "danger")

        elif role == "admin":
            user = db.execute("SELECT * FROM admin WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["role"] = "admin"
                session["name"] = user["username"]
                session["email"] = user["email"]
                return redirect(url_for("admin.dashboard"))
            flash("Invalid admin credentials.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
