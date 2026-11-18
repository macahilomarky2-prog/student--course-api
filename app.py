"""
Campus Connect - Integrated Student Enrollment and Information System
Flask REST API + SQLite backend (Laboratory 3 + Laboratory 4 combined).

Run locally (Windows):
    run.bat

Run manually:
    pip install -r requirements.txt
    python app.py

API base URL: http://127.0.0.1:5000/api
"""

import os
import sqlite3
from datetime import date

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "database.db"))

app = Flask(__name__)
CORS(app)  # lets the hosted frontend call this API from another origin

ENROLLMENT_STATUSES = ["Pending", "Approved", "Rejected", "Cancelled"]
COURSE_CAPACITY = 40

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_number TEXT NOT NULL UNIQUE,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    program        TEXT NOT NULL,
    year_level     INTEGER NOT NULL,
    contact_number TEXT,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    department  TEXT NOT NULL,
    units       INTEGER NOT NULL DEFAULT 3,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL,
    course_id       INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses  (course_id)  ON DELETE CASCADE
);

-- A student can hold only one active enrollment per course.
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_enrollment
    ON enrollments (student_id, course_id)
    WHERE status != 'Cancelled';

CREATE TABLE IF NOT EXISTS announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    author          TEXT NOT NULL,
    date_posted     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student'
);
"""

SEED_STUDENTS = [
    ("2024-00101", "Maria", "Santos", "maria.santos@campusconnect.edu", "BS Computer Science", 3, "0917 412 8830"),
    ("2024-00102", "Juan", "Dela Cruz", "juan.delacruz@campusconnect.edu", "BS Information Technology", 2, "0918 220 7741"),
    ("2024-00103", "Andrea", "Reyes", "andrea.reyes@campusconnect.edu", "BS Information Systems", 4, "0906 771 2093"),
    ("2024-00104", "Miguel", "Tan", "miguel.tan@campusconnect.edu", "BS Computer Engineering", 1, "0927 118 6640"),
    ("2024-00105", "Bea", "Villanueva", "bea.villanueva@campusconnect.edu", "BS Computer Science", 3, "0915 903 4412"),
    ("2024-00106", "Karlo", "Mendoza", "karlo.mendoza@campusconnect.edu", "BS Information Technology", 4, "0919 552 8871"),
]

SEED_COURSES = [
    ("CS101", "Introduction to Computing", "College of Computer Studies", 3),
    ("CS201", "Data Structures and Algorithms", "College of Computer Studies", 3),
    ("IT210", "Web Systems and Technologies", "College of Information Technology", 3),
    ("IS305", "Systems Integration and Architecture", "College of Information Systems", 3),
    ("GE105", "Ethics in Computing", "General Education", 3),
    ("DB220", "Database Management Systems", "College of Computer Studies", 3),
]

SEED_ENROLLMENTS = [
    (1, 4, "2026-11-18", "Approved"),
    (2, 3, "2026-11-18", "Pending"),
    (3, 6, "2026-11-17", "Approved"),
    (4, 1, "2026-11-17", "Pending"),
    (5, 2, "2026-11-16", "Approved"),
    (6, 5, "2026-11-15", "Rejected"),
    (1, 2, "2026-11-14", "Approved"),
]

SEED_ANNOUNCEMENTS = [
    ("Enrollment for 2nd Semester opens Monday",
     "Online enrollment opens at 8:00 AM. Please settle your accounts and confirm your program adviser before adding courses.",
     "Office of the Registrar", "2026-11-18"),
    ("Systems Integration lab moved to Room 402",
     "Starting this week, all Systems Integration and Architecture laboratory sessions will be held in Room 402, College of Computer Studies.",
     "Dean's Office", "2026-11-16"),
    ("Course advising schedule released",
     "Third year students may book their advising slot through their program adviser from November 20 to 24.",
     "Academic Affairs", "2026-11-14"),
    ("Library extends weekend hours",
     "The university library will be open until 8:00 PM on Saturdays during the enrollment period.",
     "University Library", "2026-11-11"),
]


def init_db():
    """Create the tables and load sample records the first time the app runs."""
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(SCHEMA)
        if connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO students (student_number, first_name, last_name, email, program, year_level, contact_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
                SEED_STUDENTS,
            )
        if connection.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO courses (course_code, course_name, department, units) VALUES (?, ?, ?, ?)",
                SEED_COURSES,
            )
        if connection.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
                SEED_ENROLLMENTS,
            )
        if connection.execute("SELECT COUNT(*) FROM announcements").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO announcements (title, content, author, date_posted) VALUES (?, ?, ?, ?)",
                SEED_ANNOUNCEMENTS,
            )
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            connection.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
                ("registrar", generate_password_hash("campus123"), "University Registrar", "admin"),
            )
        connection.commit()
    finally:
        connection.close()


def get_db():
    """One SQLite connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def as_dict(row):
    return dict(row) if row is not None else None


def payload():
    return request.get_json(silent=True) or {}


def bad_request(message, status=400):
    return jsonify({"error": message}), status


def missing_fields(data, fields):
    return [field for field in fields if str(data.get(field, "")).strip() == ""]


def fetch_enrollment(enrollment_id):
    row = get_db().execute(
        """
        SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,
               s.student_number,
               s.first_name || ' ' || s.last_name AS student_name,
               c.course_code, c.course_name, c.department
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        JOIN courses  c ON c.course_id  = e.course_id
        WHERE e.enrollment_id = ?
        """,
        (enrollment_id,),
    ).fetchone()
    return as_dict(row)


@app.get("/")
def index():
    """Small standalone API explorer (templates/index.html)."""
    return render_template("index.html")


@app.get("/api/health")
def health():
    db = get_db()
    tables = [row["name"] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()]
    return jsonify({
        "status": "ok",
        "service": "Campus Connect API",
        "database": DB_PATH,
        "tables": tables,
        "time": date.today().isoformat(),
    })


@app.get("/api/stats")
def stats():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_courses = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_enrollments = db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]

    counts = {
        row["status"]: row["total"]
        for row in db.execute("SELECT status, COUNT(*) AS total FROM enrollments GROUP BY status").fetchall()
    }

    available_courses = db.execute(
        """
        SELECT COUNT(*) FROM courses c
        WHERE (SELECT COUNT(*) FROM enrollments e
               WHERE e.course_id = c.course_id AND e.status IN ('Pending', 'Approved')) < ?
        """,
        (COURSE_CAPACITY,),
    ).fetchone()[0]

    departments = db.execute("SELECT COUNT(DISTINCT department) FROM courses").fetchone()[0]
    programs = db.execute("SELECT COUNT(DISTINCT program) FROM students").fetchone()[0]

    trend_rows = db.execute(
        "SELECT enrollment_date AS day, COUNT(*) AS value FROM enrollments GROUP BY enrollment_date ORDER BY enrollment_date DESC LIMIT 7"
    ).fetchall()
    trend = [{"day": row["day"][5:], "value": row["value"]} for row in reversed(trend_rows)]

    return jsonify({
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "available_courses": available_courses,
        "departments": departments,
        "programs": programs,
        "approved": counts.get("Approved", 0),
        "pending": counts.get("Pending", 0),
        "rejected": counts.get("Rejected", 0),
        "cancelled": counts.get("Cancelled", 0),
        "trend": trend,
    })


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@app.get("/api/students")
def list_students():
    search = (request.args.get("search") or "").strip()
    sql = "SELECT * FROM students"
    params = ()
    if search:
        like = "%" + search + "%"
        sql += (" WHERE student_number LIKE ? OR first_name LIKE ? OR last_name LIKE ?"
                " OR email LIKE ? OR program LIKE ?")
        params = (like, like, like, like, like)
    sql += " ORDER BY student_id"
    return jsonify([as_dict(row) for row in get_db().execute(sql, params).fetchall()])


@app.get("/api/students/<int:student_id>")
def get_student(student_id):
    db = get_db()
    row = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if row is None:
        return bad_request("Student not found.", 404)
    student = as_dict(row)
    student["enrollments"] = [as_dict(item) for item in db.execute(
        """
        SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,
               c.course_code, c.course_name, c.department
        FROM enrollments e
        JOIN courses c ON c.course_id = e.course_id
        WHERE e.student_id = ?
        ORDER BY e.enrollment_id DESC
        """,
        (student_id,),
    ).fetchall()]
    return jsonify(student)


@app.post("/api/students")
def create_student():
    data = payload()
    missing = missing_fields(data, ["student_number", "first_name", "last_name", "email", "program", "year_level"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    try:
        year_level = int(data["year_level"])
    except (TypeError, ValueError):
        return bad_request("Year level must be a number.")
    if year_level < 1 or year_level > 6:
        return bad_request("Year level must be between 1 and 6.")

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO students (student_number, first_name, last_name, email, program, year_level, contact_number)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data["student_number"].strip(),
                data["first_name"].strip(),
                data["last_name"].strip(),
                data["email"].strip().lower(),
                data["program"].strip(),
                year_level,
                (data.get("contact_number") or "").strip(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("Student number or email already exists.", 409)

    row = db.execute("SELECT * FROM students WHERE student_id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(as_dict(row)), 201


@app.put("/api/students/<int:student_id>")
def update_student(student_id):
    data = payload()
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return bad_request("Student not found.", 404)
    missing = missing_fields(data, ["student_number", "first_name", "last_name", "email", "program", "year_level"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    try:
        year_level = int(data["year_level"])
    except (TypeError, ValueError):
        return bad_request("Year level must be a number.")

    try:
        db.execute(
            "UPDATE students SET student_number = ?, first_name = ?, last_name = ?, email = ?,"
            " program = ?, year_level = ?, contact_number = ? WHERE student_id = ?",
            (
                data["student_number"].strip(),
                data["first_name"].strip(),
                data["last_name"].strip(),
                data["email"].strip().lower(),
                data["program"].strip(),
                year_level,
                (data.get("contact_number") or "").strip(),
                student_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("Student number or email already belongs to another student.", 409)

    row = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    return jsonify(as_dict(row))


@app.delete("/api/students/<int:student_id>")
def delete_student(student_id):
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return bad_request("Student not found.", 404)
    db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    db.commit()
    return jsonify({"message": "Student deleted."})


# ---------------------------------------------------------------------------
# Courses (Laboratory 3 - Student Course Management API)
# ---------------------------------------------------------------------------

@app.get("/api/courses")
def list_courses():
    search = (request.args.get("search") or "").strip()
    sql = "SELECT * FROM courses"
    params = ()
    if search:
        like = "%" + search + "%"
        sql += " WHERE course_code LIKE ? OR course_name LIKE ? OR department LIKE ?"
        params = (like, like, like)
    sql += " ORDER BY course_code"
    return jsonify([as_dict(row) for row in get_db().execute(sql, params).fetchall()])


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    db = get_db()
    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    if row is None:
        return bad_request("Course not found.", 404)
    course = as_dict(row)
    course["enrollments"] = [as_dict(item) for item in db.execute(
        """
        SELECT e.enrollment_id, e.status, s.student_number,
               s.first_name || ' ' || s.last_name AS student_name
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        WHERE e.course_id = ?
        ORDER BY e.enrollment_id DESC
        """,
        (course_id,),
    ).fetchall()]
    return jsonify(course)


@app.post("/api/courses")
def create_course():
    data = payload()
    missing = missing_fields(data, ["course_code", "course_name", "department"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO courses (course_code, course_name, department, units) VALUES (?, ?, ?, ?)",
            (
                data["course_code"].strip().upper(),
                data["course_name"].strip(),
                data["department"].strip(),
                int(data.get("units") or 3),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("Course code already exists.", 409)

    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(as_dict(row)), 201


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    data = payload()
    db = get_db()
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return bad_request("Course not found.", 404)
    missing = missing_fields(data, ["course_code", "course_name", "department"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    try:
        db.execute(
            "UPDATE courses SET course_code = ?, course_name = ?, department = ?, units = ? WHERE course_id = ?",
            (
                data["course_code"].strip().upper(),
                data["course_name"].strip(),
                data["department"].strip(),
                int(data.get("units") or 3),
                course_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("Course code already belongs to another course.", 409)

    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    return jsonify(as_dict(row))


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    db = get_db()
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return bad_request("Course not found.", 404)
    db.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    db.commit()
    return jsonify({"message": "Course deleted."})


# ---------------------------------------------------------------------------
# Enrollments (students + courses combined)
# ---------------------------------------------------------------------------

@app.get("/api/enrollments")
def list_enrollments():
    search = (request.args.get("search") or "").strip()
    sql = """
        SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,
               s.student_number,
               s.first_name || ' ' || s.last_name AS student_name,
               c.course_code, c.course_name, c.department
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        JOIN courses  c ON c.course_id  = e.course_id
    """
    params = ()
    if search:
        like = "%" + search + "%"
        sql += (" WHERE s.student_number LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?"
                " OR c.course_code LIKE ? OR c.course_name LIKE ? OR e.status LIKE ?")
        params = (like, like, like, like, like, like)
    sql += " ORDER BY e.enrollment_id DESC"
    return jsonify([as_dict(row) for row in get_db().execute(sql, params).fetchall()])


@app.get("/api/enrollments/<int:enrollment_id>")
def get_enrollment(enrollment_id):
    row = fetch_enrollment(enrollment_id)
    if row is None:
        return bad_request("Enrollment not found.", 404)
    return jsonify(row)


@app.post("/api/enrollments")
def create_enrollment():
    data = payload()
    if missing_fields(data, ["student_id", "course_id"]):
        return bad_request("student_id and course_id are required.")
    try:
        student_id = int(data["student_id"])
        course_id = int(data["course_id"])
    except (TypeError, ValueError):
        return bad_request("student_id and course_id must be numbers.")

    status = data.get("status") or "Pending"
    if status not in ENROLLMENT_STATUSES:
        return bad_request("Status must be one of: " + ", ".join(ENROLLMENT_STATUSES))

    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return bad_request("Student not found.", 404)
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return bad_request("Course not found.", 404)

    duplicate = db.execute(
        "SELECT enrollment_id FROM enrollments WHERE student_id = ? AND course_id = ? AND status != 'Cancelled'",
        (student_id, course_id),
    ).fetchone()
    if duplicate is not None:
        return bad_request("This student is already enrolled in that course.", 409)

    enrollment_date = data.get("enrollment_date") or date.today().isoformat()
    try:
        cursor = db.execute(
            "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
            (student_id, course_id, enrollment_date, status),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("This student is already enrolled in that course.", 409)

    return jsonify(fetch_enrollment(cursor.lastrowid)), 201


@app.put("/api/enrollments/<int:enrollment_id>")
def update_enrollment(enrollment_id):
    data = payload()
    db = get_db()
    row = fetch_enrollment(enrollment_id)
    if row is None:
        return bad_request("Enrollment not found.", 404)

    status = data.get("status") or row["status"]
    if status not in ENROLLMENT_STATUSES:
        return bad_request("Status must be one of: " + ", ".join(ENROLLMENT_STATUSES))

    enrollment_date = data.get("enrollment_date") or row["enrollment_date"]
    db.execute(
        "UPDATE enrollments SET status = ?, enrollment_date = ? WHERE enrollment_id = ?",
        (status, enrollment_date, enrollment_id),
    )
    db.commit()
    return jsonify(fetch_enrollment(enrollment_id))


@app.delete("/api/enrollments/<int:enrollment_id>")
def delete_enrollment(enrollment_id):
    db = get_db()
    if fetch_enrollment(enrollment_id) is None:
        return bad_request("Enrollment not found.", 404)
    db.execute("DELETE FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
    db.commit()
    return jsonify({"message": "Enrollment deleted."})


# ---------------------------------------------------------------------------
# Announcements (Laboratory 4 - Campus Connect portal)
# ---------------------------------------------------------------------------

@app.get("/api/announcements")
def list_announcements():
    search = (request.args.get("search") or "").strip()
    sql = "SELECT * FROM announcements"
    params = ()
    if search:
        like = "%" + search + "%"
        sql += " WHERE title LIKE ? OR content LIKE ? OR author LIKE ?"
        params = (like, like, like)
    sql += " ORDER BY date_posted DESC, announcement_id DESC"
    return jsonify([as_dict(row) for row in get_db().execute(sql, params).fetchall()])


@app.get("/api/announcements/<int:announcement_id>")
def get_announcement(announcement_id):
    row = get_db().execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
    ).fetchone()
    if row is None:
        return bad_request("Announcement not found.", 404)
    return jsonify(as_dict(row))


@app.post("/api/announcements")
def create_announcement():
    data = payload()
    missing = missing_fields(data, ["title", "content", "author"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    db = get_db()
    cursor = db.execute(
        "INSERT INTO announcements (title, content, author, date_posted) VALUES (?, ?, ?, ?)",
        (
            data["title"].strip(),
            data["content"].strip(),
            data["author"].strip(),
            data.get("date_posted") or date.today().isoformat(),
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(as_dict(row)), 201


@app.put("/api/announcements/<int:announcement_id>")
def update_announcement(announcement_id):
    data = payload()
    db = get_db()
    row = db.execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
    ).fetchone()
    if row is None:
        return bad_request("Announcement not found.", 404)
    missing = missing_fields(data, ["title", "content", "author"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    db.execute(
        "UPDATE announcements SET title = ?, content = ?, author = ?, date_posted = ? WHERE announcement_id = ?",
        (
            data["title"].strip(),
            data["content"].strip(),
            data["author"].strip(),
            data.get("date_posted") or row["date_posted"],
            announcement_id,
        ),
    )
    db.commit()
    updated = db.execute(
        "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
    ).fetchone()
    return jsonify(as_dict(updated))


@app.delete("/api/announcements/<int:announcement_id>")
def delete_announcement(announcement_id):
    db = get_db()
    if db.execute("SELECT 1 FROM announcements WHERE announcement_id = ?", (announcement_id,)).fetchone() is None:
        return bad_request("Announcement not found.", 404)
    db.execute("DELETE FROM announcements WHERE announcement_id = ?", (announcement_id,))
    db.commit()
    return jsonify({"message": "Announcement deleted."})


# ---------------------------------------------------------------------------
# Users (passwords are stored as hashes, never as plain text)
# ---------------------------------------------------------------------------

@app.get("/api/users")
def list_users():
    rows = get_db().execute("SELECT user_id, username, full_name, role FROM users ORDER BY user_id").fetchall()
    return jsonify([as_dict(row) for row in rows])


@app.post("/api/users")
def create_user():
    data = payload()
    missing = missing_fields(data, ["username", "password", "full_name"])
    if missing:
        return bad_request("Missing required fields: " + ", ".join(missing))
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (
                data["username"].strip(),
                generate_password_hash(data["password"]),
                data["full_name"].strip(),
                data.get("role") or "student",
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return bad_request("Username already exists.", 409)
    row = db.execute(
        "SELECT user_id, username, full_name, role FROM users WHERE user_id = ?", (cursor.lastrowid,)
    ).fetchone()
    return jsonify(as_dict(row)), 201


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found."}), 404
    return "Not found", 404


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "Internal server error. Check the Flask console."}), 500


init_db()  # creates database.db and the sample rows on first run

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
