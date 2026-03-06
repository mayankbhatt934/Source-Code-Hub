import os
import random
import smtplib
import string
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase, Notification, SupportTicket, CodeLike, PayoutRequest, Review, Bookmark, Comment, EmailOTP, SystemConfig, PromoCode, PlatformReport

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
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
    if request.endpoint in ['static', 'admin_dashboard', 'admin_data', 'toggle_maintenance', 'admin_logout', 'login', 'force_db_reset']:
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

@app.route('/code/<item_type>/<int:item_id>')
def view_seo_item(item_type, item_id):
    item = None
    if item_type == 'free': 
        item = FreeCode.query.get_or_404(item_id)
    elif item_type == 'prem': 
        item = PremiumCode.query.get_or_404(item_id)
    elif item_type == 'prompt': 
        item = AIPrompt.query.get_or_404(item_id)
    
    if not getattr(item, 'is_approved', True): 
        return "Item not available.", 404
    
    title = item.title
    category = getattr(item, 'category', "AI Prompt")
    price = getattr(item, 'price', 0)
    price_text = f"₹{price}" if price > 0 else "Free Open Source"
    
    seo_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} | Source Code Hub</title>
        <meta name="description" content="Download '{title}' ({category}). Get high-performance scripts, website templates, and AI prompts exclusively on Source Code Hub.">
        <script type="application/ld+json">
        {{ "@context": "https://schema.org/", "@type": "Product", "name": "{title}", "description": "{category} code snippet available on Source Code Hub.", "offers": {{ "@type": "Offer", "url": "{request.url}", "priceCurrency": "INR", "price": "{price}" }} }}
        </script>
        <style>
            body {{ background: #0f0c29; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; text-align: center; }}
            .box {{ background: #1a1a1a; padding: 40px; border-radius: 12px; border: 1px solid #00d2ff; max-width: 500px; box-shadow: 0 10px 40px rgba(0,210,255,0.1); }}
            a {{ background: linear-gradient(90deg, #00d2ff, #3a7bd5); color: #000; padding: 12px 25px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; margin-top: 25px; transition: 0.3s; }}
            a:hover {{ box-shadow: 0 0 20px rgba(0,210,255,0.4); transform: translateY(-2px); }}
        </style>
    </head>
    <body>
        <div class="box">
            <span style="color: #00d2ff; font-weight: bold; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 1px;">{category}</span>
            <h1 style="margin-top: 10px; margin-bottom: 10px;">{title}</h1>
            <p style="color: #aaa; margin-bottom: 20px;">Price: <strong style="color: #00ff88;">{price_text}</strong></p>
            <p style="line-height: 1.6; color: #ccc;">This code is safely hosted on the Source Code Hub platform. Click below to view the full script, access the download, and read community reviews.</p>
            <a href="/">Open in Dashboard</a>
        </div>
    </body>
    </html>
    """
    return seo_html

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

@app.route('/api/validate-promo', methods=['POST'])
def validate_promo():
    data = request.json
    promo = PromoCode.query.filter_by(code=data.get('code', '').upper()).first()
    
    if not promo: 
        return jsonify({"error": "Invalid code"}), 404
        
    if promo.limit > 0 and promo.uses >= promo.limit: 
        return jsonify({"error": "Fully claimed!"}), 400
        
    amount = data.get('amount', 0)
    new_amt = max(0, amount - int(amount * (promo.discount / 100)))
    return jsonify({"status": "success", "new_amount": new_amt, "discount": promo.discount})

# SPRINT 2: TIPPING AND REPORTS
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
        reason=data.get('reason')
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

@app.route('/api/submit-review', methods=['POST'])
def submit_review():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    data = request.json
    purchased = UserCodePurchase.query.filter_by(email=user.email, code_id=data.get('code_id')).first()
    
    if not purchased and not user.is_premium and getattr(user, 'role', 'member') not in ['admin', 'owner', 'staff']: 
        return jsonify({"error": "Purchase required."}), 403
        
    db.session.add(Review(email=user.email, code_id=data.get('code_id'), rating=data.get('rating'), comment=data.get('comment')))
    db.session.commit()
    
    return jsonify({"status": "success"})

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

@app.route('/api/tickets', methods=['GET', 'POST'])
def handle_tickets():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    if request.method == 'POST': 
        db.session.add(SupportTicket(email=user.email, subject=request.json.get('subject'), message=request.json.get('message')))
        db.session.commit()
        return jsonify({"status": "success"})
        
    tickets = SupportTicket.query.filter_by(email=user.email).order_by(SupportTicket.date_created.desc()).all()
    return jsonify([{"id": t.id, "subject": t.subject, "message": t.message, "admin_reply": t.admin_reply, "status": t.status} for t in tickets])

@app.route('/api/interact-code', methods=['POST'])
def interact_code():
    data = request.json
    c_type = data.get('type')
    c_id = data.get('id')
    action = data.get('action')
    
    code = FreeCode.query.get(c_id) if c_type == 'free' else PremiumCode.query.get(c_id)
    if not code: 
        return jsonify({"error": "Not found"}), 404
        
    if action == 'view': 
        if hasattr(code, 'views'): 
            code.views += 1
        db.session.commit()
        return jsonify({"status": "success", "views": getattr(code, 'views', 0)})
        
    elif action == 'like':
        user = get_current_user()
        if not user: 
            return jsonify({"error": "Login to like"}), 401
            
        if CodeLike.query.filter_by(email=user.email, code_type=c_type, code_id=c_id).first(): 
            return jsonify({"error": "Already liked!"}), 400
            
        db.session.add(CodeLike(email=user.email, code_type=c_type, code_id=c_id))
        if hasattr(code, 'likes'): 
            code.likes += 1
        db.session.commit()
        return jsonify({"status": "success", "likes": getattr(code, 'likes', 0)})

@app.route('/api/toggle-bookmark', methods=['POST'])
def toggle_bookmark():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    email = user.email
    b = Bookmark.query.filter_by(email=email, item_type=data.get('type'), item_id=data.get('id')).first()
    
    if b: 
        db.session.delete(b)
        action = "removed"
    else: 
        db.session.add(Bookmark(email=email, item_type=data.get('type'), item_id=data.get('id')))
        action = "added"
        
    db.session.commit()
    return jsonify({"status": "success", "action": action})

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

@app.route('/api/comments/<item_type>/<int:item_id>', methods=['GET'])
def get_comments(item_type, item_id):
    comments = Comment.query.filter_by(item_type=item_type, item_id=item_id).order_by(Comment.date_created.desc()).all()
    res = []
    
    for c in comments:
        u = User.query.filter_by(email=c.email).first()
        uname = u.username if u and hasattr(u, 'username') else c.email.split('@')[0]
        res.append({"user": uname, "text": c.text, "date": c.date_created.strftime('%b %d')})
        
    return jsonify(res)

@app.route('/api/add-comment', methods=['POST'])
def add_comment():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    if not getattr(user, 'is_verified', False): 
        return jsonify({"error": "Verify email first!"}), 403
        
    data = request.json
    db.session.add(Comment(email=user.email, item_type=data.get('type'), item_id=data.get('id'), text=data.get('text')))
    db.session.commit()
    return jsonify({"status": "success"})

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

@app.route('/api/creator/upload', methods=['POST'])
def creator_upload():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Session expired."}), 401
        
    if not user.is_premium and getattr(user, 'role', 'member') not in ['admin', 'owner', 'staff']: 
        return jsonify({"error": "Must be premium!"}), 403
        
    data = request.json
    sub_type = data.get('sub_type')
    
    try: 
        price_int = int(data.get('price')) if data.get('price') else 0
    except ValueError: 
        price_int = 0
        
    if sub_type == 'premium': 
        db.session.add(PremiumCode(title=data.get('title'), category=data.get('category'), tags=data.get('tags', ''), price=price_int, code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'free': 
        db.session.add(FreeCode(title=data.get('title'), category=data.get('category'), tags=data.get('tags', ''), code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'prompt': 
        db.session.add(AIPrompt(title=data.get('title'), prompt_text=data.get('code'), tags=data.get('tags', ''), creator_email=user.email, is_approved=False))
        
    db.session.add(Notification(email=user.email, title="Submission Sent 🚀", message="Sent to Staff for approval!"))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/creator/payout', methods=['POST'])
def request_payout():
    user = get_current_user()
    if not user: 
        return jsonify({"error": "Unauthorized"}), 401
        
    amount = int(request.json.get('amount', 0))
    if amount < 100: 
        return jsonify({"error": "Minimum payout is ₹100"}), 400
        
    if getattr(user, 'earnings', 0) < amount: 
        return jsonify({"error": "Insufficient balance"}), 400
        
    user.earnings -= amount
    db.session.add(PayoutRequest(email=user.email, amount=amount, upi_id=request.json.get('upi')))
    db.session.add(Notification(email=user.email, title="Payout Requested 💸", message=f"Your request for ₹{amount} is pending."))
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/api/public-profile/<username>', methods=['GET'])
def public_profile(username):
    if username.lower() == 'admin':
        u_name = "Admin 👑"
        u_photo = f"https://ui-avatars.com/api/?name=Admin&background=00d2ff&color=fff"
        u_badges = [{"name": "Owner 👑", "class": "badge-owner"}]
        all_prem = PremiumCode.query.filter_by(creator_email='admin').all()
        all_free = FreeCode.query.filter_by(creator_email='admin').all()
    else:
        u = User.query.filter_by(username=username).first()
        if not u: 
            return jsonify({"error": "User not found"}), 404
            
        u_name = u.username
        u_photo = u.profile_photo or f"https://ui-avatars.com/api/?name={u.name}&background=00d2ff&color=fff"
        u_badges = get_user_badges(u)
        all_prem = PremiumCode.query.filter_by(creator_email=u.email).all()
        all_free = FreeCode.query.filter_by(creator_email=u.email).all()
        
    codes = [c for c in all_prem if getattr(c, 'is_approved', True)] + [c for c in all_free if getattr(c, 'is_approved', True)]
    code_list = [{"id": c.id, "title": c.title, "type": "Premium" if hasattr(c, 'price') else "Free"} for c in codes]
    
    return jsonify({"name": u_name, "photo": u_photo, "badges": u_badges, "codes": code_list})

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
    if request.method == 'POST':
        staff_email = request.form.get('email')
        password = request.form.get('password')
        
        if staff_email == ADMIN_USERNAME and password == ADMIN_PASSWORD: 
            session.clear() 
            session.permanent = True
            session['is_admin'] = True
            return redirect('/admin')
            
        user = User.query.filter_by(email=staff_email).first()
        if user and check_password_hash(user.password, password):
            if getattr(user, 'role', 'member') in ['staff', 'admin', 'owner']: 
                session.clear() 
                session.permanent = True
                session['user_email'] = user.email
                return redirect('/admin')
            else: 
                return render_template('admin.html', logged_in=False, error="Access Denied.")
                
        return render_template('admin.html', logged_in=False, error="Invalid email or password.")
        
    if not check_admin_access(): 
        return render_template('admin.html', logged_in=False)
        
    return render_template('admin.html', logged_in=True)

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
        
        if analytics and analytics.last_broadcast_time:
            time_since = datetime.utcnow() - analytics.last_broadcast_time
            if time_since < timedelta(minutes=2): 
                broadcast_cooldown = 120 - int(time_since.total_seconds())

        sys_conf = SystemConfig.query.first()
        m_mode = sys_conf.maintenance_mode if sys_conf else False

        all_tx = Transaction.query.filter_by(status='Success').all()
        revenue = sum([t.amount for t in all_tx])
        
        pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
        banned_users = [{"email": u.email, "expiry": u.ban_expiry.strftime('%b %d') if u.ban_expiry else "Perm"} for u in User.query.filter_by(is_banned=True).all()]
        open_tickets = [{"id": t.id, "email": t.email, "subject": t.subject, "message": t.message} for t in SupportTicket.query.filter_by(status='Open').all()]
        
        payouts = [{"id": p.id, "email": p.email, "amount": p.amount, "upi": p.upi_id} for p in getattr(PayoutRequest, 'query').filter_by(status='Pending').all()] if hasattr(PayoutRequest, 'query') else []
        pend_prem = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "premium", "code": c.code} for c in PremiumCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_free = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "free", "code": c.code} for c in FreeCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_prompt = [{"id": p.id, "title": p.title, "creator": getattr(p, 'creator_email', 'admin'), "type": "prompt", "code": p.prompt_text} for p in AIPrompt.query.all() if not getattr(p, 'is_approved', True)]
        
        promos_list = [{"id": p.id, "code": p.code, "discount": p.discount, "limit": p.limit, "uses": p.uses} for p in PromoCode.query.all()] if role == 'owner' else []
        reports_list = [{"id": r.id, "reporter": r.reporter_email.split('@')[0], "type": r.item_type, "item_id": r.item_id, "reason": r.reason} for r in PlatformReport.query.filter_by(status='Open').all()]

        return jsonify({
            "current_role": role, 
            "current_username": current_username, 
            "total_users": User.query.count(), 
            "premium_users": User.query.filter_by(is_premium=True).count(), 
            "total_revenue": revenue, 
            "page_views": pv, 
            "pending_payments": pending_list, 
            "banned_users": banned_users, 
            "tickets": open_tickets, 
            "pending_codes": pend_prem + pend_free + pend_prompt, 
            "payouts": payouts, 
            "broadcast_cooldown": broadcast_cooldown, 
            "maintenance_mode": m_mode, 
            "promos": promos_list, 
            "reports": reports_list
        })
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

@app.route('/admin/toggle-maintenance', methods=['POST'])
def toggle_maintenance():
    if get_user_role() != 'owner': 
        return jsonify({"error": "Unauthorized"}), 403
        
    conf = SystemConfig.query.first()
    if not conf: 
        conf = SystemConfig(maintenance_mode=False)
        db.session.add(conf)
        
    conf.maintenance_mode = not conf.maintenance_mode
    db.session.commit()
    return jsonify({"status": "success", "mode": conf.maintenance_mode})

@app.route('/admin/promo', methods=['POST'])
def add_promo():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    code = data.get('code').upper()
    
    if PromoCode.query.filter_by(code=code).first(): 
        return jsonify({"error": "Code already exists"}), 400
        
    db.session.add(PromoCode(code=code, discount=int(data.get('discount')), limit=int(data.get('limit'))))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/promo/<int:id>', methods=['DELETE'])
def delete_promo(id):
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    p = PromoCode.query.get(id)
    if p: 
        db.session.delete(p)
        db.session.commit()
        
    return jsonify({"status": "success"})

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
                    if tx.plan == 'Weekly Pass': 
                        user.premium_expiry = datetime.utcnow() + timedelta(days=7)
                    elif tx.plan == 'Monthly Pass': 
                        user.premium_expiry = datetime.utcnow() + timedelta(days=30)
                    elif tx.plan == 'Yearly Pass': 
                        user.premium_expiry = datetime.utcnow() + timedelta(days=365)
                    elif tx.plan == 'Lifetime Pass': 
                        user.premium_expiry = None
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

@app.route('/admin/approve-payout/<int:pid>', methods=['POST'])
def approve_payout(pid):
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    p = PayoutRequest.query.get(pid)
    p.status = 'Paid'
    db.session.add(Notification(email=p.email, title="Payout Sent! 💸", message=f"Your payout of ₹{p.amount} has been processed to {p.upi_id}."))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user: 
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    if data.get('type') == 'membership':
        user.is_premium = True
        plan = data.get('value')
        if plan == 'Weekly Pass': 
            user.premium_expiry = datetime.utcnow() + timedelta(days=7)
        elif plan == 'Monthly Pass': 
            user.premium_expiry = datetime.utcnow() + timedelta(days=30)
        elif plan == 'Yearly Pass': 
            user.premium_expiry = datetime.utcnow() + timedelta(days=365)
        elif plan == 'Lifetime Pass': 
            user.premium_expiry = None
    elif data.get('type') == 'code': 
        db.session.add(UserCodePurchase(email=user.email, code_id=data.get('value')))
        
    db.session.add(Notification(email=user.email, title="Gift! 🎁", message="Admin gifted you access!"))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/update-role', methods=['POST'])
def admin_update_role():
    try:
        curr_role = get_user_role()
        if curr_role not in ['admin', 'owner']: 
            return jsonify({"error": "Unauthorized"}), 403
            
        data = request.json
        email = data.get('email')
        target_role = data.get('role', 'member')
        is_friend = data.get('is_friend', False)
        send_email = data.get('send_email', False)
        
        if curr_role == 'admin' and target_role in ['admin', 'owner']: 
            return jsonify({"status": "error", "message": "Admins cannot grant Admin or Owner roles!"}), 403
            
        user = User.query.filter_by(email=email).first()
        if not user: 
            return jsonify({"status": "error", "message": "User not found! They must register on the main website first."}), 404
            
        if not getattr(user, 'is_verified', False): 
            return jsonify({"status": "error", "message": "Target user must verify their email in their profile before receiving Staff access."}), 400
            
        old_role = getattr(user, 'role', 'member')
        old_friend = getattr(user, 'is_friend', False)
        
        if curr_role == 'admin' and old_role in ['admin', 'owner']: 
            return jsonify({"status": "error", "message": "You cannot modify an Admin or Owner!"}), 403
            
        user.role = target_role
        user.is_friend = is_friend
        new_password = None
        
        if send_email:
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        if old_role != target_role: 
            db.session.add(Notification(email=user.email, title="Role Updated 👑", message=f"Your role is now: {target_role.upper()}!"))
            
        if is_friend and not old_friend: 
            db.session.add(Notification(email=user.email, title="New Badge 🤝", message="You have been granted the Friend badge!"))
            
        db.session.commit()
        
        if send_email and new_password:
            msg = f"Hello,\n\nYou have been assigned the {target_role.upper()} role.\n\nLogin Portal: https://mayanksourcecodehub.vercel.app/admin\nEmail: {email}\nNew Password: {new_password}\n\nPlease keep these secure."
            send_system_email(email, f"Source Code Hub - {target_role.upper()} Access", msg)
            return jsonify({"status": "success", "message": f"Role updated! New password emailed to {email}."})
            
        return jsonify({"status": "success", "message": "Roles updated successfully."})
        
    except Exception as e: 
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

@app.route('/admin/ban-user', methods=['POST'])
def admin_ban_user():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    user = User.query.filter_by(email=request.json.get('email')).first()
    if not user: 
        return jsonify({"status": "error"}), 404
        
    days = int(request.json.get('duration_days', 0))
    user.is_banned = True
    user.ban_expiry = None if days == 0 else datetime.utcnow() + timedelta(days=days)
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/admin/unban-user', methods=['POST'])
def admin_unban_user():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    user = User.query.filter_by(email=request.json.get('email')).first()
    if user:
        user.is_banned = False
        user.ban_expiry = None
        db.session.commit()
        
    return jsonify({"status": "success"})

@app.route('/admin/reply-ticket', methods=['POST'])
def admin_reply_ticket():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    ticket = SupportTicket.query.get(request.json.get('ticket_id'))
    if ticket:
        ticket.admin_reply = request.json.get('reply')
        ticket.status = 'Closed'
        db.session.add(Notification(email=ticket.email, title="Ticket Replied 🛠️", message=f"Staff replied to: {ticket.subject}"))
        db.session.commit()
        
    return jsonify({"status": "success"})

@app.route('/admin/dismiss-report/<int:id>', methods=['POST'])
def dismiss_report(id):
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    report = PlatformReport.query.get(id)
    if report: 
        report.status = 'Closed'
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/approve-submission', methods=['POST'])
def approve_submission():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    item_id = data.get('id')
    item_type = data.get('type')
    
    if item_type == 'premium': 
        obj = PremiumCode.query.get(item_id)
    elif item_type == 'free': 
        obj = FreeCode.query.get(item_id)
    elif item_type == 'prompt': 
        obj = AIPrompt.query.get(item_id)
    else: 
        obj = None
        
    if obj: 
        obj.is_approved = True
        db.session.add(Notification(email=getattr(obj, 'creator_email', 'admin'), title="Approved! 🌟", message=f"Your {item_type} '{obj.title}' is now live!"))
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/send-notification', methods=['POST'])
def admin_send_notification():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    analytics = SiteAnalytics.query.first()
    if analytics and analytics.last_broadcast_time:
        time_since = datetime.utcnow() - analytics.last_broadcast_time
        if time_since < timedelta(minutes=2): 
            return jsonify({"error": "Universal Cooldown active.", "cooldown": 120 - int(time_since.total_seconds())}), 429
            
    data = request.json
    target = data.get('target', 'all')
    title = data.get('title')
    message = data.get('message')
    
    if target == 'all':
        for u in User.query.all(): 
            db.session.add(Notification(email=u.email, title=title, message=message))
    else: 
        db.session.add(Notification(email=target, title=title, message=message))
        
    if analytics: 
        analytics.last_broadcast_time = datetime.utcnow()
        
    db.session.commit()
    return jsonify({"status": "success", "cooldown": 120})

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
                revs = Review.query.filter_by(code_id=p.id).all()
                avg_rating = round(sum([r.rating for r in revs]) / len(revs), 1) if revs else 0
                all_revs = [{"user": r.email.split('@')[0], "rating": r.rating, "comment": r.comment} for r in revs]
                p_list.append({"id": p.id, "title": p.title, "category": p.category, "tags": getattr(p, 'tags', ''), "price": p.price, "code": p.code, "views": getattr(p, 'views', 0), "likes": getattr(p, 'likes', 0), "creator": info['name'], "creator_username": info['username'], "creator_email": info['email'], "avg_rating": avg_rating, "reviews": all_revs})
                
        pr_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text, "tags": getattr(p, 'tags', '')} for p in AIPrompt.query.all() if getattr(p, 'is_approved', True)]
        
        return jsonify({"codes": c_list, "premium_codes": p_list, "prompts": pr_list})
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

@app.route('/admin/add-code', methods=['POST'])
def admin_add_code():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    creator = session.get('user_email', 'admin')
    db.session.add(FreeCode(title=request.json.get('title'), category=request.json.get('category'), code=request.json.get('code'), tags=request.json.get('tags', ''), creator_email=creator, is_approved=True))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    creator = session.get('user_email', 'admin')
    db.session.add(PremiumCode(title=request.json.get('title'), category=request.json.get('category'), price=int(request.json.get('price')), tags=request.json.get('tags', ''), code=request.json.get('code'), creator_email=creator, is_approved=True))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/add-prompt', methods=['POST'])
def admin_add_prompt():
    if not check_admin_access(): 
        return jsonify({"error": "Unauthorized"}), 401
        
    creator = session.get('user_email', 'admin')
    db.session.add(AIPrompt(title=request.json.get('title'), prompt_text=request.json.get('prompt_text'), tags=request.json.get('tags', ''), creator_email=creator, is_approved=True))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/delete-submission', methods=['POST'])
def delete_submission():
    if get_user_role() not in ['admin', 'owner']: 
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    item_id = data.get('id')
    item_type = data.get('type')
    reason = data.get('reason', 'Does not meet platform guidelines.') 
    
    if item_type == 'premium': 
        obj = PremiumCode.query.get(item_id)
    elif item_type == 'free': 
        obj = FreeCode.query.get(item_id)
    elif item_type == 'prompt': 
        obj = AIPrompt.query.get(item_id)
    else: 
        obj = None
        
    if obj: 
        creator_email = getattr(obj, 'creator_email', 'admin')
        if creator_email != 'admin': 
            db.session.add(Notification(email=creator_email, title="Submission Rejected ❌", message=f"Your {item_type} '{obj.title}' was rejected. Reason: {reason}"))
        db.session.delete(obj)
        db.session.commit()
        return jsonify({"status": "success"})
        
    return jsonify({"error": "Item not found"}), 404

@app.after_request
def add_cache_control(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__': 
    app.run(debug=True)