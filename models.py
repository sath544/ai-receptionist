# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class SuperAdmin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)   # used in widget ?client=slug
    name = db.Column(db.String(200), nullable=False)
    logo = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(20), default="#2563eb")

    # billing fields (optional)
    stripe_customer_id = db.Column(db.String(200), nullable=True)
    stripe_subscription_id = db.Column(db.String(200), nullable=True)
    billing_status = db.Column(db.String(50), default="inactive")

    # webhook for client integrations (optional)
    webhook_url = db.Column(db.String(500), nullable=True)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)  # email
    password = db.Column(db.String(200), nullable=False)  # hashed
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    client = db.relationship("Client", backref="admins")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    client = db.relationship("Client", backref="appointments")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(50), nullable=False)   # YYYY-MM-DD
    time = db.Column(db.String(20), nullable=False)   # HH:MM
    purpose = db.Column(db.String(500), nullable=True)
    raw_message = db.Column(db.String(1000), nullable=True)
