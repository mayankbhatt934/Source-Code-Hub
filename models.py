from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import string, random

db = SQLAlchemy()

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expiry = db.Column(db.DateTime, nullable=True)
    profile_photo = db.Column(db.Text, nullable=True)
    is_banned = db.Column(db.Boolean, default=False)
    ban_expiry = db.Column(db.DateTime, nullable=True)
    role = db.Column(db.String(20), default='member') 
    is_friend = db.Column(db.Boolean, default=False)
    referral_code = db.Column(db.String(10), unique=True, default=generate_ref_code)
    earnings = db.Column(db.Integer, default=0)

class PayoutRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    upi_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

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

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False) 
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

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
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    creator_email = db.Column(db.String(100), default='admin')
    is_approved = db.Column(db.Boolean, default=True) # NEW: Approvals for free codes

class PremiumCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    code = db.Column(db.Text, nullable=False)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    creator_email = db.Column(db.String(100), default='admin')
    is_approved = db.Column(db.Boolean, default=True)

class CodeLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    code_type = db.Column(db.String(20), nullable=False)
    code_id = db.Column(db.Integer, nullable=False)

class SupportTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    admin_reply = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Open')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class AIPrompt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    creator_email = db.Column(db.String(100), default='admin') # NEW: Prompt creator
    is_approved = db.Column(db.Boolean, default=True) # NEW: Approvals for prompts