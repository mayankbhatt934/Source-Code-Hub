from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expiry = db.Column(db.DateTime, nullable=True)
    profile_photo = db.Column(db.Text, nullable=True)
    
    # NEW BAN COLUMNS
    is_banned = db.Column(db.Boolean, default=False)
    ban_expiry = db.Column(db.DateTime, nullable=True) # Null means permanent if is_banned is True

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    sender_upi = db.Column(db.String(100))
    amount = db.Column(db.Integer)
    plan = db.Column(db.String(50))
    code_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), default='Pending')
    is_gift = db.Column(db.Boolean, default=False)
    gift_recipient_email = db.Column(db.String(100), nullable=True)

class UserCodePurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code_id = db.Column(db.Integer, nullable=False)

class SiteAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    page_views = db.Column(db.Integer, default=0)

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

class FreeCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    code = db.Column(db.Text, nullable=False)

class PremiumCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    code = db.Column(db.Text, nullable=False)

class AIPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)