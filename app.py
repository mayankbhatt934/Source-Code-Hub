import os, random, smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'super_secret_key_change_this_later' 

ADMIN_USERNAME = 'mayank'
ADMIN_PASSWORD = 'password123'

DB_URL = os.environ.get('DATABASE_URL')
if DB_URL:
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    if os.environ.get('VERCEL'): app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db'
    else: app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    if not SiteAnalytics.query.first():
        db.session.add(SiteAnalytics(page_views=0))
        db.session.commit()

@app.route('/force-db-reset')
def force_db_reset():
    db.drop_all()
    db.create_all()
    if not SiteAnalytics.query.first():
        db.session.add(SiteAnalytics(page_views=0))
        db.session.commit()
    return "DATABASE RESET SUCCESSFUL!"

@app.route('/')
def home():
    stats = SiteAnalytics.query.first()
    stats.page_views += 1
    db.session.commit()
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(email=data.get('email')).first(): return jsonify({"status": "error", "message": "Email is already registered!"}), 400
    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    db.session.add(User(name=data.get('name'), email=data.get('email'), password=hashed_password))
    db.session.commit()
    return jsonify({"status": "success", "message": "Account created successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user_email'] = user.email 
        return jsonify({"status": "success", "message": "Logged in successfully!", "is_premium": user.is_premium})
    return jsonify({"status": "error", "message": "Invalid email or password!"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    return jsonify({"status": "success"})

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry:
        user.is_premium = False; db.session.commit()
    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else ("Lifetime Access" if user.is_premium else None)
    return jsonify({"name": user.name, "email": user.email, "is_premium": user.is_premium, "expiry": expiry_str, "photo": user.profile_photo})

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    data = request.json
    user = User.query.filter_by(email=session['user_email']).first()
    if data.get('name'): user.name = data['name']
    if data.get('photo'): user.profile_photo = data['photo']
    db.session.commit()
    return jsonify({"status": "success", "message": "Profile updated!"})

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"status": "success", "message": "If this email exists, a code was sent."})
    code = str(random.randint(100000, 999999))
    db.session.add(PasswordReset(email=email, code=code, expiry=datetime.utcnow() + timedelta(minutes=15)))
    db.session.commit()
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    if sender_email and sender_password:
        try:
            msg = MIMEText(f"Your Source Code Hub password reset code is: {code}\n\nThis code expires in 15 minutes.")
            msg['Subject'] = 'Source Code Hub - Password Reset Code'
            msg['From'] = f"Source Code Hub Support <{sender_email}>"
            msg['To'] = email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, email, msg.as_string())
        except Exception as e: print("Email failed to send:", e)
    return jsonify({"status": "success", "message": "Code sent to your email!"})

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    reset_entry = PasswordReset.query.filter_by(email=data.get('email'), code=data.get('code')).first()
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
    if 'user_email' not in session: return jsonify({"status": "error", "message": "Please login to buy premium!"}), 401
    
    if data.get('is_gift'):
        recipient = User.query.filter_by(email=data.get('gift_email')).first()
        if not recipient: return jsonify({"status": "error", "message": "Recipient email not found! They must create an account first."}), 404

    new_tx = Transaction(
        email=session['user_email'], 
        sender_upi=data.get('sender_upi'), # CHANGED: Saving UPI ID
        amount=data.get('amount'), 
        plan=data.get('plan'), 
        code_id=data.get('code_id'),
        is_gift=data.get('is_gift', False),
        gift_recipient_email=data.get('gift_email'),
        status='Pending'
    )
    db.session.add(new_tx)
    db.session.commit()
    return jsonify({"status": "success", "message": "Payment submitted! Admin will verify."})

@app.route('/api/my-purchases', methods=['GET'])
def my_purchases():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    purchases = UserCodePurchase.query.filter_by(email=user.email).all()
    purchased_code_ids = [p.code_id for p in purchases]
    codes = PremiumCode.query.filter(PremiumCode.id.in_(purchased_code_ids)).all()
    code_list = [{"id": c.id, "title": c.title, "category": c.category, "code": c.code} for c in codes]
    return jsonify({"status": "success", "is_premium": user.is_premium, "codes": code_list})

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    error = None
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True  
            return redirect(url_for('admin_dashboard'))
        else: error = "Invalid username or password"
    if not session.get('is_admin'): return render_template('admin.html', logged_in=False, error=error)
    return render_template('admin.html', logged_in=True)

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None) 
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin-data')
def admin_data():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    revenue = sum([t.amount for t in Transaction.query.filter_by(status='Success').all()])
    pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
    return jsonify({"total_users": User.query.count(), "premium_users": User.query.filter_by(is_premium=True).count(), "total_revenue": revenue, "page_views": SiteAnalytics.query.first().page_views, "pending_payments": pending_list})

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
            elif tx.code_id:
                db.session.add(UserCodePurchase(email=user.email, code_id=tx.code_id))
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Transaction not found"}), 404

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error", "message": "User email not found."}), 404
    
    if data.get('type') == 'membership':
        user.is_premium = True
        plan = data.get('value')
        if plan == 'Weekly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
        elif plan == 'Monthly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
        elif plan == 'Yearly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
        elif plan == 'Lifetime Pass': user.premium_expiry = None
    elif data.get('type') == 'code':
        db.session.add(UserCodePurchase(email=user.email, code_id=data.get('value')))
    
    db.session.commit()
    return jsonify({"status": "success", "message": "Gift sent successfully!"})

@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        codes = FreeCode.query.all()
        prompts = AIPrompt.query.all()
        premium = PremiumCode.query.all()
        code_list = [{"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "code": c.code} for c in codes]
        premium_list = [{"id": p.id, "title": p.title, "category": p.category, "price": p.price, "code": p.code} for p in premium]
        prompt_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text} for p in prompts]
        return jsonify({"codes": code_list, "premium_codes": premium_list, "prompts": prompt_list})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/admin/add-code', methods=['POST'])
def admin_add_code():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(FreeCode(title=request.json.get('title'), category=request.json.get('category'), code=request.json.get('code')))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(PremiumCode(title=request.json.get('title'), category=request.json.get('category'), price=int(request.json.get('price')), code=request.json.get('code')))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-prompt', methods=['POST'])
def admin_add_prompt():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(AIPrompt(title=request.json.get('title'), prompt_text=request.json.get('prompt_text')))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/delete-code/<int:code_id>', methods=['DELETE'])
def delete_code(code_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    c = FreeCode.query.get(code_id)
    if c: db.session.delete(c); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/delete-premium/<int:code_id>', methods=['DELETE'])
def delete_premium(code_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    c = PremiumCode.query.get(code_id)
    if c: db.session.delete(c); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/delete-prompt/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    p = AIPrompt.query.get(prompt_id)
    if p: db.session.delete(p); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)