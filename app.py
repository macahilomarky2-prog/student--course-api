"""
Campus Connect - Integrated Student Enrollment and Information System
Backend: Python + Flask + SQLite REST API

Combines:
  * Laboratory 3 - Student Course Management API (courses endpoints)
  * Laboratory 4 - Campus Connect Student Information Portal (students,
    enrollments, announcements, dashboard statistics)

Run locally: python app.py
Then browse: http://127.0.0.1:5000
API base URL: http://127.0.0.1:5000/api
"""

import os
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CAMPUS_CONNECT_DB", os.path.join(BASE_DIR, "database.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "campus-connect-development-key")

# The Base44 frontend runs on a different origin, so the API must allow CORS.
CORS(app, resources={r"/api/*": {"origins": "*"}})

ENROLLMENT_STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")
STUDENT_FIELDS = ("first_name", "last_name", "email", "program", "year_level")
COURSE_FIELDS = ("course_code", "course_name", "department")
ANNOUNCEMENT_FIELDS = ("title", "content", "author")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    program TEXT NOT NULL,
    year_level TEXT NOT NULL,
    contact_number TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS courses (
    course_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    department TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 40,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    date_posted TEXT NOT NULL,
    author TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    student_id INTEGER,
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_enrollment_student ON enrollments (student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_course ON enrollments (course_id);
"""

ENROLLMENT_SELECT = """
SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,
       s.first_name || ' ' || s.last_name AS student_name,
       s.program AS program,
       c.course_code AS course_code,
       c.course_name AS course_name,
       c.department AS department
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN courses c ON c.course_id = e.course_id
"""


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and seed a default admin account and sample data."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "Administrator", "admin"),
        )

    if conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO courses (course_code, course_name, department, capacity) VALUES (?, ?, ?, ?)",
            [
                ("IT101", "Introduction to Computing", "Information Technology", 40),
                ("IT201", "Web Development", "Information Technology", 35),
                ("CS101", "Programming Fundamentals", "Computer Science", 40),
            ],
        )

    if conn.execute("SELECT COUNT(*) FROM announcements").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
            (
                "Welcome to Campus Connect",
                "Enrollment for the new term is now open.",
                date.today().isoformat(),
                "Administrator",
            ),
        )

    conn.commit()
    conn.close()


def rows_to_list(rows):
    return [dict(r) for r in rows]


def error(message, status=400):
    return jsonify({"error": message}), status


def missing_fields(data, fields):
    return [f for f in fields if not str(data.get(f, "")).strip()]


def update_row(table, pk, row_id, data, allowed):
    """Update only the allowed columns that were sent. Returns the updated row or None."""
    db = get_db()
    cols = [c for c in allowed if c in data]
    if cols:
        sql = f"UPDATE {table} SET {', '.join(c + ' = ?' for c in cols)} WHERE {pk} = ?"
        db.execute(sql, [data[c] for c in cols] + [row_id])
        db.commit()
    return db.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (row_id,)).fetchone()


def delete_row(table, pk, row_id):
    db = get_db()
    cur = db.execute(f"DELETE FROM {table} WHERE {pk} = ?", (row_id,))
    db.commit()
    if cur.rowcount == 0:
        return error("Record not found.", 404)
    return jsonify({"message": "Deleted successfully."})


# ---------------------------------------------------------------------------
# Page routes (served directly by Flask)
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/students")
def students_page():
    return render_template("students.html")


@app.route("/courses")
def courses_page():
    return render_template("courses.html")


@app.route("/enrollment")
def enrollment_page():
    return render_template("enrollment.html")


@app.route("/announcements")
def announcements_page():
    return render_template("announcement.html")


# ---------------------------------------------------------------------------
# Health, stats, login
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})


@app.route("/api/stats")
def stats():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_courses = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_enrollments = db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
    available_courses = db.execute(
        """
        SELECT COUNT(*) FROM courses c
        WHERE c.capacity > (
            SELECT COUNT(*) FROM enrollments e
            WHERE e.course_id = c.course_id AND e.status IN ('Pending', 'Approved')
        )
        """
    ).fetchone()[0]
    return jsonify(
        {
            "total_students": total_students,
            "total_courses": total_courses,
            "total_enrollments": total_enrollments,
            "available_courses": available_courses,
        }
    )


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return error("Invalid username or password.", 401)
    return jsonify(
        {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "student_id": user["student_id"],
        }
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@app.route("/api/students", methods=["GET", "POST"])
def students():
    db = get_db()
    if request.method == "GET":
        search = request.args.get("search", "").strip()
        if search:
            like = f"%{search}%"
            rows = db.execute(
                """SELECT * FROM students
                   WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ? OR program LIKE ?
                   ORDER BY student_id""",
                (like, like, like, like),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM students ORDER BY student_id").fetchall()
        return jsonify(rows_to_list(rows))

    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, STUDENT_FIELDS)
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")
    try:
        cur = db.execute(
            """INSERT INTO students (first_name, last_name, email, program, year_level, contact_number)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["first_name"].strip(),
                data["last_name"].strip(),
                data["email"].strip(),
                data["program"].strip(),
                str(data["year_level"]).strip(),
                data.get("contact_number"),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A student with that email already exists.", 409)
    row = db.execute("SELECT * FROM students WHERE student_id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/students/<int:student_id>", methods=["GET", "PUT", "DELETE"])
def student_detail(student_id):
    db = get_db()
    row = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        return error("Student not found.", 404)
    if request.method == "GET":
        return jsonify(dict(row))
    if request.method == "DELETE":
        return delete_row("students", "student_id", student_id)

    data = request.get_json(silent=True) or {}
    try:
        updated = update_row(
            "students", "student_id", student_id, data, STUDENT_FIELDS + ("contact_number",)
        )
    except sqlite3.IntegrityError:
        return error("A student with that email already exists.", 409)
    return jsonify(dict(updated))


# ---------------------------------------------------------------------------
# Courses (Laboratory 3)
# ---------------------------------------------------------------------------
@app.route("/api/courses", methods=["GET", "POST"])
def courses():
    db = get_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM courses ORDER BY course_id").fetchall()
        return jsonify(rows_to_list(rows))

    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, COURSE_FIELDS)
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")
    try:
        capacity = int(data.get("capacity", 40))
    except (TypeError, ValueError):
        return error("Capacity must be a number.")
    try:
        cur = db.execute(
            "INSERT INTO courses (course_code, course_name, department, capacity) VALUES (?, ?, ?, ?)",
            (
                data["course_code"].strip(),
                data["course_name"].strip(),
                data["department"].strip(),
                capacity,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return error("A course with that code already exists.", 409)
    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/courses/<int:course_id>", methods=["GET", "PUT", "DELETE"])
def course_detail(course_id):
    db = get_db()
    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    if row is None:
        return error("Course not found.", 404)
    if request.method == "GET":
        return jsonify(dict(row))
    if request.method == "DELETE":
        return delete_row("courses", "course_id", course_id)

    data = request.get_json(silent=True) or {}
    try:
        updated = update_row(
            "courses", "course_id", course_id, data, COURSE_FIELDS + ("capacity",)
        )
    except sqlite3.IntegrityError:
        return error("A course with that code already exists.", 409)
    return jsonify(dict(updated))


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------
@app.route("/api/enrollments", methods=["GET", "POST"])
def enrollments():
    db = get_db()
    if request.method == "GET":
        sql = ENROLLMENT_SELECT
        params = []
        student_id = request.args.get("student_id")
        if student_id:
            sql += " WHERE e.student_id = ?"
            params.append(student_id)
        sql += " ORDER BY e.enrollment_id"
        return jsonify(rows_to_list(db.execute(sql, params).fetchall()))

    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, ("student_id", "course_id"))
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")

    status = data.get("status", "Pending")
    if status not in ENROLLMENT_STATUSES:
        return error(f"Status must be one of: {', '.join(ENROLLMENT_STATUSES)}")

    student = db.execute("SELECT 1 FROM students WHERE student_id = ?", (data["student_id"],)).fetchone()
    course = db.execute("SELECT capacity FROM courses WHERE course_id = ?", (data["course_id"],)).fetchone()
    if student is None:
        return error("Student not found.", 404)
    if course is None:
        return error("Course not found.", 404)

    duplicate = db.execute(
        """SELECT 1 FROM enrollments
           WHERE student_id = ? AND course_id = ? AND status IN ('Pending', 'Approved')""",
        (data["student_id"], data["course_id"]),
    ).fetchone()
    if duplicate:
        return error("Student is already enrolled in this course.", 409)

    taken = db.execute(
        "SELECT COUNT(*) FROM enrollments WHERE course_id = ? AND status IN ('Pending', 'Approved')",
        (data["course_id"],),
    ).fetchone()[0]
    if taken >= course["capacity"]:
        return error("This course is full.", 409)

    cur = db.execute(
        "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
        (
            data["student_id"],
            data["course_id"],
            data.get("enrollment_date") or date.today().isoformat(),
            status,
        ),
    )
    db.commit()
    row = db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/enrollments/<int:enrollment_id>", methods=["GET", "PUT", "DELETE"])
def enrollment_detail(enrollment_id):
    db = get_db()
    row = db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (enrollment_id,)).fetchone()
    if row is None:
        return error("Enrollment not found.", 404)
    if request.method == "GET":
        return jsonify(dict(row))
    if request.method == "DELETE":
        return delete_row("enrollments", "enrollment_id", enrollment_id)

    data = request.get_json(silent=True) or {}
    if "status" in data and data["status"] not in ENROLLMENT_STATUSES:
        return error(f"Status must be one of: {', '.join(ENROLLMENT_STATUSES)}")
    update_row(
        "enrollments",
        "enrollment_id",
        enrollment_id,
        data,
        ("student_id", "course_id", "enrollment_date", "status"),
    )
    row = db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (enrollment_id,)).fetchone()
    return jsonify(dict(row))


# ---------------------------------------------------------------------------
# Announcements (Laboratory 4)
# ---------------------------------------------------------------------------
@app.route("/api/announcements", methods=["GET", "POST"])
def announcements():
    db = get_db()
    if request.method == "GET":
        rows = db.execute(
            "SELECT * FROM announcements ORDER BY date_posted DESC, announcement_id DESC"
        ).fetchall()
        return jsonify(rows_to_list(rows))

    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, ANNOUNCEMENT_FIELDS)
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")
    cur = db.execute(
        "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
        (
            data["title"].strip(),
            data["content"].strip(),
            data.get("date_posted") or date.today().isoformat(),
            data["author"].strip(),
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(dict(row)), 201


@app.route("/api/announcements/<int:announcement_id>", methods=["GET", "PUT", "DELETE"])
def announcement_detail(announcement_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
    ).fetchone()
    if row is None:
        return error("Announcement not found.", 404)
    if request.method == "GET":
        return jsonify(dict(row))
    if request.method == "DELETE":
        return delete_row("announcements", "announcement_id", announcement_id)

    data = request.get_json(silent=True) or {}
    updated = update_row(
        "announcements",
        "announcement_id",
        announcement_id,
        data,
        ANNOUNCEMENT_FIELDS + ("date_posted",),
    )
    return jsonify(dict(updated))


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
# Called at module level so tables exist when gunicorn imports the app on Render.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
