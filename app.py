# app.py
import os
import io
import csv
import smtplib
import stripe
from datetime import datetime, date

from flask import (
    Flask, render_template, request, jsonify,
    session, redirect, url_for, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_

from models import db, SuperAdmin, Client, AdminUser, Appointment

# -------------------------
# APP SETUP
# -------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET", "super-secret-key")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# -------------------------
# EMAIL SENDER
# -------------------------
def send_email(to, subject, body):
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not smtp_user:
        print("⚠ Email not configured. Skipping.")
        return

    msg = f"Subject: {subject}\n\n{body}"

    try:
        s = smtplib.SMTP(smtp_server, smtp_port)
        s.starttls()
        s.login(smtp_user, smtp_pass)
        s.sendmail(smtp_user, to, msg)
        s.quit()
    except Exception as e:
        print("Email error:", e)

# -------------------------
# INITIAL DATABASE SETUP
# -------------------------
with app.app_context():
    db.create_all()

    # Default Super Admin
    if not SuperAdmin.query.first():
        sa = SuperAdmin(
            username="owner",
            password=generate_password_hash("owner123")
        )
        db.session.add(sa)
        db.session.commit()

    # Create demo client if none exist
    if not Client.query.filter_by(slug="demo").first():
        demo = Client(slug="demo", name="Demo Business", color="#2563eb")
        db.session.add(demo)
        db.session.commit()

        admin = AdminUser(
            username="admin@demo",
            password=generate_password_hash("demo123"),
            client_id=demo.id
        )
        db.session.add(admin)
        db.session.commit()

# -------------------------
# SUPER ADMIN AUTH
# -------------------------
from functools import wraps

def superadmin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "superadmin_id" not in session:
            return redirect(url_for("superadmin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/superadmin/login", methods=["GET","POST"])
def superadmin_login():
    if request.method == "POST":
        user = SuperAdmin.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["superadmin_id"] = user.id
            return redirect(url_for("superadmin_dashboard"))
        return render_template("superadmin_login.html", error="Invalid credentials")
    return render_template("superadmin_login.html")

@app.route("/superadmin/logout")
def superadmin_logout():
    session.pop("superadmin_id", None)
    return redirect(url_for("superadmin_login"))

# -------------------------
# SUPER ADMIN DASHBOARD
# -------------------------
@app.route("/superadmin")
@superadmin_required
def superadmin_dashboard():
    clients = Client.query.all()
    return render_template("superadmin_dashboard.html", clients=clients)

@app.route("/superadmin/client/new", methods=["GET","POST"])
@superadmin_required
def create_client():
    if request.method == "POST":
        slug = request.form["slug"].strip()
        name = request.form["name"].strip()
        logo = request.form["logo"].strip()
        color = request.form["color"]

        username = request.form["username"].strip()
        password = request.form["password"].strip()

        c = Client(slug=slug, name=name, logo=logo, color=color)
        db.session.add(c)
        db.session.commit()

        admin = AdminUser(
            username=username,
            password=generate_password_hash(password),
            client_id=c.id
        )
        db.session.add(admin)
        db.session.commit()

        return redirect(url_for("superadmin_dashboard"))

    return render_template("client_form.html", mode="create")

@app.route("/superadmin/client/<int:cid>/edit", methods=["GET","POST"])
@superadmin_required
def edit_client(cid):
    c = Client.query.get_or_404(cid)

    if request.method == "POST":
        c.slug = request.form["slug"]
        c.name = request.form["name"]
        c.logo = request.form["logo"]
        c.color = request.form["color"]
        db.session.commit()
        return redirect(url_for("superadmin_dashboard"))

    return render_template("client_form.html", mode="edit", client=c)

@app.route("/superadmin/client/<int:cid>/delete", methods=["POST"])
@superadmin_required
def delete_client(cid):
    Appointment.query.filter_by(client_id=cid).delete()
    AdminUser.query.filter_by(client_id=cid).delete()
    Client.query.filter_by(id=cid).delete()
    db.session.commit()
    return redirect(url_for("superadmin_dashboard"))

# -------------------------
# SUPER ADMIN ANALYTICS
# -------------------------
@app.route("/superadmin/analytics")
@superadmin_required
def superadmin_analytics():
    total_clients = Client.query.count()
    total_appointments = Appointment.query.count()

    today = date.today()
    today_count = Appointment.query.filter(
        Appointment.created_at >= datetime(today.year, today.month, today.day)
    ).count()

    month_count = Appointment.query.filter(
        Appointment.created_at >= datetime(today.year, today.month, 1)
    ).count()

    top_clients = db.session.query(
        Client.name, func.count(Appointment.id)
    ).join(Appointment).group_by(Client.id).limit(5).all()

    trend = db.session.query(
        func.date(Appointment.created_at),
        func.count(Appointment.id)
    ).group_by(func.date(Appointment.created_at)).all()

    labels = [str(t[0]) for t in trend]
    values = [t[1] for t in trend]

    return render_template(
        "superadmin_analytics.html",
        total_clients=total_clients,
        total_appointments=total_appointments,
        today_count=today_count,
        month_count=month_count,
        top_clients=top_clients,
        labels=labels,
        values=values
    )

# -------------------------
# CLIENT ADMIN AUTH
# -------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        user = AdminUser.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password, request.form["password"]):
            session["admin_id"] = user.id
            session["client_id"] = user.client_id
            session["client_slug"] = user.client.slug
            session["client_name"] = user.client.name
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html", error="Invalid")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

# -------------------------
# CLIENT ADMIN DASHBOARD
# -------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    cid = session["client_id"]

    q = request.args.get("q", "").strip()

    query = Appointment.query.filter_by(client_id=cid)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Appointment.name.ilike(like),
                Appointment.purpose.ilike(like)
            )
        )

    appts = query.order_by(Appointment.created_at.desc()).all()

    return render_template(
        "admin_dashboard.html",
        appts=appts,
        q=q
    )

@app.route("/admin/delete/<int:aid>", methods=["POST"])
@admin_required
def admin_delete(aid):
    Appointment.query.filter_by(id=aid).delete()
    db.session.commit()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export")
@admin_required
def admin_export():
    cid = session["client_id"]
    appts = Appointment.query.filter_by(client_id=cid).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Date", "Time", "Purpose"])
    for a in appts:
        w.writerow([a.name, a.date, a.time, a.purpose])

    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        as_attachment=True,
        download_name="appointments.csv"
    )

# -------------------------
# PUBLIC CHAT API
# -------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "")

    # appointment format:
    # book appointment: 2025-12-10 10:30, John Doe, haircut
    if "book appointment" in msg.lower():
        try:
            _, rest = msg.split(":", 1)
            parts = [p.strip() for p in rest.split(",")]

            dt = datetime.strptime(parts[0], "%Y-%m-%d %H:%M")
            name = parts[1]
            purpose = ", ".join(parts[2:])

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

            # notify admin
            admin = AdminUser.query.filter_by(client_id=client.id).first()
            send_email(
                admin.username,
                "New Appointment",
                f"Name: {name}\nDate: {appt.date}\nTime: {appt.time}\nPurpose: {purpose}"
            )

            return jsonify({"reply": f"Appointment booked for {name} on {appt.date} at {appt.time}!"})

        except Exception as e:
            print("Parse error:", e)

    return jsonify({"reply": "Hello! How can I help you today?"})


if __name__ == "__main__":
    app.run(debug=True)
