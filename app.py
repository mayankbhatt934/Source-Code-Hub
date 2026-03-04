import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User, Transaction, SiteAnalytics

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
    # 1. Cloud Database (Neon Postgres via Vercel env variables)
    if DB_URL.startswith("postgres://"):
        DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    # 2. Local SQLite Fallback
    if os.environ.get('VERCEL'):
        # Just in case DATABASE_URL is missing on Vercel, it won't crash
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db'
    else:
        # Standard local testing on your PC
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    if not SiteAnalytics.query.first():
        db.session.add(SiteAnalytics(page_views=0))
        db.session.commit()

@app.route('/')
def home():
    stats = SiteAnalytics.query.first()
    stats.page_views += 1
    db.session.commit()
    return render_template('index.html')

# --- AUTH & PROFILE ROUTES ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"status": "error", "message": "Email is already registered!"}), 400

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(name=name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"status": "success", "message": "Account created successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        session['user_email'] = user.email 
        return jsonify({"status": "success", "message": "Logged in successfully!", "is_premium": user.is_premium})
    return jsonify({"status": "error", "message": "Invalid email or password!"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    return jsonify({"status": "success"})

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    user = User.query.filter_by(email=session['user_email']).first()
    
    # Check if premium expired
    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry:
        user.is_premium = False
        db.session.commit()

    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else None
    
    return jsonify({
        "name": user.name, 
        "email": user.email, 
        "is_premium": user.is_premium, 
        "expiry": expiry_str, 
        "photo": user.profile_photo
    })

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user_email' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    user = User.query.filter_by(email=session['user_email']).first()
    
    if data.get('name'):
        user.name = data['name']
    if data.get('photo'):
        user.profile_photo = data['photo']
        
    db.session.commit()
    return jsonify({"status": "success", "message": "Profile updated!"})

# --- PAYMENT ROUTES ---
@app.route('/submit-upi-payment', methods=['POST'])
def submit_upi_payment():
    data = request.json
    if 'user_email' not in session:
        return jsonify({"status": "error", "message": "Please login to buy premium!"}), 401

    new_tx = Transaction(
        email=session['user_email'], 
        utr_number=data.get('utr_number'), 
        amount=data.get('amount'), 
        plan=data.get('plan'),
        status='Pending'
    )
    db.session.add(new_tx)
    db.session.commit()
    return jsonify({"status": "success", "message": "Payment submitted! Admin will verify and activate your account shortly."})

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True  
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid username or password"
    if not session.get('is_admin'): return render_template('admin.html', logged_in=False, error=error)
    return render_template('admin.html', logged_in=True)

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None) 
    return redirect(url_for('admin_dashboard'))

@app.route('/api/admin-data')
def admin_data():
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    users_count = User.query.count()
    premium_count = User.query.filter_by(is_premium=True).count()
    success_tx = Transaction.query.filter_by(status='Success').all()
    revenue = sum([t.amount for t in success_tx])
    views = SiteAnalytics.query.first().page_views
    pending_tx = Transaction.query.filter_by(status='Pending').all()
    pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "utr": t.utr_number} for t in pending_tx]
    return jsonify({"total_users": users_count, "premium_users": premium_count, "total_revenue": revenue, "page_views": views, "pending_payments": pending_list})

@app.route('/admin/approve-payment/<int:tx_id>', methods=['POST'])
def approve_payment(tx_id):
    if not session.get('is_admin'): return jsonify({"error": "Unauthorized"}), 401
    tx = Transaction.query.get(tx_id)
    if tx:
        tx.status = 'Success'
        user = User.query.filter_by(email=tx.email).first()
        if user:
            user.is_premium = True
            # Calculate Expiry Date based on plan
            if tx.plan == 'Weekly': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
            elif tx.plan == 'Monthly': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
            elif tx.plan == 'Yearly': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Transaction not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)