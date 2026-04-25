import sqlite3
import os
from flask import g


def get_db(app=None):
    if "db" not in g:
        from flask import current_app
        _app = app or current_app
        # Do NOT use detect_types so timestamps stay as plain strings
        g.db = sqlite3.connect(_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        # Auto-init tables if missing
        try:
            g.db.execute("SELECT 1 FROM admin LIMIT 1")
        except sqlite3.OperationalError:
            g.db.close()
            g.pop("db", None)
            init_db(_app)
            g.db = sqlite3.connect(_app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(app):
    db_path = app.config["DATABASE"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    schema = """
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        phone TEXT,
        skills TEXT,
        education TEXT,
        bio TEXT,
        resume_path TEXT,
        profile_score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        industry TEXT,
        location TEXT,
        website TEXT,
        about TEXT,
        logo_path TEXT,
        is_approved INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        requirements TEXT,
        skills_required TEXT,
        location TEXT,
        job_type TEXT DEFAULT 'Full-Time',
        salary TEXT,
        deadline DATE,
        is_approved INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(id)
    );

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        cover_letter TEXT,
        status TEXT DEFAULT 'Applied',
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        UNIQUE(student_id, job_id)
    );

    CREATE TABLE IF NOT EXISTS interviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        scheduled_at TIMESTAMP,
        mode TEXT DEFAULT 'Online',
        location_link TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_role TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    for statement in schema.split(";"):
        stmt = statement.strip()
        if stmt:
            conn.execute(stmt)

    # Seed default admin if not exists
    from werkzeug.security import generate_password_hash
    existing = conn.execute("SELECT id FROM admin WHERE username='admin'").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO admin (username, email, password_hash) VALUES (?,?,?)",
            ("admin", "admin@jobportal.com", generate_password_hash("admin123")),
        )

    conn.commit()
    conn.close()
