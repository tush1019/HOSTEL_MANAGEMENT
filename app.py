import os
import sqlite3
from datetime import datetime

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["DATABASE"] = os.path.join(app.root_path, "hostel.db")
app.config["SECRET_KEY"] = "dev-secret-key"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    if "db" in g:
        g.db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            capacity INTEGER NOT NULL,
            rent INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'available'
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (room_id) REFERENCES rooms(id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT NOT NULL,
            paid_on TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """
    )

    room_count = db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if room_count == 0:
        db.executemany(
            "INSERT INTO rooms (room_number, capacity, rent, status) VALUES (?, ?, ?, ?)",
            [
                ("A-101", 2, 5500, "available"),
                ("A-102", 3, 6000, "available"),
                ("B-201", 2, 6500, "available"),
            ],
        )

    student_count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if student_count == 0:
        db.execute(
            """
            INSERT INTO students (name, phone, room_id, check_in, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("Ananya Sharma", "9876543210", 1, "2026-01-05", "Active"),
        )

    db.commit()


with app.app_context():
    init_db()


@app.route("/")
def index():
    db = get_db()
    total_rooms = db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    occupied_rooms = db.execute(
        "SELECT COUNT(DISTINCT room_id) FROM students WHERE status = 'Active'"
    ).fetchone()[0]
    total_revenue = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments"
    ).fetchone()[0]
    recent_payments = db.execute(
        """
        SELECT p.*, s.name AS student_name
        FROM payments p
        JOIN students s ON s.id = p.student_id
        ORDER BY p.paid_on DESC, p.id DESC
        LIMIT 5
        """
    ).fetchall()
    students = db.execute(
        "SELECT id, name FROM students ORDER BY name"
    ).fetchall()

    return render_template(
        "index.html",
        total_rooms=total_rooms,
        total_students=total_students,
        occupied_rooms=occupied_rooms,
        total_revenue=total_revenue,
        recent_payments=recent_payments,
        students=students,
    )


@app.route("/api/summary")
def api_summary():
    db = get_db()
    summary = {
        "total_rooms": db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0],
        "total_students": db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "occupied_rooms": db.execute(
            "SELECT COUNT(DISTINCT room_id) FROM students WHERE status = 'Active'"
        ).fetchone()[0],
        "total_revenue": db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments"
        ).fetchone()[0],
    }
    return jsonify(summary)


@app.route("/rooms")
def rooms():
    db = get_db()
    room_rows = db.execute(
        """
        SELECT r.*, COUNT(s.id) AS occupied_students
        FROM rooms r
        LEFT JOIN students s ON s.room_id = r.id AND s.status = 'Active'
        GROUP BY r.id
        ORDER BY r.room_number
        """
    ).fetchall()
    return render_template("rooms.html", rooms=room_rows)


@app.route("/rooms/add", methods=["POST"])
def add_room():
    room_number = request.form.get("room_number", "").strip()
    capacity = request.form.get("capacity", "0").strip()
    rent = request.form.get("rent", "0").strip()

    if not room_number or not capacity or not rent:
        return "Room number, capacity and rent are required.", 400

    try:
        capacity = int(capacity)
        rent = int(rent)
    except ValueError:
        return "Capacity and rent must be valid numbers.", 400

    if capacity <= 0 or rent <= 0:
        return "Capacity and rent must be greater than zero.", 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO rooms (room_number, capacity, rent, status) VALUES (?, ?, ?, 'available')",
            (room_number, capacity, rent),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return "A room with this number already exists.", 400

    return redirect(url_for("rooms"))


@app.route("/students")
def students():
    db = get_db()
    student_rows = db.execute(
        """
        SELECT s.*, r.room_number
        FROM students s
        JOIN rooms r ON r.id = s.room_id
        ORDER BY s.name
        """
    ).fetchall()
    room_rows = db.execute(
        "SELECT id, room_number FROM rooms ORDER BY room_number"
    ).fetchall()
    return render_template("students.html", students=student_rows, rooms=room_rows)


@app.route("/students/add", methods=["POST"])
def add_student():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    room_id = request.form.get("room_id", "").strip()
    check_in = request.form.get("check_in") or datetime.utcnow().strftime("%Y-%m-%d")

    if not name or not phone or not room_id:
        return "Name, phone number and room are required.", 400

    try:
        room_id = int(room_id)
    except ValueError:
        return "Room selection is invalid.", 400

    db = get_db()
    room = db.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if room is None:
        return "Selected room does not exist.", 400

    occupied = db.execute(
        "SELECT COUNT(*) FROM students WHERE room_id = ? AND status = 'Active'",
        (room_id,),
    ).fetchone()[0]
    if occupied >= room["capacity"]:
        return "Selected room has reached its capacity.", 400

    db.execute(
        "INSERT INTO students (name, phone, room_id, check_in, status) VALUES (?, ?, ?, ?, 'Active')",
        (name, phone, room_id, check_in),
    )
    db.commit()
    return redirect(url_for("students"))


@app.route("/payments/add", methods=["POST"])
def add_payment():
    student_id = request.form.get("student_id", "").strip()
    amount = request.form.get("amount", "").strip()
    method = request.form.get("method", "").strip()

    if not student_id or not amount or not method:
        return "Student, amount and payment method are required.", 400

    try:
        student_id = int(student_id)
        amount = float(amount)
    except ValueError:
        return "Student ID and amount must be valid numbers.", 400

    if amount <= 0:
        return "Payment amount must be greater than zero.", 400

    db = get_db()
    student = db.execute("SELECT id FROM students WHERE id = ?", (student_id,)).fetchone()
    if student is None:
        return "Student does not exist.", 400

    db.execute(
        "INSERT INTO payments (student_id, amount, method, paid_on) VALUES (?, ?, ?, ?)",
        (student_id, amount, method, datetime.utcnow().strftime("%Y-%m-%d")),
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/health")
def health_check():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
