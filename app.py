import os, random, smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
# Imported all your new Hybrid Marketplace models!
from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase

# --- FOLDER PATH CONFIGURATION ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'super_secret_key_change_this_later' 

ADMIN_USERNAME = 'mayank'
ADMIN_PASSWORD = 'password123'

# --- SMART DATABASE CONFIGURATION ---
DB_URL = os.environ.get('DATABASE_URL')

if DB_URL:
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    if os.environ.get('VERCEL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not SiteAnalytics.query.first():
        db.session.add(SiteAnalytics(page_views=0))
        db.session.commit()

# ==========================================
# SECRET DB RESET ROUTE (FIXES THE LOADING BUG)
# ==========================================
@app.route('/force-db-reset')
def force_db_reset():
    db.drop_all() # Wipes the old confused tables
    db.create_all() # Rebuilds them perfectly with your new categories
    if not SiteAnalytics.query.first():
        db.session.add(SiteAnalytics(page_views=0))
        db.session.commit()
    return "DATABASE RESET SUCCESSFUL! Postgres is now perfectly synced. You can go back to your website!"

# ==========================================
# STANDARD ROUTES
# ==========================================
@app.route('/')
def home():
    stats = SiteAnalytics.query.first()
    stats.page_views += 1
    db.session.commit()
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    existing_user = User.query.filter_by(email=data.get('email')).first()
    if existing_user: return jsonify({"status": "error", "message": "Email is already registered!"}), 400

    hashed_password = generate_password_hash(data.get('password'), method='pbkdf2:sha256')
    new_user = User(name=data.get('name'), email=data.get('email'), password=hashed_password)
    db.session.add(new_user)
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
        user.is_premium = False
        db.session.commit()

    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else "Lifetime Access"
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

# --- PASSWORD RESET ROUTES ---
@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"status": "success", "message": "If this email exists, a code was sent."})

    code = str(random.randint(100000, 999999))
    new_reset = PasswordReset(email=email, code=code, expiry=datetime.utcnow() + timedelta(minutes=15))
    db.session.add(new_reset)
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
        db.session.delete(reset_entry)
        db.session.commit()
        return jsonify({"status": "success", "message": "Password updated successfully!"})
    return jsonify({"status": "error", "message": "User not found!"}), 404

# --- ADMIN DASHBOARD ROUTES ---
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
    pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "utr": t.utr_number} for t in Transaction.query.filter_by(status='Pending').all()]
    return jsonify({
        "total_users": User.query.count(), 
        "premium_users": User.query.filter_by(is_premium=True).count(), 
        "total_revenue": revenue, 
        "page_views": SiteAnalytics.query.first().page_views, 
        "pending_payments": pending_list
    })

# --- DYNAMIC CONTENT ROUTES ---
@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        codes = FreeCode.query.all()
        prompts = AIPrompt.query.all()
        premium = PremiumCode.query.all() # Fetching Premium codes!
        
        # Safely fetching categories and prices
        code_list = [{"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "code": c.code} for c in codes]
        premium_list = [{"id": p.id, "title": p.title, "category": p.category, "price": p.price, "code": p.code} for p in premium]
        prompt_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text} for p in prompts]
        
        return jsonify({"codes": code_list, "premium_codes": premium_list, "prompts": prompt_list})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_premium = PremiumCode(
        title=data.get('title'), 
        category=data.get('category'), 
        price=int(data.get('price')), 
        code=data.get('code')
    )
    db.session.add(new_premium)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route('/admin/delete-premium/<int:code_id>', methods=['DELETE'])
def delete_premium(code_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    code = PremiumCode.query.get(code_id)
    if code:
        db.session.delete(code)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Code not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)