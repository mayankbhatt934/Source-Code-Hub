import os, random, smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase, Notification

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'super_secret_key_change_this_later' 

ADMIN_USERNAME = 'mayank'
ADMIN_PASSWORD = 'password123'

DB_URL = os.environ.get('DATABASE_URL')
if DB_URL:
    if DB_URL.startswith("postgres://"): DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    if os.environ.get('VERCEL'): app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db'
    else: app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    if not SiteAnalytics.query.first(): db.session.add(SiteAnalytics(page_views=0)); db.session.commit()

# --- AUTOMATED EMAIL HELPER ---
def send_system_email(to_email, subject, body):
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    if sender_email and sender_password:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = f"Source Code Hub <{sender_email}>"
            msg['To'] = to_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, to_email, msg.as_string())
        except Exception as e: print("Email failed:", e)

@app.route('/force-db-reset')
def force_db_reset():
    db.drop_all(); db.create_all(); db.session.add(SiteAnalytics(page_views=0)); db.session.commit()
    return "DATABASE RESET SUCCESSFUL!"

@app.route('/')
def home():
    stats = SiteAnalytics.query.first(); stats.page_views += 1; db.session.commit()
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(email=data.get('email')).first(): return jsonify({"status": "error", "message": "Email is already registered!"}), 400
    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    db.session.add(User(name=data.get('name'), email=data.get('email'), password=hashed_password))
    # NEW: Welcome Notification
    db.session.add(Notification(email=data.get('email'), title="Welcome to Source Code Hub! 👋", message="Thanks for creating an account. Explore our free codes or upgrade to premium for exclusive access!"))
    db.session.commit()
    return jsonify({"status": "success", "message": "Account created successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user_email'] = user.email 
        return jsonify({"status": "success", "message": "Logged in successfully!", "is_premium": user.is_premium, "is_banned": user.is_banned})
    return jsonify({"status": "error", "message": "Invalid email or password!"}), 401

@app.route('/logout', methods=['POST'])
def logout(): session.pop('user_email', None); return jsonify({"status": "success"})

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if not user: session.pop('user_email', None); return jsonify({"error": "User deleted"}), 401
    
    if user.is_banned and user.ban_expiry and datetime.utcnow() > user.ban_expiry:
        user.is_banned = False; user.ban_expiry = None; db.session.commit()

    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry:
        user.is_premium = False; db.session.commit()
    
    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else ("Lifetime Access" if user.is_premium else None)
    return jsonify({"name": user.name, "email": user.email, "is_premium": user.is_premium, "expiry": expiry_str, "photo": user.profile_photo, "is_banned": user.is_banned})

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    data = request.json; user = User.query.filter_by(email=session['user_email']).first()
    if data.get('name'): user.name = data['name']
    if data.get('photo'): user.profile_photo = data['photo']
    db.session.commit(); return jsonify({"status": "success", "message": "Profile updated!"})

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email'); user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"status": "success", "message": "If this email exists, a code was sent."})
    code = str(random.randint(100000, 999999))
    db.session.add(PasswordReset(email=email, code=code, expiry=datetime.utcnow() + timedelta(minutes=15))); db.session.commit()
    send_system_email(email, "Source Code Hub - Password Reset Code", f"Your reset code is: {code}\n\nExpires in 15 minutes.")
    return jsonify({"status": "success", "message": "Code sent to your email!"})

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json; reset_entry = PasswordReset.query.filter_by(email=data.get('email'), code=data.get('code')).first()
    if not reset_entry or datetime.utcnow() > reset_entry.expiry: return jsonify({"status": "error", "message": "Invalid or expired code!"}), 400
    user = User.query.filter_by(email=data.get('email')).first()
    if user:
        user.password = generate_password_hash(data.get('new_password'), method='pbkdf2:sha256')
        db.session.delete(reset_entry); db.session.commit()
        return jsonify({"status": "success", "message": "Password updated successfully!"})
    return jsonify({"status": "error", "message": "User not found!"}), 404

@app.route('/submit-upi-payment', methods=['POST'])
def submit_upi_payment():
    data = request.json
    if 'user_email' not in session: return jsonify({"status": "error", "message": "Please login!"}), 401
    if data.get('is_gift'):
        recipient = User.query.filter_by(email=data.get('gift_email')).first()
        if not recipient: return jsonify({"status": "error", "message": "Recipient email not found!"}), 404

    db.session.add(Transaction(email=session['user_email'], sender_upi=data.get('sender_upi'), amount=data.get('amount'), plan=data.get('plan'), code_id=data.get('code_id'), is_gift=data.get('is_gift', False), gift_recipient_email=data.get('gift_email'), status='Pending'))
    db.session.add(Notification(email=session['user_email'], title="Payment Submitted ⏳", message=f"We are verifying your payment of ₹{data.get('amount')} for {data.get('plan')}. Please allow admin time to approve."))
    db.session.commit()
    return jsonify({"status": "success", "message": "Payment submitted! Admin will verify."})

@app.route('/api/my-purchases', methods=['GET'])
def my_purchases():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    purchased_code_ids = [p.code_id for p in UserCodePurchase.query.filter_by(email=user.email).all()]
    codes = PremiumCode.query.filter(PremiumCode.id.in_(purchased_code_ids)).all()
    code_list = [{"id": c.id, "title": c.title, "category": c.category, "code": c.code} for c in codes]
    return jsonify({"status": "success", "is_premium": user.is_premium, "codes": code_list})

# NEW: NOTIFICATIONS API
@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_email' not in session: return jsonify([])
    notifs = Notification.query.filter((Notification.email == session['user_email']) | (Notification.email == 'all')).order_by(Notification.date_created.desc()).all()
    return jsonify([{"id": n.id, "title": n.title, "message": n.message, "date": n.date_created.strftime('%b %d'), "is_read": n.is_read} for n in notifs])

@app.route('/api/notifications/read', methods=['POST'])
def read_notifications():
    if 'user_email' in session:
        notifs = Notification.query.filter_by(email=session['user_email'], is_read=False).all()
        for n in notifs: n.is_read = True
        db.session.commit()
    return jsonify({"status": "success"})

# --- ADMIN ROUTES ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD: session['is_admin'] = True; return redirect(url_for('admin_dashboard'))
        else: error = "Invalid username or password"
    if not session.get('is_admin'): return render_template('admin.html', logged_in=False, error=error)
    return render_template('admin.html', logged_in=True)

@app.route('/admin-logout')
def admin_logout(): session.pop('is_admin', None); return redirect(url_for('admin_dashboard'))

@app.route('/api/admin-data')
def admin_data():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    revenue = sum([t.amount for t in Transaction.query.filter_by(status='Success').all()])
    pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
    banned_users = [{"email": u.email, "expiry": u.ban_expiry.strftime('%b %d, %Y') if u.ban_expiry else "Permanent"} for u in User.query.filter_by(is_banned=True).all()]
    return jsonify({"total_users": User.query.count(), "premium_users": User.query.filter_by(is_premium=True).count(), "total_revenue": revenue, "page_views": SiteAnalytics.query.first().page_views, "pending_payments": pending_list, "banned_users": banned_users})

@app.route('/admin/approve-payment/<int:tx_id>', methods=['POST'])
def approve_payment(tx_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    tx = Transaction.query.get(tx_id)
    if tx:
        tx.status = 'Success'
        target_email = tx.gift_recipient_email if tx.is_gift else tx.email
        user = User.query.filter_by(email=target_email).first()
        if user:
            if 'Pass' in tx.plan:
                user.is_premium = True
                if tx.plan == 'Weekly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
                elif tx.plan == 'Monthly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
                elif tx.plan == 'Yearly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
                elif tx.plan == 'Lifetime Pass': user.premium_expiry = None
            elif tx.code_id: db.session.add(UserCodePurchase(email=user.email, code_id=tx.code_id))
            
            # AUTOMATION: SEND NOTIFICATION & EMAIL
            msg = f"Your access to {tx.plan} has been unlocked!"
            db.session.add(Notification(email=user.email, title="Payment Approved! 🎉" if not tx.is_gift else "You received a Gift! 🎁", message=msg))
            send_system_email(user.email, "Source Code Hub - Premium Unlocked!", f"Great news! {msg} Log in to your dashboard to access it.")
        
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Transaction not found"}), 404

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error", "message": "User email not found."}), 404
    if data.get('type') == 'membership':
        user.is_premium = True; plan = data.get('value')
        if plan == 'Weekly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
        elif plan == 'Monthly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
        elif plan == 'Yearly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
        elif plan == 'Lifetime Pass': user.premium_expiry = None
    elif data.get('type') == 'code': db.session.add(UserCodePurchase(email=user.email, code_id=data.get('value')))
    
    # AUTOMATION: SEND NOTIFICATION & EMAIL
    db.session.add(Notification(email=user.email, title="You got a Gift! 🎁", message="The Admin has manually gifted you premium access!"))
    send_system_email(user.email, "Source Code Hub - Gift Received! 🎁", "The Admin has gifted you premium access. Log in to check your account!")
    db.session.commit(); return jsonify({"status": "success", "message": "Gift sent successfully!"})

@app.route('/admin/ban-user', methods=['POST'])
def admin_ban_user():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error", "message": "User not found!"}), 404
    
    days = int(data.get('duration_days', 0))
    user.is_banned = True
    if days == 0: 
        user.ban_expiry = None; msg = "Permanent Ban"
    else: 
        user.ban_expiry = datetime.utcnow() + timedelta(days=days); msg = f"{days} Days Ban"
    
    db.session.add(Notification(email=user.email, title="Account Suspended 🚫", message=f"Your account has been restricted ({msg}) due to a violation of our terms."))
    db.session.commit()
    return jsonify({"status": "success", "message": f"User {user.email} banned ({msg})."})

@app.route('/admin/unban-user', methods=['POST'])
def admin_unban_user():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=request.json.get('email')).first()
    if user:
        user.is_banned = False; user.ban_expiry = None
        db.session.add(Notification(email=user.email, title="Account Restored ✅", message="Your ban has been lifted. You can now browse the platform again."))
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "User not found."}), 404

@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        code_list = [{"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "code": c.code} for c in FreeCode.query.all()]
        premium_list = [{"id": p.id, "title": p.title, "category": p.category, "price": p.price, "code": p.code} for p in PremiumCode.query.all()]
        prompt_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text} for p in AIPrompt.query.all()]
        return jsonify({"codes": code_list, "premium_codes": premium_list, "prompts": prompt_list})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/admin/add-code', methods=['POST'])
def admin_add_code():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(FreeCode(title=request.json.get('title'), category=request.json.get('category'), code=request.json.get('code')))
    db.session.add(Notification(email='all', title="New Free Code Added! 🚀", message=f"We just published: {request.json.get('title')}. Check it out now!"))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(PremiumCode(title=request.json.get('title'), category=request.json.get('category'), price=int(request.json.get('price')), code=request.json.get('code')))
    db.session.add(Notification(email='all', title="New Premium Code Added! ⭐", message=f"{request.json.get('title')} was just added to the Premium Room."))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-prompt', methods=['POST'])
def admin_add_prompt():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(AIPrompt(title=request.json.get('title'), prompt_text=request.json.get('prompt_text')))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/delete-code/<int:code_id>', methods=['DELETE'])
def delete_code(code_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    c = FreeCode.query.get(code_id); db.session.delete(c); db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/delete-premium/<int:code_id>', methods=['DELETE'])
def delete_premium(code_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    c = PremiumCode.query.get(code_id); db.session.delete(c); db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/delete-prompt/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    p = AIPrompt.query.get(prompt_id); db.session.delete(p); db.session.commit(); return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)