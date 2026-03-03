from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    is_premium = db.Column(db.Boolean, default=False)
    premium_expiry = db.Column(db.DateTime, nullable=True) # Tracks when premium ends
    profile_photo = db.Column(db.Text, default="") # Stores image as Base64 text
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False) 
    utr_number = db.Column(db.String(50), nullable=False) 
    amount = db.Column(db.Integer, nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="Pending")
    date = db.Column(db.DateTime, default=datetime.utcnow)

class SiteAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_views = db.Column(db.Integer, default=0)