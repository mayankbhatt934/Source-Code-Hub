import os
import random
import smtplib
import string
import urllib.request
import json
import time

# Global variable to track the last broadcast
last_broadcast_time = 0

from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase, Notification, SupportTicket, CodeLike, PayoutRequest, Review, Bookmark, Comment, EmailOTP, SystemConfig, PromoCode, PlatformReport

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# ALLOW CROSS-ORIGIN REQUESTS FOR LOCAL AND PRODUCTION
CORS(app, supports_credentials=True)

app.secret_key = 'super_secret_key_change_this_later' 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

ADMIN_USERNAME = 'mayank@123'
ADMIN_PASSWORD = 'password123'

DB_URL = os.environ.get('DATABASE_URL')
if DB_URL:
    if DB_URL.startswith("postgres://"): 
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db' if os.environ.get('VERCEL') else f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    try:
        if not SiteAnalytics.query.first(): 
            db.session.add(SiteAnalytics(page_views=0))
        if not SystemConfig.query.first():
            db.session.add(SystemConfig(maintenance_mode=False))
        db.session.commit()
    except Exception:
        db.session.rollback()

def get_current_user():
    if 'user_email' not in session: 
        return None
    try:
        u = User.query.filter_by(email=session['user_email']).first()
        if not u: 
            session.pop('user_email', None)
        return u
    except Exception:
        session.pop('user_email', None)
        return None

def get_user_role():
    if session.get('is_admin'): 
        return 'owner'
    u = get_current_user()
    if u: 
        return getattr(u, 'role', 'member')
    return 'member'

def check_admin_access(): 
    return get_user_role() in ['staff', 'admin', 'owner']

@app.before_request
def check_maintenance():
    session.permanent = True 
    if request.endpoint in ['static', 'admin_dashboard', 'admin_data', 'toggle_maintenance', 'admin_logout', 'login', 'force_db_reset', 'api_admin_login', 'init_admin']:
        return
    try:
        conf = SystemConfig.query.first()
        if conf and conf.maintenance_mode:
            if get_user_role() in ['staff', 'admin', 'owner'] or session.get('is_admin'):
                return 
            if request.path.startswith('/api/'):
                return jsonify({"error": "Maintenance Mode Active. Please wait."}), 503
            
            maintenance_html = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Maintenance - Source Code Hub</title><style>body { background-color: #0f0c29; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; } .box { background: #1a1a1a; padding: 40px; border-radius: 12px; border: 1px solid #ff5f56; max-width: 500px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); } h1 { color: #ff5f56; margin-bottom: 10px; }</style></head><body><div class="box"><div style="font-size: 3rem; margin-bottom: 20px;">🛠️</div><h1>System Upgrade in Progress</h1><p style="color: #ccc; line-height: 1.6;">We are currently deploying new enterprise features to Source Code Hub. We will be back online shortly. Thank you for your patience!</p></div></body></html>"""
            return maintenance_html, 503
    except Exception:
        pass

def send_system_email(to_email, subject, body):
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    if sender_email and sender_password:
        try:
            html_body = f"""<html><body style="background-color: #0f0c29; color: #ffffff; font-family: sans-serif; padding: 40px 20px; text-align: center; margin: 0;"><div style="max-width: 600px; margin: 0 auto; background-color: #1a1a1a; padding: 30px; border-radius: 15px; border: 1px solid #333;"><h1 style="color: #00d2ff; letter-spacing: 2px; margin-bottom: 30px;">SOURCE CODE <span style="color: #fff;">HUB</span></h1><div style="background-color: rgba(255,255,255,0.05); padding: 25px; border-radius: 10px; text-align: left; font-size: 16px; line-height: 1.6; color: #ddd;">{body.replace(chr(10), '<br>')}</div></div></body></html>"""
            msg = MIMEText(html_body, 'html')
            msg['Subject'] = subject
            msg['From'] = f"Source Code Hub <{sender_email}>"
            msg['To'] = to_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server: 
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
        except Exception:
            pass

@app.route('/force-db-reset')
def force_db_reset(): 
    # CHANGED: Now allows the Master Admin OR anyone with the 'owner' role (like your Superuser)
    if not session.get('is_admin') and get_user_role() != 'owner':
        return "ACCESS DENIED. Master Admin or Owner authentication required.", 403
    try:
        db.drop_all()
        db.create_all()
        db.session.add(SiteAnalytics(page_views=0))
        db.session.add(SystemConfig(maintenance_mode=False))
        db.session.commit()
        return "DATABASE RESET SUCCESSFUL! Tables created safely."
    except Exception as e: 
        return f"Reset Failed: {str(e)}"

@app.route('/')
def home(): 
    try:
        stats = SiteAnalytics.query.first()
        if stats: 
            stats.page_views += 1
            db.session.commit()
    except Exception: 
        db.session.rollback()
    return render_template('index.html')

@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    username = data.get('username').lower().replace(" ", "")
    
    if User.query.filter_by(email=email).first(): 
        return jsonify({"status": "error", "message": "Email is already registered!"}), 400
    if User.query.filter_by(username=username).first(): 
        return jsonify({"status": "error", "message": "Username is already taken!"}), 400
        
    new_user = User(
        name=data.get('name'), 
        username=username, 
        email=email, 
        password=generate_password_hash(data.get('password'), method='pbkdf2:sha256'), 
        is_verified=False
    )
    
    db.session.add(new_user)
    db.session.add(Notification(email=email, title="Welcome! 👋", message="Thanks for creating an account! Verify your email to unlock all features."))
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Account created! You can now log in."})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    login_id = data.get('login_id', '').strip()
    password = data.get('password')
    
    user = User.query.filter((User.email == login_id) | (User.username == login_id.lower().replace(" ", ""))).first()
    
    if user and check_password_hash(user.password, password):
        session.clear() 
        session.permanent = True
        session['user_email'] = user.email
        return jsonify({"status": "success", "message": "Logged in successfully!", "is_premium": user.is_premium, "is_banned": user.is_banned})
        
    return jsonify({"status": "error", "message": "Invalid username/email or password!"}), 401

@app.route('/logout', methods=['POST'])
def logout(): 
    session.clear()
    return jsonify({"status": "success"})

@app.route('/api/send-verification-otp', methods=['POST'])
def send_verification_otp():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    email = user.email
    otp = str(random.randint(100000, 999999))
    EmailOTP.query.filter_by(email=email).delete() 
    
    db.session.add(EmailOTP(email=email, otp=otp, expiry=datetime.utcnow() + timedelta(minutes=15)))
    db.session.commit()
    
    send_system_email(email, "Verify your Email", f"Your 6-digit verification code is:\n\n<h2>{otp}</h2>\n\nThis expires in 15 minutes.")
    return jsonify({"status": "success", "message": "OTP sent to your email!"})

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    otp = request.json.get('otp')
    otp_record = EmailOTP.query.filter_by(email=user.email, otp=otp).first()
    
    if not otp_record or datetime.utcnow() > otp_record.expiry: 
        return jsonify({"status": "error", "message": "Invalid or expired OTP!"}), 400
        
    user.is_verified = True
    db.session.delete(otp_record)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Email Verified Successfully!"})

def get_user_badges(user):
    badges = []
    if user.is_banned: 
        badges.append({"name": "Banned 🚫", "class": "badge-banned"})
    else:
        r = getattr(user, 'role', 'member')
        if r == 'owner': 
            badges.append({"name": "Owner 👑", "class": "badge-owner"})
        elif r == 'admin': 
            badges.append({"name": "Admin 🛡️", "class": "badge-admin"})
        elif r == 'staff': 
            badges.append({"name": "Staff 🛠️", "class": "badge-staff"})
            
        if getattr(user, 'is_friend', False): 
            badges.append({"name": "Friend 🤝", "class": "badge-friend"})
            
        if r not in ['owner', 'admin']:
            if user.is_premium: 
                badges.append({"name": "Premium ⭐", "class": "badge-premium"})
            elif r == 'member': 
                badges.append({"name": "Member", "class": "badge-basic"})
    return badges

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session:
        return jsonify({"error": "Not logged in"}), 401
        
    user = get_current_user()
    if not user: 
        return jsonify({"error": "User deleted."}), 401
        
    if user.is_banned and user.ban_expiry and datetime.utcnow() > user.ban_expiry: 
        user.is_banned = False
        user.ban_expiry = None
        db.session.commit()
        
    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry: 
        user.is_premium = False
        db.session.commit()
        
    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else ("Lifetime Access" if user.is_premium else None)
    
    return jsonify({
        "name": user.name, 
        "username": getattr(user, 'username', 'user'), 
        "email": user.email, 
        "is_verified": getattr(user, 'is_verified', False), 
        "is_premium": user.is_premium, 
        "expiry": expiry_str, 
        "photo": user.profile_photo, 
        "is_banned": user.is_banned, 
        "badges": get_user_badges(user), 
        "role": getattr(user, 'role', 'member'), 
        "has_staff_access": getattr(user, 'role', 'member') in ['staff', 'admin', 'owner'], 
        "earnings": getattr(user, 'earnings', 0)
    })

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Not logged in"}), 401
        
    data = request.json
    if data.get('name'): 
        user.name = data['name']
    if data.get('photo'): 
        user.profile_photo = data['photo']
        
    new_username = data.get('username')
    if new_username and new_username.lower().replace(" ", "") != user.username:
        new_un = new_username.lower().replace(" ", "")
        if User.query.filter_by(username=new_un).first(): 
            return jsonify({"status": "error", "message": "Username is already taken!"}), 400
        if user.username_last_changed and datetime.utcnow() < user.username_last_changed + timedelta(days=14):
            return jsonify({"status": "error", "message": "Change limit active."}), 400
        user.username = new_un
        user.username_last_changed = datetime.utcnow()
        
    db.session.commit()
    return jsonify({"status": "success", "message": "Profile updated!"})

@app.route('/api/change-password', methods=['POST'])
def change_password():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Not logged in"}), 401
        
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    
    if not check_password_hash(user.password, old_password): 
        return jsonify({"status": "error", "message": "Incorrect password!"}), 400
        
    user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    db.session.commit()
    return jsonify({"status": "success", "message": "Password updated successfully!"})

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    
    if not user: 
        return jsonify({"status": "success"})
        
    code = str(random.randint(100000, 999999))
    db.session.add(PasswordReset(email=email, code=code, expiry=datetime.utcnow() + timedelta(minutes=15)))
    db.session.commit()
    
    send_system_email(email, "Password Reset", f"Your code is: {code}")
    return jsonify({"status": "success"})

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    reset_entry = PasswordReset.query.filter_by(email=data.get('email'), code=data.get('code')).first()
    
    if not reset_entry or datetime.utcnow() > reset_entry.expiry: 
        return jsonify({"status": "error", "message": "Invalid code!"}), 400
        
    user = User.query.filter_by(email=data.get('email')).first()
    if user: 
        user.password = generate_password_hash(data.get('new_password'), method='pbkdf2:sha256')
        db.session.delete(reset_entry)
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"status": "error"}), 404

@app.route('/submit-upi-payment', methods=['POST'])
def submit_upi_payment():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    data = request.json
    plan = data.get('plan')
    
    if not getattr(user, 'is_verified', False): 
        return jsonify({"error": "Please verify email first!"}), 403
        
    if data.get('is_gift'):
        if not User.query.filter_by(email=data.get('gift_email')).first(): 
            return jsonify({"error": "Recipient email not found!"}), 404
            
    promo_code = data.get('promo_code')
    promo = PromoCode.query.filter_by(code=promo_code).first() if promo_code else None
    if promo: 
        promo.uses += 1
            
    db.session.add(Transaction(
        email=user.email, 
        sender_upi=data.get('sender_upi'), 
        amount=data.get('amount'), 
        plan=plan, 
        code_id=data.get('code_id'), 
        is_gift=data.get('is_gift', False), 
        gift_recipient_email=data.get('gift_email'), 
        status='Pending'
    ))
    db.session.add(Notification(email=user.email, title="Payment Submitted ⏳", message=f"Verifying ₹{data.get('amount')}. Please wait."))
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Payment submitted! Admin will verify."})

@app.route('/api/report', methods=['POST'])
def submit_report():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    db.session.add(PlatformReport(
        reporter_email=user.email, 
        item_type=data.get('type'), 
        item_id=data.get('id'), 
        reason=data.get('reason'),
        proof=data.get('proof', '')
    ))
    db.session.add(Notification(email=user.email, title="Report Received 🚩", message="Staff will review your report shortly."))
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/api/my-purchases', methods=['GET'])
def my_purchases():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Unauthorized"}), 401
        
    purchased_code_ids = [p.code_id for p in UserCodePurchase.query.filter_by(email=user.email).all()]
    codes = PremiumCode.query.filter(PremiumCode.id.in_(purchased_code_ids)).all()
    code_list = [{"id": c.id, "title": c.title, "category": c.category, "code": c.code} for c in codes]
    
    return jsonify({"status": "success", "is_premium": user.is_premium, "codes": code_list})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    user = get_current_user()
    if not user: 
        return jsonify([])
        
    notifs = Notification.query.filter_by(email=user.email).order_by(Notification.date_created.desc()).all()
    return jsonify([{"id": n.id, "title": n.title, "message": n.message, "date": n.date_created.strftime('%b %d'), "is_read": n.is_read} for n in notifs])

@app.route('/api/notifications/read', methods=['POST'])
def read_notifications():
    user = get_current_user()
    if not user: 
        return jsonify({"status": "success"})
        
    for n in Notification.query.filter_by(email=user.email, is_read=False).all(): 
        n.is_read = True
        
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/bookmarks', methods=['GET'])
def get_bookmarks():
    user = get_current_user()
    if not user: 
        return jsonify([])
        
    marks = Bookmark.query.filter_by(email=user.email).all()
    res = []
    
    for m in marks:
        title = ""
        if m.item_type == 'free': 
            c = FreeCode.query.get(m.item_id)
            title = c.title if c else ""
        elif m.item_type == 'prem': 
            c = PremiumCode.query.get(m.item_id)
            title = c.title if c else ""
        elif m.item_type == 'prompt': 
            p = AIPrompt.query.get(m.item_id)
            title = p.title if p else ""
            
        if title: 
            res.append({"id": m.item_id, "type": m.item_type, "title": title})
            
    return jsonify(res)

@app.route('/api/creator/stats', methods=['GET'])
def creator_stats():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Unauthorized"}), 401
        
    email = user.email
    stats = []
    
    for c in FreeCode.query.filter_by(creator_email=email).all(): 
        stats.append({"title": c.title, "type": "Free", "views": c.views, "likes": c.likes, "sales": 0, "earnings": 0})
        
    for p in PremiumCode.query.filter_by(creator_email=email).all():
        sales = UserCodePurchase.query.filter_by(code_id=p.id).count()
        stats.append({"title": p.title, "type": "Premium", "views": p.views, "likes": p.likes, "sales": sales, "earnings": int(sales * p.price * 0.8)})
        
    return jsonify(stats)

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    creators = {}
    for c in FreeCode.query.all() + PremiumCode.query.all():
        if getattr(c, 'is_approved', True) and getattr(c, 'creator_email', 'admin') != 'admin':
            email = c.creator_email
            if email not in creators: 
                u = User.query.filter_by(email=email).first()
                creators[email] = {
                    "name": getattr(u, 'username', 'User') if u else "Unknown", 
                    "email": email, 
                    "username": getattr(u, 'username', 'user') if u else 'user', 
                    "score": 0
                }
            creators[email]['score'] += getattr(c, 'likes', 0) + (getattr(c, 'views', 0) // 10)
            
    top = sorted(creators.values(), key=lambda x: x['score'], reverse=True)[:5]
    return jsonify(top)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. Master Admin Check
        if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session.permanent = True
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
            
        # 2. Staff Check
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if getattr(user, 'role', 'member') in ['staff', 'admin', 'owner']:
                session.clear()
                session.permanent = True
                session['user_email'] = user.email
                return redirect(url_for('admin_dashboard'))
                
        # 3. If neither worked, show error
        error = "Invalid credentials or Access Denied."
        
    return render_template('admin.html', logged_in=check_admin_access(), error=error)

# NEW JSON LOGIN ROUTE FOR REACT
@app.route('/api/admin-login', methods=['POST'])
def api_admin_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    # Master Admin Check
    if email == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session.clear()
        session.permanent = True
        session['is_admin'] = True
        return jsonify({"status": "success", "role": "owner"})
        
    # Staff Check
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        if getattr(user, 'role', 'member') in ['staff', 'admin', 'owner']:
            session.clear()
            session.permanent = True
            session['user_email'] = user.email
            return jsonify({"status": "success", "role": user.role})
            
    return jsonify({"error": "Invalid credentials or Access Denied."}), 401

@app.route('/admin-logout')
def admin_logout(): 
    session.clear()
    return redirect('/')

@app.route('/api/admin-data')
def admin_data():
    try:
        role = get_user_role()
        if role not in ['staff', 'admin', 'owner']: 
            return jsonify({"error": "Unauthorized"}), 401
            
        current_username = "Master Admin"
        if 'user_email' in session:
            u = User.query.filter_by(email=session['user_email']).first()
            if u: 
                current_username = getattr(u, 'username', u.name)

        analytics = SiteAnalytics.query.first()
        pv = analytics.page_views if analytics else 0
        broadcast_cooldown = 0

        sys_conf = SystemConfig.query.first()
        m_mode = sys_conf.maintenance_mode if sys_conf else False

        all_tx = Transaction.query.filter_by(status='Success').all()
        revenue = sum([t.amount for t in all_tx])
        
        pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
        banned_users = [{"email": u.email, "expiry": u.ban_expiry.strftime('%b %d') if u.ban_expiry else "Perm"} for u in User.query.filter_by(is_banned=True).all()]
        
        pend_prem = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "premium", "code": c.code} for c in PremiumCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_free = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "free", "code": c.code} for c in FreeCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_prompt = [{"id": p.id, "title": p.title, "creator": getattr(p, 'creator_email', 'admin'), "type": "prompt", "code": p.prompt_text} for p in AIPrompt.query.all() if not getattr(p, 'is_approved', True)]
        
        promos_list = [{"id": p.id, "code": p.code, "discount": p.discount, "limit": p.limit, "uses": p.uses} for p in PromoCode.query.all()] if role == 'owner' else []
        
        # FIXED: Checking for 'prem' alongside 'premium'
        reports_list = []
        for r in PlatformReport.query.filter_by(status='Open').all():
            i_title = "Deleted Content"
            c_email = "Unknown"
            
            if r.item_type == 'prem' or r.item_type == 'premium': 
                obj = PremiumCode.query.get(r.item_id)
                if obj: 
                    i_title = obj.title
                    c_email = obj.creator_email
            elif r.item_type == 'free':
                obj = FreeCode.query.get(r.item_id)
                if obj: 
                    i_title = obj.title
                    c_email = obj.creator_email
            elif r.item_type == 'prompt':
                obj = AIPrompt.query.get(r.item_id)
                if obj: 
                    i_title = obj.title
                    c_email = obj.creator_email
            
            reports_list.append({
                "id": r.id, 
                "reporter": r.reporter_email.split('@')[0], 
                "type": r.item_type, 
                "item_id": r.item_id, 
                "reason": r.reason,
                "proof": getattr(r, 'proof', ''),
                "item_title": i_title, 
                "creator": c_email,
                "link": f"/code/{r.item_type}/{r.item_id}"
            })

        return jsonify({
            "current_role": role, 
            "current_username": current_username, 
            "total_users": User.query.count(), 
            "premium_users": User.query.filter_by(is_premium=True).count(), 
            "total_revenue": revenue, 
            "page_views": pv, 
            "pending_payments": pending_list, 
            "banned_users": banned_users, 
            "pending_codes": pend_prem + pend_free + pend_prompt, 
            "maintenance_mode": m_mode, 
            "promos": promos_list, 
            "reports": reports_list
        })
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

@app.route('/admin/approve-payment/<int:tx_id>', methods=['POST'])
def approve_payment(tx_id):
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    tx = Transaction.query.get(tx_id)
    if tx:
        tx.status = 'Success'
        target_email = tx.gift_recipient_email if tx.is_gift else tx.email
        
        if "Creator Tip" in tx.plan:
            try:
                creator_email = tx.plan.split(" - ")[1]
                creator = User.query.filter_by(email=creator_email).first()
                if creator: 
                    creator.earnings = getattr(creator, 'earnings', 0) + tx.amount
                    db.session.add(Notification(email=creator.email, title="Coffee Received! ☕", message=f"A user tipped you ₹{tx.amount}! Added to your wallet."))
                db.session.add(Notification(email=tx.email, title="Tip Sent! 💖", message=f"Your tip of ₹{tx.amount} was verified and sent to the creator!"))
            except Exception:
                pass
        else:
            user = User.query.filter_by(email=target_email).first()
            if user:
                if 'Pass' in tx.plan:
                    user.is_premium = True
                    if tx.plan == 'Weekly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
                    elif tx.plan == 'Monthly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
                    elif tx.plan == 'Yearly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
                    elif tx.plan == 'Lifetime Pass': user.premium_expiry = None
                elif tx.code_id: 
                    db.session.add(UserCodePurchase(email=user.email, code_id=tx.code_id))
                    code = PremiumCode.query.get(tx.code_id)
                    if code and getattr(code, 'creator_email', 'admin') != 'admin':
                        creator = User.query.filter_by(email=code.creator_email).first()
                        if creator: 
                            creator.earnings = getattr(creator, 'earnings', 0) + int(tx.amount * 0.8)
                            db.session.add(Notification(email=creator.email, title="New Sale! 💰", message=f"Someone bought {code.title}! ₹{int(tx.amount * 0.8)} added to your wallet."))
                db.session.add(Notification(email=user.email, title="Approved! 🎉", message=f"Access to {tx.plan} granted!"))
                
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/action-report', methods=['POST'])
def admin_action_report():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    report = PlatformReport.query.get(data.get('report_id'))
    if not report: 
        return jsonify({"error": "Not found"}), 404
        
    action = data.get('action')
    reply_text = data.get('reply', '').strip()
    
    if action == 'delete_content':
        # FIXED: Supports both 'prem' and 'premium' to match frontend DB logic
        if report.item_type == 'premium' or report.item_type == 'prem': 
            obj = PremiumCode.query.get(report.item_id)
        elif report.item_type == 'free': 
            obj = FreeCode.query.get(report.item_id)
        elif report.item_type == 'prompt': 
            obj = AIPrompt.query.get(report.item_id)
        else: 
            obj = None
        
        if obj: 
            creator_email = getattr(obj, 'creator_email', 'admin')
            db.session.delete(obj)
            if creator_email != 'admin':
                db.session.add(Notification(email=creator_email, title="Content Removed 🚨", message=f"Your {report.item_type} was removed by Staff due to Community Reports."))
        
        msg = f"Thank you for reporting. The {report.item_type} was reviewed and deleted."
        if reply_text: 
            msg += f"\nStaff Note: {reply_text}"
        db.session.add(Notification(email=report.reporter_email, title="Report Action Taken ✔️", message=msg))
                
    elif action == 'dismiss':
        msg = f"Your report regarding the {report.item_type} was reviewed, but no action was deemed necessary."
        if reply_text: 
            msg += f"\nStaff Note: {reply_text}"
        db.session.add(Notification(email=report.reporter_email, title="Report Reviewed ℹ️", message=msg))

    report.admin_reply = reply_text
    report.status = 'Closed'
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        def get_c_info(e):
            if not e or e == 'admin': 
                return {'name': 'Admin 👑', 'username': 'admin', 'email': 'admin'}
            u = User.query.filter_by(email=e).first()
            if u:
                icon = ""
                if u.role == 'owner': icon = " 👑"
                elif u.role == 'admin': icon = " 🛡️"
                elif u.role == 'staff': icon = " 🛠️"
                return {'name': f"{u.username}{icon}", 'username': u.username, 'email': e}
            return {'name': 'Unknown', 'username': 'unknown', 'email': 'unknown'}
            
        c_list = []
        for c in FreeCode.query.all():
            if getattr(c, 'is_approved', True):
                info = get_c_info(getattr(c, 'creator_email', 'admin'))
                c_list.append({"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "tags": getattr(c, 'tags', ''), "code": c.code, "views": getattr(c, 'views', 0), "likes": getattr(c, 'likes', 0), "creator": info['name'], "creator_username": info['username'], "creator_email": info['email']})
                
        p_list = []
        for p in PremiumCode.query.all():
            if getattr(p, 'is_approved', True):
                info = get_c_info(getattr(p, 'creator_email', 'admin'))
                p_list.append({"id": p.id, "title": p.title, "category": p.category, "tags": getattr(p, 'tags', ''), "price": p.price, "code": p.code, "views": getattr(p, 'views', 0), "likes": getattr(p, 'likes', 0), "creator": info['name'], "creator_username": info['username'], "creator_email": info['email']})
                
        pr_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text, "tags": getattr(p, 'tags', '')} for p in AIPrompt.query.all() if getattr(p, 'is_approved', True)]
        
        return jsonify({"codes": c_list, "premium_codes": p_list, "prompts": pr_list})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500


# --- ADMIN DIRECT UPLOAD ROUTES ---
@app.route('/admin/add-code', methods=['POST'])
def admin_add_code():
    if not check_admin_access():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    new_code = FreeCode(
        title=data.get('title'),
        category=data.get('category'),
        tags=data.get('tags', ''),
        code=data.get('code'),
        creator_email='admin',
        is_approved=True 
    )
    db.session.add(new_code)
    db.session.commit()
    return jsonify({"message": "Code published successfully!"}), 200

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not check_admin_access():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    new_code = PremiumCode(
        title=data.get('title'),
        category=data.get('category'),
        tags=data.get('tags', ''),
        price=int(data.get('price', 0)),
        code=data.get('code'),
        creator_email='admin',
        is_approved=True 
    )
    db.session.add(new_code)
    db.session.commit()
    return jsonify({"message": "Premium code published successfully!"}), 200

@app.route('/admin/add-prompt', methods=['POST'])
def admin_add_prompt():
    if not check_admin_access():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    new_prompt = AIPrompt(
        title=data.get('title'),
        tags=data.get('tags', ''),
        prompt_text=data.get('prompt_text'),
        creator_email='admin',
        is_approved=True 
    )
    db.session.add(new_prompt)
    db.session.commit()
    return jsonify({"message": "Prompt published successfully!"}), 200

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if not check_admin_access():
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.json
        target_email = data.get('email')
        gift_type = data.get('type')    # 'membership' or 'code'
        gift_value = data.get('value')  # 'Lifetime Pass' or the code ID

        user = User.query.filter_by(email=target_email).first()
        if not user:
            return jsonify({"error": "User email not found in database!"}), 404

        if gift_type == 'membership':
            user.is_premium = True
            if gift_value == 'Weekly Pass': 
                user.premium_expiry = datetime.utcnow() + timedelta(days=7)
            elif gift_value == 'Monthly Pass': 
                user.premium_expiry = datetime.utcnow() + timedelta(days=30)
            elif gift_value == 'Yearly Pass': 
                user.premium_expiry = datetime.utcnow() + timedelta(days=365)
            elif gift_value == 'Lifetime Pass': 
                user.premium_expiry = None
            
            db.session.add(Notification(
                email=user.email, 
                title="🎁 You received a Gift!", 
                message=f"The Admin has granted you a free {gift_value}! Please reload your web page to see the changes."
            ))

        elif gift_type == 'code':
            # Grant access to a specific premium code
            code = PremiumCode.query.get(int(gift_value))
            if not code:
                return jsonify({"error": "Premium code not found!"}), 404
            
            already_owned = UserCodePurchase.query.filter_by(email=user.email, code_id=code.id).first()
            if not already_owned:
                db.session.add(UserCodePurchase(email=user.email, code_id=code.id))
                db.session.add(Notification(
                    email=user.email, 
                    title="🎁 Premium Code Gifted!", 
                    message=f"The Admin gifted you full access to: {code.title}"
                ))

        db.session.commit()
        return jsonify({"success": True, "message": "Gift dispatched successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route('/admin/broadcast', methods=['POST'])
def admin_broadcast():
    global last_broadcast_time
    
    # 1. SERVER-SIDE COOLDOWN CHECK
    current_time = time.time()
    time_passed = current_time - last_broadcast_time
    if time_passed < 60:
        remaining = int(60 - time_passed)
        return jsonify({"success": False, "error": f"Please wait {remaining} more seconds.", "cooldown": remaining}), 429

    try:
        data = request.json
        target = data.get('target')
        title = data.get('title')
        message = data.get('message')

        if not title or not message:
            return jsonify({"success": False, "error": "Title and message required"}), 400

        if target == 'all':
            users = User.query.all()
            for user in users:
                notif = Notification(email=user.email, title=title, message=message)
                db.session.add(notif)
        else:
            user = User.query.filter_by(email=target).first()
            if not user:
                return jsonify({"success": False, "error": "User not found."}), 404
            notif = Notification(email=target, title=title, message=message)
            db.session.add(notif)
            
        db.session.commit()
        
        # 2. RECORD THE TIME OF THIS SUCCESSFUL BROADCAST
        last_broadcast_time = time.time() 
        
        return jsonify({"success": True, "message": "Broadcast sent!", "cooldown": 60})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/admin/update-role', methods=['POST'])
def admin_update_role():
    # Security: Only the Master Owner can change roles
    if get_user_role() != 'owner': 
        return jsonify({"status": "error", "message": "Unauthorized. Only the Owner can change roles."}), 403
        
    try:
        data = request.json
        email = data.get('email')
        new_role = data.get('role')
        is_friend = data.get('is_friend', False)
        send_email_flag = data.get('send_email', False)

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"status": "error", "message": "User email not found in database!"}), 404

        # Update the database values
        user.role = new_role
        user.is_friend = is_friend

        # If "Email Password" is checked, generate a random secure password
        if send_email_flag and new_role in ['staff', 'admin', 'owner']:
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user.password = generate_password_hash(temp_password, method='pbkdf2:sha256')
            
            # Send the email to the new staff member
            email_subject = "Your Staff Credentials - Source Code Hub"
            email_body = f"Welcome to the team!\n\nYour account role has been upgraded to: {new_role.upper()}\nYour temporary password is: {temp_password}\n\nPlease log in to the admin panel immediately and change your password."
            send_system_email(user.email, email_subject, email_body)

        # Notify the user on their dashboard
        db.session.add(Notification(
            email=user.email, 
            title="Role Updated 👑", 
            message=f"Your account role has been changed to {new_role.upper()}."
        ))
        
        db.session.commit()
        return jsonify({"status": "success", "message": f"Successfully updated {email} to {new_role}!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
# NEW: Quick route to instantly reclaim your Owner status after a DB Reset
@app.route('/init-admin')
def init_admin():
    # Looks for the email you registered with and forcefully upgrades it
    user = User.query.filter_by(email='mayankbhatt934@gmail.com').first()
    if user:
        user.role = 'owner'
        user.is_verified = True
        db.session.commit()
        return "SUCCESS! You are now the Owner. Please return to the Admin Panel and login."
    return "User not found. Please register an account on the main website first!"

@app.route('/create-superuser')
def create_superuser():
    test_email = "test@superuser.com"
    test_password = "test"
    
    # Check if the account already exists
    user = User.query.filter_by(email=test_email).first()
    
    if not user:
        # Create a brand new user if it doesn't exist
        user = User(
            name="Super Tester",
            username="test_god",
            email=test_email,
            password=generate_password_hash(test_password, method='pbkdf2:sha256'),
            is_verified=True
        )
        db.session.add(user)
    
    # Force max upgrade every time this URL is visited
    user.role = 'owner'
    user.is_premium = True
    user.premium_expiry = None  # Lifetime access
    user.is_verified = True
    user.earnings = 50000       # Give some test money in the wallet
    setattr(user, 'is_friend', True) # Give the special friend badge

    db.session.commit()
    
    return f"""
    <h1 style='color: #00ff88; background: #111; padding: 20px; font-family: sans-serif;'>
        ✅ SUPERUSER CREATED SUCCESSFULLY!
    </h1>
    <h3 style='font-family: sans-serif;'>You can now log into the main website and admin panel with:</h3>
    <ul style='font-family: sans-serif; font-size: 1.2rem;'>
        <li><b>Email:</b> {test_email}</li>
        <li><b>Password:</b> {test_password}</li>
    </ul>
    <p><i>(Remember to delete this route from app.py before sharing your site with the public!)</i></p>
    """

if __name__ == '__main__': 
    app.run(debug=True)