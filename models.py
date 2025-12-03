from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    logo = db.Column(db.String(500), nullable=True)
    color = db.Column(db.String(20), default="#2563eb")
    webhook_url = db.Column(db.String(500), nullable=True)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    client = db.relationship("Client", backref="admins")

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"), nullable=False)
    client = db.relationship("Client", backref="appointments")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    purpose = db.Column(db.String(500), nullable=True)
    raw_message = db.Column(db.String(1000), nullable=True)
