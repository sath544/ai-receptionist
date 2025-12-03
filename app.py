import os, json, io, csv
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_, and_

from models import db, Appointment, AdminUser, Client

# -------------------------------------
# APP SETUP
# -------------------------------------

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = "sqlite:///" + os.path.join(BASE_DIR, "data.db")

app.config["SQLALCHEMY_DATABASE_URI"] = DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# -------------------------------------
# INITIALIZE DATABASE + DEFAULT CLIENT
# -------------------------------------

with app.app_context():
    db.create_all()

    # Create default client for testing
    if not Client.query.first():
        default_client = Client(
            slug="demo",
            name="Demo Business",
            color="#2563eb",
            logo=None
        )
        db.session.add(default_client)
        db.session.commit()

        # Admin for demo client
        demo_admin = AdminUser(
            username="admin@demo",
            password=generate_password_hash("demo123"),
            client_id=default_client.id
        )
        db.session.add(demo_admin)
        db.session.commit()

# -------------------------------------
# HELPER: LOGIN REQUIRED
# -------------------------------------

from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped

# -------------------------------------
# ROUTE: HOME (Chat UI)
# -------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

# -------------------------------------
# ROUTE: CHAT API
# -------------------------------------

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()

    # Basic quick responses
    if any(g in msg.lower() for g in ["hi", "hello", "hey"]):
        return jsonify({"reply": "Hello! 👋 I'm your AI receptionist. How can I help you today?"})

    # Appointment booking pattern
    try:
        if "book appointment" in msg.lower():
            parts = msg.split(":", 1)[1].strip()
            segs = [s.strip() for s in parts.split(",")]

            dt = datetime.strptime(segs[0], "%Y-%m-%d %H:%M")
            name = segs[1]
            purpose = ", ".join(segs[2:])

            # Use default client (demo)
            client = Client.query.filter_by(slug="demo").first()

            appt = Appointment(
                client_id=client.id,
                name=name,
                date=dt.date().isoformat(),
                time=dt.strftime("%H:%M"),
                purpose=purpose,
                raw_message=msg
            )
            db.session.add(appt)
            db.session.commit()

            return jsonify({
                "reply": f"Appointment booked:\nName: {name}\nDate: {appt.date}\nTime: {appt.time}\nPurpose: {purpose}"
            })

    except:
        pass

    return jsonify({"reply": "Sorry, I didn't understand. Try: book appointment: YYYY-MM-DD HH:MM, Name, purpose"})

# -------------------------------------
# ROUTE: ADMIN LOGIN
# -------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = AdminUser.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["admin_id"] = user.id
            session["client_id"] = user.client_id
            session["client_slug"] = user.client.slug
            session["client_name"] = user.client.name
            return redirect(url_for("admin_dashboard"))

        return render_template("admin_login.html", error="Invalid login")

    return render_template("admin_login.html")

# -------------------------------------
# ROUTE: ADMIN LOGOUT
# -------------------------------------

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# -------------------------------------
# ROUTE: ADMIN DASHBOARD
# -------------------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    client_id = session["client_id"]

    q = request.args.get("q", "").strip()
    date_from = request.args.get("from")
    date_to = request.args.get("to")

    page = int(request.args.get("page", 1))
    per_page = 20

    query = Appointment.query.filter_by(client_id=client_id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Appointment.name.ilike(like),
                Appointment.purpose.ilike(like),
                Appointment.raw_message.ilike(like),
            )
        )

    if date_from:
        query = query.filter(Appointment.created_at >= date_from)
    if date_to:
        query = query.filter(Appointment.created_at <= date_to)

    query = query.order_by(Appointment.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    appts = pagination.items

    return render_template(
        "admin_dashboard.html",
        appts=appts,
        pagination=pagination,
        q=q,
        date_from=date_from,
        date_to=date_to
    )

# -------------------------------------
# ROUTE: DELETE APPOINTMENT
# -------------------------------------

@app.route("/admin/delete/<int:aid>", methods=["POST"])
@admin_required
def admin_delete(aid):
    appt = Appointment.query.get_or_404(aid)
    if appt.client_id != session["client_id"]:
        return "Unauthorized", 403
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

# -------------------------------------
# ROUTE: EXPORT CSV
# -------------------------------------

@app.route("/admin/export")
@admin_required
def admin_export():
    client_id = session["client_id"]

    appts = Appointment.query.filter_by(client_id=client_id).order_by(Appointment.created_at.desc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "created_at", "name", "date", "time", "purpose", "raw_message"])

    for a in appts:
        writer.writerow([
            a.id, a.created_at, a.name, a.date, a.time, a.purpose, a.raw_message
        ])

    buf.seek(0)
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        as_attachment=True,
        download_name="appointments.csv"
    )

# -------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
