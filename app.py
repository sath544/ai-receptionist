# app.py (full)
import os
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from io import StringIO
import csv
from datetime import datetime
from urllib.parse import urlencode
import json

# local models
from models import db, Client, Appointment, FAQ

app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{os.path.join(BASE_DIR, 'data.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET", "please-change-this-secret")

db.init_app(app)

# Ensure DB exists (create tables)
with app.app_context():
    db.create_all()

# --------------- Public widget & chat logic ---------------
def load_client_by_slug(slug):
    if not slug:
        return None
    return Client.query.filter_by(slug=slug).first()

def match_faq_for_client(message, client):
    msg = message.lower()
    if not client:
        # fallback to global faqs (client_id is None)
        faqs = FAQ.query.filter_by(client_id=None).all()
    else:
        faqs = FAQ.query.filter((FAQ.client_id == client.id) | (FAQ.client_id == None)).all()
    for f in faqs:
        ks = (f.keywords or "").lower()
        for kw in [k.strip() for k in ks.split(",") if k.strip()]:
            if kw and kw in msg:
                return f.answer
        # also check question substring
        if f.question.lower() in msg:
            return f.answer
    return None

def parse_appointment(message):
    if "book appointment" not in message.lower():
        return None
    try:
        parts = message.split(":", 1)
        details = parts[1].strip()
        segments = [s.strip() for s in details.split(",")]
        if len(segments) < 3:
            return None
        dt_str = segments[0]      # "2025-12-03 16:00"
        name = segments[1]
        purpose = ", ".join(segments[2:])
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return {
            "name": name,
            "date": dt.date().isoformat(),
            "time": dt.strftime("%H:%M"),
            "purpose": purpose
        }
    except Exception as e:
        print("parse_appointment error:", e)
        return None

def save_appointment_for_client(appt, raw_message, client):
    a = Appointment(
        client_id = client.id if client else None,
        name = appt['name'],
        date = appt['date'],
        time = appt['time'],
        purpose = appt['purpose'],
        raw_message = raw_message
    )
    db.session.add(a)
    db.session.commit()

@app.route("/")
def index():
    # If ?client=slug present it will be used by the client widget
    client_slug = request.args.get("client")
    client = load_client_by_slug(client_slug) if client_slug else None
    return render_template("index.html", client=client)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"reply": "Invalid request - missing JSON."}), 400
    user_message = data.get("message", "").strip()
    client_slug = request.args.get("client") or data.get("client")
    client = load_client_by_slug(client_slug) if client_slug else None

    if not user_message:
        return jsonify({"reply": "Please type something 😊"})

    # simple intents
    if any(w in user_message.lower() for w in ["hi", "hello", "hey"]):
        return jsonify({"reply": "Hello! 👋 I'm your AI Receptionist.\nAsk me anything or book an appointment!"})

    if any(w in user_message.lower() for w in ["thank", "thanks"]):
        return jsonify({"reply": "You're welcome! 😊"})

    appt = parse_appointment(user_message)
    if appt:
        save_appointment_for_client(appt, user_message, client)
        return jsonify({"reply": f"Appointment booked for {appt['name']} on {appt['date']} at {appt['time']}!"})

    # FAQ match
    faq_ans = match_faq_for_client(user_message, client)
    if faq_ans:
        return jsonify({"reply": faq_ans})

    # fallback
    return jsonify({"reply": "Sorry, I didn't understand that. Try asking about timings, location, contact, or: `book appointment: 2025-12-03 16:00, Your Name, purpose`"})

# --------------- Admin / client login + client admin pages ---------------
def require_client_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("client_id"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("client_id"):
        return redirect(url_for("admin_dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        client = Client.query.filter_by(admin_username=username).first()
        if client and check_password_hash(client.admin_password_hash, password):
            session["client_id"] = client.id
            session["client_name"] = client.name
            return redirect(url_for("admin_dashboard"))
        error = "Invalid username or password"
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("client_id", None)
    session.pop("client_name", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@require_client_login
def admin_dashboard():
    client_id = session["client_id"]
    q = request.args.get("q","").strip()
    if q:
        appts = Appointment.query.filter(Appointment.client_id==client_id).filter(
            (Appointment.name.ilike(f"%{q}%")) | (Appointment.purpose.ilike(f"%{q}%"))
        ).order_by(Appointment.created_at.desc()).all()
    else:
        appts = Appointment.query.filter_by(client_id=client_id).order_by(Appointment.created_at.desc()).all()
    return render_template("client_admin.html", section="appointments", appts=appts, q=q, active='appointments')

@app.route("/admin/delete/<int:appt_id>", methods=["POST"])
@require_client_login
def admin_delete_appointment(appt_id):
    client_id = session["client_id"]
    appt = Appointment.query.filter_by(id=appt_id, client_id=client_id).first()
    if appt:
        db.session.delete(appt)
        db.session.commit()
        flash("Appointment deleted.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/faqs", methods=["GET","POST"])
@require_client_login
def admin_faqs():
    client_id = session["client_id"]
    if request.method == "POST":
        question = request.form.get("question","").strip()
        answer = request.form.get("answer","").strip()
        keywords = request.form.get("keywords","").strip()
        if question and answer:
            f = FAQ(client_id=client_id, question=question, answer=answer, keywords=keywords)
            db.session.add(f)
            db.session.commit()
            flash("FAQ added.")
            return redirect(url_for("admin_faqs"))
    faqs = FAQ.query.filter_by(client_id=client_id).order_by(FAQ.id.desc()).all()
    return render_template("client_admin.html", section="faqs", faqs=faqs, active='faqs')

@app.route("/admin/faqs/delete/<int:faq_id>", methods=["POST"])
@require_client_login
def admin_faq_delete(faq_id):
    client_id = session["client_id"]
    f = FAQ.query.filter_by(id=faq_id, client_id=client_id).first()
    if f:
        db.session.delete(f)
        db.session.commit()
        flash("FAQ removed.")
    return redirect(url_for("admin_faqs"))

@app.route("/admin/settings", methods=["GET","POST"])
@require_client_login
def admin_settings():
    client_id = session["client_id"]
    client = Client.query.get_or_404(client_id)
    msg = None
    if request.method == "POST":
        name = request.form.get("name","").strip()
        logo = request.form.get("logo","").strip()
        color = request.form.get("color","").strip() or "#2563eb"
        password = request.form.get("password","").strip()
        client.name = name
        client.logo = logo
        client.color = color
        if password:
            client.admin_password_hash = generate_password_hash(password)
        db.session.add(client)
        db.session.commit()
        msg = "Settings saved."
    base_url = request.host_url.rstrip("/")
    return render_template("client_admin.html", section="settings", client=client, msg=msg, base_url=base_url, active='settings')

@app.route("/admin/export")
@require_client_login
def admin_export():
    client_id = session["client_id"]
    appts = Appointment.query.filter_by(client_id=client_id).order_by(Appointment.created_at.desc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id","created_at","name","date","time","purpose","raw_message"])
    for a in appts:
        writer.writerow([a.id, a.created_at.isoformat() if a.created_at else "", a.name, a.date, a.time, a.purpose, a.raw_message])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=appointments_client_{client_id}.csv"
    output.headers["Content-Type"] = "text/csv"
    return output

# --------------- Superadmin (manage clients) ---------------
def require_superadmin_login(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("superadmin"):
            return redirect(url_for("superadmin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/superadmin/login", methods=["GET","POST"])
def superadmin_login():
    if session.get("superadmin"):
        return redirect(url_for("superadmin_dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        if username == os.environ.get("SUPERADMIN_USER","owner") and password == os.environ.get("SUPERADMIN_PASS","owner123"):
            session["superadmin"] = True
            return redirect(url_for("superadmin_dashboard"))
        error = "Invalid credentials"
    return render_template("superadmin_login.html", error=error)

@app.route("/superadmin/logout")
def superadmin_logout():
    session.pop("superadmin", None)
    return redirect(url_for("superadmin_login"))

@app.route("/superadmin")
@require_superadmin_login
def superadmin_dashboard():
    clients = Client.query.order_by(Client.created_at.desc()).all()
    return render_template("superadmin_dashboard.html", clients=clients)

@app.route("/superadmin/client/new", methods=["GET","POST"])
@require_superadmin_login
def superadmin_client_new():
    if request.method == "POST":
        slug = request.form.get("slug","").strip()
        name = request.form.get("name","").strip()
        logo = request.form.get("logo","").strip()
        color = request.form.get("color","").strip() or "#2563eb"
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        if slug and name and username and password:
            hashed = generate_password_hash(password)
            c = Client(slug=slug, name=name, logo=logo, color=color, admin_username=username, admin_password_hash=hashed)
            db.session.add(c)
            db.session.commit()
            flash("Client created.")
            return redirect(url_for("superadmin_dashboard"))
        flash("Please fill required fields")
    return render_template("client_form.html", mode="create", client=None)

@app.route("/superadmin/client/<int:cid>/edit", methods=["GET","POST"])
@require_superadmin_login
def superadmin_client_edit(cid):
    client = Client.query.get_or_404(cid)
    if request.method == "POST":
        client.slug = request.form.get("slug", client.slug).strip()
        client.name = request.form.get("name", client.name).strip()
        client.logo = request.form.get("logo", client.logo).strip()
        client.color = request.form.get("color", client.color).strip() or "#2563eb"
        db.session.add(client)
        db.session.commit()
        flash("Client updated.")
        return redirect(url_for("superadmin_dashboard"))
    return render_template("client_form.html", mode="edit", client=client)

@app.route("/superadmin/client/<int:cid>/delete", methods=["POST"])
@require_superadmin_login
def superadmin_client_delete(cid):
    client = Client.query.get_or_404(cid)
    # optional: cascade delete faqs & appointments
    Appointment.query.filter_by(client_id=client.id).delete()
    FAQ.query.filter_by(client_id=client.id).delete()
    db.session.delete(client)
    db.session.commit()
    flash("Client deleted.")
    return redirect(url_for("superadmin_dashboard"))

# --------------- widget file endpoints ---------------
# serve a minimal widget JS from static/widget.js (we'll provide file) - nothing special here
# But we also support direct widget query ?client=slug on index which is already handled

# --------------- run ---------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
