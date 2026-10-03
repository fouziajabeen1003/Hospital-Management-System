from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import date, datetime

app = Flask(__name__)
app.secret_key = "hospital_secret_key"


def init_db():

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            doctor TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    cursor.execute("PRAGMA table_info(appointments)")
    appointment_columns = [
        column[1] for column in cursor.fetchall()
    ]

    if "user_id" not in appointment_columns:
        cursor.execute(
            "ALTER TABLE appointments ADD COLUMN user_id INTEGER"
        )

    if "status" not in appointment_columns:
        cursor.execute(
            "ALTER TABLE appointments ADD COLUMN status TEXT DEFAULT 'Pending'"
        )

    cursor.execute("""
        UPDATE appointments
        SET status = 'Pending'
        WHERE status IS NULL OR status = ''
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor TEXT NOT NULL,
            medicine TEXT NOT NULL,
            dosage TEXT NOT NULL,
            instructions TEXT NOT NULL
        )
    """)

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, ("doctor@gmail.com",))

    doctor = cursor.fetchone()

    if not doctor:

        cursor.execute("""
            INSERT INTO users
            (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            "Dr. Rahul Sharma",
            "doctor@gmail.com",
            "12345",
            "Doctor"
        ))

    connection.commit()
    connection.close()
    @app.route("/")
    def home():

      return render_template("index.html")


# ---------------------------------------------------
# REGISTER
# ---------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            connection.close()

            flash(
                "Email already registered.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        cursor.execute("""
            INSERT INTO users
            (name, email, password, role)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            password,
            role
        ))

        connection.commit()
        connection.close()

        flash(
            "Registration successful! Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template("register.html")


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, name, email, role
            FROM users
            WHERE email = ?
            AND password = ?
        """, (
            email,
            password
        ))

        user = cursor.fetchone()

        connection.close()

        if user:

            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["user_email"] = user[2]
            session["role"] = user[3]

            flash(
                "Login successful! Welcome.",
                "success"
            )

            if user[3].lower() == "doctor":

                return redirect(
                    url_for("doctor_dashboard")
                )

            return redirect(
                url_for("patient_dashboard")
            )

        flash(
            "Invalid email or password.",
            "error"
        )

    return render_template("login.html")


# ---------------------------------------------------
# LOGOUT
# ---------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("login")
    )
# ---------------------------------------------------
# PATIENT DASHBOARD
# ---------------------------------------------------

@app.route("/patient_dashboard")
def patient_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    return render_template(
        "patient_dashboard.html"
    )


# ---------------------------------------------------
# DOCTORS
# ---------------------------------------------------

@app.route("/doctors")
def doctors():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    doctors_list = [
        {
            "name": "Dr. Rahul Sharma",
            "department": "Cardiology",
            "experience": "10 Years"
        },
        {
            "name": "Dr. Priya Reddy",
            "department": "Pediatrics",
            "experience": "8 Years"
        },
        {
            "name": "Dr. Arjun Kumar",
            "department": "General Medicine",
            "experience": "7 Years"
        }
    ]

    return render_template(
        "doctors.html",
        doctors=doctors_list
    )


# ---------------------------------------------------
# BOOK APPOINTMENT
# ---------------------------------------------------

@app.route("/appointment", methods=["GET", "POST"])
def appointment():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    # TODAY'S DATE
    current_date = date.today().isoformat()

    if request.method == "POST":

        doctor = request.form["doctor"]
        appointment_date = request.form["date"]
        appointment_time = request.form["time"]
        reason = request.form["reason"]

        # CURRENT DATE AND TIME
        current_datetime = datetime.now()

        # CONVERT FORM DATE AND TIME
        try:

            appointment_datetime = datetime.strptime(
                f"{appointment_date} {appointment_time}",
                "%Y-%m-%d %H:%M"
            )

        except ValueError:

            flash(
                "Please enter a valid appointment date and time.",
                "error"
            )

            return redirect(
                url_for("appointment")
            )

        # PREVENT PAST DATE/TIME
        if appointment_datetime < current_datetime:

            flash(
                "Please select a future date and time.",
                "error"
            )

            return redirect(
                url_for("appointment")
            )

        # CONNECT TO DATABASE
        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        # CHECK FOR DOUBLE BOOKING
        cursor.execute("""
            SELECT id
            FROM appointments
            WHERE doctor = ?
            AND date = ?
            AND time = ?
            AND status != 'Cancelled'
        """, (
            doctor,
            appointment_date,
            appointment_time
        ))

        existing_appointment = cursor.fetchone()

        if existing_appointment:

            connection.close()

            flash(
                "This doctor is already booked at this date and time. Please choose another time.",
                "error"
            )

            return redirect(
                url_for("appointment")
            )

        # INSERT APPOINTMENT
        cursor.execute("""
            INSERT INTO appointments
            (
                user_id,
                doctor,
                date,
                time,
                reason,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            doctor,
            appointment_date,
            appointment_time,
            reason,
            "Pending"
        ))

        connection.commit()
        connection.close()

        flash(
            "Appointment booked successfully!",
            "success"
        )

        return redirect(
            url_for("appointments")
        )

    return render_template(
        "appointment.html",
        current_date=current_date
    )
# ---------------------------------------------------
# PATIENT APPOINTMENTS
# ---------------------------------------------------

@app.route("/appointments")
def appointments():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            doctor,
            date,
            time,
            reason,
            status
        FROM appointments
        WHERE user_id = ?
        ORDER BY date, time
    """, (
        session["user_id"],
    ))

    appointments_list = cursor.fetchall()

    connection.close()

    return render_template(
        "appointments.html",
        appointments=appointments_list
    )


# ---------------------------------------------------
# CANCEL APPOINTMENT
# ---------------------------------------------------

@app.route("/cancel_appointment/<int:appointment_id>")
def cancel_appointment(appointment_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ?
        AND user_id = ?
        AND status = 'Pending'
    """, (
        appointment_id,
        session["user_id"]
    ))

    connection.commit()
    connection.close()

    flash(
        "Appointment cancelled successfully.",
        "success"
    )

    return redirect(
        url_for("appointments")
    )


# ---------------------------------------------------
# PATIENT PRESCRIPTIONS
# ---------------------------------------------------

@app.route("/prescriptions")
def prescriptions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "patient":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            doctor,
            medicine,
            dosage,
            instructions
        FROM prescriptions
        WHERE patient_id = ?
    """, (
        session["user_id"],
    ))

    prescriptions_list = cursor.fetchall()

    connection.close()

    return render_template(
        "prescriptions.html",
        prescriptions=prescriptions_list
    )
# ---------------------------------------------------
# DOCTOR DASHBOARD
# ---------------------------------------------------

@app.route("/doctor_dashboard")
def doctor_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "doctor":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    doctor_name = session["user_name"]

    # TOTAL APPOINTMENTS
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
    """, (
        doctor_name,
    ))

    total = cursor.fetchone()[0]

    # PENDING
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
        AND status = 'Pending'
    """, (
        doctor_name,
    ))

    pending = cursor.fetchone()[0]

    # APPROVED
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
        AND status = 'Approved'
    """, (
        doctor_name,
    ))

    approved = cursor.fetchone()[0]

    # REJECTED
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
        AND status = 'Rejected'
    """, (
        doctor_name,
    ))

    rejected = cursor.fetchone()[0]

    # COMPLETED
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
        AND status = 'Completed'
    """, (
        doctor_name,
    ))

    completed = cursor.fetchone()[0]

    # CANCELLED
    cursor.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor = ?
        AND status = 'Cancelled'
    """, (
        doctor_name,
    ))

    cancelled = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "doctor_dashboard.html",
        total=total,
        pending=pending,
        approved=approved,
        rejected=rejected,
        completed=completed,
        cancelled=cancelled
    )
# ---------------------------------------------------
# DOCTOR APPOINTMENTS
# ---------------------------------------------------

@app.route("/doctor_appointments")
def doctor_appointments():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "doctor":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            appointments.id,
            users.name,
            users.email,
            appointments.doctor,
            appointments.date,
            appointments.time,
            appointments.reason,
            appointments.status
        FROM appointments
        JOIN users
        ON appointments.user_id = users.id
        WHERE appointments.doctor = ?
        ORDER BY appointments.date, appointments.time
    """, (
        session["user_name"],
    ))

    appointments_list = cursor.fetchall()

    connection.close()

    return render_template(
        "doctor_appointments.html",
        appointments=appointments_list
    )


# ---------------------------------------------------
# UPDATE APPOINTMENT STATUS
# ---------------------------------------------------

@app.route(
    "/update_appointment_status/<int:appointment_id>",
    methods=["POST"]
)
def update_appointment_status(appointment_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "doctor":
        return redirect(url_for("login"))

    status = request.form["status"]

    allowed_statuses = [
        "Pending",
        "Approved",
        "Rejected",
        "Completed"
    ]

    if status not in allowed_statuses:

        flash(
            "Invalid appointment status.",
            "error"
        )

        return redirect(
            url_for("doctor_appointments")
        )

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE appointments
        SET status = ?
        WHERE id = ?
        AND doctor = ?
    """, (
        status,
        appointment_id,
        session["user_name"]
    ))

    connection.commit()
    connection.close()

    flash(
        "Appointment status updated successfully.",
        "success"
    )

    return redirect(
        url_for("doctor_appointments")
    )
# ---------------------------------------------------
# DOCTOR PRESCRIPTIONS
# ---------------------------------------------------

# ---------------------------------------------------
# DOCTOR PRESCRIPTIONS
# ---------------------------------------------------

@app.route(
    "/doctor_prescriptions",
    methods=["GET", "POST"]
)
def doctor_prescriptions():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "doctor":
        return redirect(url_for("login"))

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    if request.method == "POST":

        patient_id = request.form["patient_id"]
        medicine = request.form["medicine"]
        dosage = request.form["dosage"]
        instructions = request.form["instructions"]

        cursor.execute("""
            INSERT INTO prescriptions
            (
                patient_id,
                doctor,
                medicine,
                dosage,
                instructions
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            patient_id,
            session["user_name"],
            medicine,
            dosage,
            instructions
        ))

        connection.commit()
        connection.close()

        flash(
            "Prescription added successfully!",
            "success"
        )

        return redirect(
            url_for("doctor_prescriptions")
        )

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE email = ?
    """, ("john@gmail.com",))

    patients = cursor.fetchall()

    connection.close()

    return render_template(
        "doctor_prescriptions.html",
        patients=patients
    )
# ---------------------------------------------------
# DOCTOR PROFILE
# ---------------------------------------------------

@app.route("/doctor_profile")
def doctor_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role", "").lower() != "doctor":
        return redirect(url_for("login"))

    doctor = {
        "name": "Dr. Rahul Sharma",
        "email": "doctor@gmail.com",
        "department": "Cardiology",
        "experience": "10 Years"
    }

    return render_template(
        "doctor_profile.html",
        doctor=doctor
    )
# ---------------------------------------------------
# RUN APPLICATION
# ---------------------------------------------------

if __name__ == "__main__":

    init_db()

    app.run(debug=True)