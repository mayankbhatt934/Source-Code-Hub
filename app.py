import os, random, smtplib, string
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from models import db, User, Transaction, SiteAnalytics, PasswordReset, FreeCode, PremiumCode, AIPrompt, UserCodePurchase, Notification, SupportTicket, CodeLike, PayoutRequest

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = 'super_secret_key_change_this_later' 

ADMIN_USERNAME = 'mayank'; ADMIN_PASSWORD = 'password123'

DB_URL = os.environ.get('DATABASE_URL')
if DB_URL:
    if DB_URL.startswith("postgres://"): DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/sourcehub.db' if os.environ.get('VERCEL') else f'sqlite:///{os.path.join(BASE_DIR, "sourcehub.db")}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    if not SiteAnalytics.query.first(): db.session.add(SiteAnalytics(page_views=0)); db.session.commit()

def send_system_email(to_email, subject, body):
    sender_email = os.environ.get('MAIL_USERNAME'); sender_password = os.environ.get('MAIL_PASSWORD')
    if sender_email and sender_password:
        try:
            msg = MIMEText(body); msg['Subject'] = subject; msg['From'] = f"Source Code Hub <{sender_email}>"; msg['To'] = to_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server: server.login(sender_email, sender_password); server.sendmail(sender_email, to_email, msg.as_string())
        except: pass

def get_user_role():
    if 'user_email' in session:
        u = User.query.filter_by(email=session['user_email']).first()
        return getattr(u, 'role', 'member') if u else 'member'
    elif session.get('is_admin'):
        return 'owner'
    return 'member'

def check_admin_access():
    return get_user_role() in ['staff', 'admin', 'owner']

@app.route('/force-db-reset')
def force_db_reset(): db.drop_all(); db.create_all(); db.session.add(SiteAnalytics(page_views=0)); db.session.commit(); return "DATABASE RESET SUCCESSFUL!"

@app.route('/')
def home(): stats = SiteAnalytics.query.first(); stats.page_views += 1; db.session.commit(); return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(email=data.get('email')).first(): return jsonify({"status": "error", "message": "Email is already registered!"}), 400
    new_user = User(name=data.get('name'), email=data.get('email'), password=generate_password_hash(data.get('password'), method='pbkdf2:sha256'))
    ref_code = data.get('ref_code')
    if ref_code:
        referrer = User.query.filter_by(referral_code=ref_code).first()
        if referrer:
            referrer.is_premium = True; referrer.premium_expiry = max(referrer.premium_expiry or datetime.utcnow(), datetime.utcnow()) + timedelta(days=3)
            new_user.is_premium = True; new_user.premium_expiry = datetime.utcnow() + timedelta(days=3)
            db.session.add(Notification(email=referrer.email, title="Referral Success! 🚀", message="Someone signed up using your link! You got 3 Days of Free Premium!"))
            db.session.add(Notification(email=new_user.email, title="Welcome Bonus! 🎁", message="You used an invite link and received 3 Days of Free Premium!"))
    db.session.add(new_user)
    if not ref_code: db.session.add(Notification(email=data.get('email'), title="Welcome! 👋", message="Thanks for creating an account!"))
    db.session.commit(); return jsonify({"status": "success", "message": "Account created!"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if user and check_password_hash(user.password, data.get('password')):
        session['user_email'] = user.email 
        return jsonify({"status": "success", "message": "Logged in successfully!", "is_premium": user.is_premium, "is_banned": user.is_banned})
    return jsonify({"status": "error", "message": "Invalid email or password!"}), 401

@app.route('/logout', methods=['POST'])
def logout(): session.pop('user_email', None); session.pop('is_admin', None); return jsonify({"status": "success"})

def get_user_badges(user):
    badges = []
    if user.is_banned: badges.append({"name": "Banned 🚫", "class": "badge-banned"})
    else:
        r = getattr(user, 'role', 'member')
        if r == 'owner': badges.append({"name": "Owner 👑", "class": "badge-owner"})
        elif r == 'admin': badges.append({"name": "Admin 🛡️", "class": "badge-admin"})
        elif r == 'staff': badges.append({"name": "Staff 🛠️", "class": "badge-staff"})
        if getattr(user, 'is_friend', False): badges.append({"name": "Friend 🤝", "class": "badge-friend"})
        if r not in ['owner', 'admin']:
            if user.is_premium: badges.append({"name": "Premium ⭐", "class": "badge-premium"})
            elif r == 'member': badges.append({"name": "Member", "class": "badge-basic"})
    return badges

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if not user: session.pop('user_email', None); return jsonify({"error": "User deleted"}), 401
    if user.is_banned and user.ban_expiry and datetime.utcnow() > user.ban_expiry: user.is_banned = False; user.ban_expiry = None; db.session.commit()
    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry: user.is_premium = False; db.session.commit()
    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else ("Lifetime Access" if user.is_premium else None)
    return jsonify({"name": user.name, "email": user.email, "is_premium": user.is_premium, "expiry": expiry_str, "photo": user.profile_photo, "is_banned": user.is_banned, "badges": get_user_badges(user), "role": getattr(user, 'role', 'member'), "has_staff_access": getattr(user, 'role', 'member') in ['staff', 'admin', 'owner'], "ref_code": getattr(user, 'referral_code', ''), "earnings": getattr(user, 'earnings', 0)})

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    data = request.json; user = User.query.filter_by(email=session['user_email']).first()
    if data.get('name'): user.name = data['name']
    if data.get('photo'): user.profile_photo = data['photo']
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email'); user = User.query.filter_by(email=email).first()
    if not user: return jsonify({"status": "success"})
    code = str(random.randint(100000, 999999))
    db.session.add(PasswordReset(email=email, code=code, expiry=datetime.utcnow() + timedelta(minutes=15))); db.session.commit()
    send_system_email(email, "Source Code Hub - Password Reset", f"Your reset code is: {code}\n\nExpires in 15 minutes.")
    return jsonify({"status": "success"})

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json; reset_entry = PasswordReset.query.filter_by(email=data.get('email'), code=data.get('code')).first()
    if not reset_entry or datetime.utcnow() > reset_entry.expiry: return jsonify({"status": "error", "message": "Invalid code!"}), 400
    user = User.query.filter_by(email=data.get('email')).first()
    if user: user.password = generate_password_hash(data.get('new_password'), method='pbkdf2:sha256'); db.session.delete(reset_entry); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/submit-upi-payment', methods=['POST'])
def submit_upi_payment():
    data = request.json
    if 'user_email' not in session: return jsonify({"status": "error", "message": "Please login!"}), 401
    if data.get('is_gift'):
        recipient = User.query.filter_by(email=data.get('gift_email')).first()
        if not recipient: return jsonify({"status": "error", "message": "Recipient email not found!"}), 404
    db.session.add(Transaction(email=session['user_email'], sender_upi=data.get('sender_upi'), amount=data.get('amount'), plan=data.get('plan'), code_id=data.get('code_id'), is_gift=data.get('is_gift', False), gift_recipient_email=data.get('gift_email'), status='Pending'))
    db.session.add(Notification(email=session['user_email'], title="Payment Submitted ⏳", message=f"Verifying ₹{data.get('amount')}. Please wait."))
    db.session.commit(); return jsonify({"status": "success", "message": "Payment submitted! Admin will verify."})

@app.route('/api/my-purchases', methods=['GET'])
def my_purchases():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    purchased_code_ids = [p.code_id for p in UserCodePurchase.query.filter_by(email=user.email).all()]
    codes = PremiumCode.query.filter(PremiumCode.id.in_(purchased_code_ids)).all()
    code_list = [{"id": c.id, "title": c.title, "category": c.category, "code": c.code} for c in codes]
    return jsonify({"status": "success", "is_premium": user.is_premium, "codes": code_list})

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    if 'user_email' not in session: return jsonify([])
    notifs = Notification.query.filter((Notification.email == session['user_email']) | (Notification.email == 'all')).order_by(Notification.date_created.desc()).all()
    return jsonify([{"id": n.id, "title": n.title, "message": n.message, "date": n.date_created.strftime('%b %d'), "is_read": n.is_read} for n in notifs])

@app.route('/api/notifications/read', methods=['POST'])
def read_notifications():
    if 'user_email' in session:
        for n in Notification.query.filter_by(email=session['user_email'], is_read=False).all(): n.is_read = True
        db.session.commit()
    return jsonify({"status": "success"})

@app.route('/api/tickets', methods=['GET', 'POST'])
def handle_tickets():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    if request.method == 'POST':
        db.session.add(SupportTicket(email=session['user_email'], subject=request.json.get('subject'), message=request.json.get('message')))
        db.session.commit(); return jsonify({"status": "success"})
    tickets = SupportTicket.query.filter_by(email=session['user_email']).order_by(SupportTicket.date_created.desc()).all()
    return jsonify([{"id": t.id, "subject": t.subject, "message": t.message, "admin_reply": t.admin_reply, "status": t.status} for t in tickets])

@app.route('/api/interact-code', methods=['POST'])
def interact_code():
    data = request.json; c_type = data.get('type'); c_id = data.get('id'); action = data.get('action')
    code = FreeCode.query.get(c_id) if c_type == 'free' else PremiumCode.query.get(c_id)
    if not code: return jsonify({"error": "Not found"}), 404
    if action == 'view': 
        if hasattr(code, 'views'): code.views += 1
        db.session.commit(); return jsonify({"status": "success", "views": getattr(code, 'views', 0)})
    elif action == 'like':
        if 'user_email' not in session: return jsonify({"error": "Login to like"}), 401
        if CodeLike.query.filter_by(email=session['user_email'], code_type=c_type, code_id=c_id).first(): return jsonify({"error": "Already liked!"}), 400
        db.session.add(CodeLike(email=session['user_email'], code_type=c_type, code_id=c_id))
        if hasattr(code, 'likes'): code.likes += 1
        db.session.commit(); return jsonify({"status": "success", "likes": getattr(code, 'likes', 0)})

@app.route('/api/creator/upload', methods=['POST'])
def creator_upload():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if not user.is_premium and getattr(user, 'role', 'member') not in ['admin', 'owner', 'staff']: return jsonify({"error": "Must be premium!"}), 403
    
    data = request.json; sub_type = data.get('sub_type')
    if sub_type == 'premium': db.session.add(PremiumCode(title=data.get('title'), category=data.get('category'), price=int(data.get('price') or 0), code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'free': db.session.add(FreeCode(title=data.get('title'), category=data.get('category'), code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'prompt': db.session.add(AIPrompt(title=data.get('title'), prompt_text=data.get('code'), creator_email=user.email, is_approved=False))

    db.session.add(Notification(email=user.email, title="Submission Sent 🚀", message="Your content was sent to the Staff for approval!"))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/api/creator/payout', methods=['POST'])
def request_payout():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    amount = int(request.json.get('amount', 0))
    if amount < 100: return jsonify({"error": "Minimum payout is ₹100"}), 400
    if getattr(user, 'earnings', 0) < amount: return jsonify({"error": "Insufficient balance"}), 400
    user.earnings -= amount
    db.session.add(PayoutRequest(email=user.email, amount=amount, upi_id=request.json.get('upi')))
    db.session.add(Notification(email=user.email, title="Payout Requested 💸", message=f"Your request for ₹{amount} is pending admin approval."))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/api/public-profile/<email>', methods=['GET'])
def public_profile(email):
    u = User.query.filter_by(email=email).first()
    if not u: return jsonify({"error": "User not found"}), 404
    all_prem = PremiumCode.query.all(); all_free = FreeCode.query.all()
    codes = [c for c in all_prem if getattr(c, 'creator_email', '') == email and getattr(c, 'is_approved', True)] + [c for c in all_free if getattr(c, 'creator_email', '') == email and getattr(c, 'is_approved', True)]
    code_list = [{"id": c.id, "title": c.title, "type": "Premium" if hasattr(c, 'price') else "Free"} for c in codes]
    return jsonify({"name": u.name, "photo": u.profile_photo or f"https://ui-avatars.com/api/?name={u.name}&background=00d2ff&color=fff", "badges": get_user_badges(u), "codes": code_list})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    creators = {}
    for c in FreeCode.query.all() + PremiumCode.query.all():
        if getattr(c, 'is_approved', True) and getattr(c, 'creator_email', 'admin') != 'admin':
            email = c.creator_email
            if email not in creators:
                u = User.query.filter_by(email=email).first()
                creators[email] = {"name": u.name if u else "Unknown", "email": email, "score": 0}
            creators[email]['score'] += getattr(c, 'likes', 0) + (getattr(c, 'views', 0) // 10)
    top = sorted(creators.values(), key=lambda x: x['score'], reverse=True)[:5]
    return jsonify(top)

# --- BULLETPROOF ADMIN ROUTES ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        email_or_user = request.form.get('username')
        password = request.form.get('password')
        
        if email_or_user == ADMIN_USERNAME and password == ADMIN_PASSWORD: 
            session['is_admin'] = True; return redirect('/admin')
            
        user = User.query.filter_by(email=email_or_user).first()
        if user and check_password_hash(user.password, password):
            if getattr(user, 'role', 'member') in ['staff', 'admin', 'owner']:
                session['is_admin'] = True; session['user_email'] = user.email
                return redirect('/admin')
            else: return render_template('admin.html', logged_in=False, error="Access Denied: You do not have Staff permissions.")
        return render_template('admin.html', logged_in=False, error="Invalid email or password.")

    if not check_admin_access(): return render_template('admin.html', logged_in=False)
    return render_template('admin.html', logged_in=True)

# FIXED LOGOUT: Redirects safely to homepage!
@app.route('/admin-logout')
def admin_logout(): 
    session.pop('is_admin', None)
    session.pop('user_email', None)
    return redirect('/')

@app.route('/api/admin-data')
def admin_data():
    try:
        role = get_user_role()
        if role not in ['staff', 'admin', 'owner']: return jsonify({"error": "Unauthorized"}), 401
        
        revenue = sum([t.amount for t in Transaction.query.filter_by(status='Success').all()])
        pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
        banned_users = [{"email": u.email, "expiry": u.ban_expiry.strftime('%b %d') if u.ban_expiry else "Perm"} for u in User.query.filter_by(is_banned=True).all()]
        open_tickets = [{"id": t.id, "email": t.email, "subject": t.subject, "message": t.message} for t in SupportTicket.query.filter_by(status='Open').all()]
        
        payouts = [{"id": p.id, "email": p.email, "amount": p.amount, "upi": p.upi_id} for p in getattr(PayoutRequest, 'query').filter_by(status='Pending').all()] if hasattr(PayoutRequest, 'query') else []
        pend_prem = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "premium"} for c in PremiumCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_free = [{"id": c.id, "title": c.title, "creator": getattr(c, 'creator_email', 'admin'), "type": "free"} for c in FreeCode.query.all() if not getattr(c, 'is_approved', True)]
        pend_prompt = [{"id": p.id, "title": p.title, "creator": getattr(p, 'creator_email', 'admin'), "type": "prompt"} for p in AIPrompt.query.all() if not getattr(p, 'is_approved', True)]
        
        pv = SiteAnalytics.query.first().page_views if SiteAnalytics.query.first() else 0
        return jsonify({"current_role": role, "total_users": User.query.count(), "premium_users": User.query.filter_by(is_premium=True).count(), "total_revenue": revenue, "page_views": pv, "pending_payments": pending_list, "banned_users": banned_users, "tickets": open_tickets, "pending_codes": pend_prem + pend_free + pend_prompt, "payouts": payouts})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/admin/approve-payment/<int:tx_id>', methods=['POST'])
def approve_payment(tx_id):
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    tx = Transaction.query.get(tx_id)
    if tx:
        tx.status = 'Success'; target_email = tx.gift_recipient_email if tx.is_gift else tx.email
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
                    if creator: creator.earnings = getattr(creator, 'earnings', 0) + int(tx.amount * 0.8); db.session.add(Notification(email=creator.email, title="New Sale! 💰", message=f"Someone bought {code.title}! ₹{int(tx.amount * 0.8)} added to your wallet."))
            db.session.add(Notification(email=user.email, title="Approved! 🎉", message=f"Access to {tx.plan} granted!"))
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/approve-payout/<int:pid>', methods=['POST'])
def approve_payout(pid):
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    p = PayoutRequest.query.get(pid)
    if p: p.status = 'Paid'; db.session.add(Notification(email=p.email, title="Payout Sent! 💸", message=f"Your payout of ₹{p.amount} has been processed to {p.upi_id}.")); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error", "message": "User not found"}), 404
    if data.get('type') == 'membership':
        user.is_premium = True; plan = data.get('value')
        if plan == 'Weekly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=7)
        elif plan == 'Monthly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=30)
        elif plan == 'Yearly Pass': user.premium_expiry = datetime.utcnow() + timedelta(days=365)
        elif plan == 'Lifetime Pass': user.premium_expiry = None
    elif data.get('type') == 'code': db.session.add(UserCodePurchase(email=user.email, code_id=data.get('value')))
    db.session.add(Notification(email=user.email, title="Gift! 🎁", message="Admin gifted you access!")); db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/update-role', methods=['POST'])
def admin_update_role():
    curr_role = get_user_role()
    if curr_role not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    email = data.get('email'); target_role = data.get('role', 'member')
    is_friend = data.get('is_friend', False); send_email = data.get('send_email', False)
    
    if curr_role == 'admin' and target_role in ['admin', 'owner']: return jsonify({"status": "error", "message": "Admins cannot grant Admin or Owner roles!"}), 403
        
    user = User.query.filter_by(email=email).first()
    new_password = None
    
    if not user:
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
        user = User(name=email.split('@')[0], email=email, password=hashed, role=target_role, is_friend=is_friend)
        db.session.add(user)
        db.session.commit()
        db.session.add(Notification(email=user.email, title="Welcome to the Team! 💼", message=f"You have been hired as {target_role.upper()}!"))
        if is_friend: db.session.add(Notification(email=user.email, title="New Badge 🤝", message="You received the Friend badge!"))
    else:
        old_role = getattr(user, 'role', 'member')
        old_friend = getattr(user, 'is_friend', False)
        
        if curr_role == 'admin' and old_role in ['admin', 'owner']: return jsonify({"status": "error", "message": "You cannot modify an Admin or Owner!"}), 403

        user.role = target_role
        user.is_friend = is_friend
        if send_email:
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
            
        if old_role != target_role: db.session.add(Notification(email=user.email, title="Role Updated 👑", message=f"Your role is now: {target_role.upper()}!"))
        if is_friend and not old_friend: db.session.add(Notification(email=user.email, title="New Badge 🤝", message="You have been granted the Friend badge!"))
            
    db.session.commit()
    
    if send_email and new_password:
        msg = f"Hello,\n\nYou have been assigned the {target_role.upper()} role.\nLogin: https://mayanksourcecodehub.vercel.app/admin\nEmail: {email}\nPassword: {new_password}"
        send_system_email(email, f"Source Code Hub - {target_role.upper()} Access", msg)
        return jsonify({"status": "success", "message": f"Role updated! Password emailed to {email}."})
    return jsonify({"status": "success", "message": "Roles updated successfully."})

@app.route('/admin/ban-user', methods=['POST'])
def admin_ban_user():
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error"}), 404
    days = int(data.get('duration_days', 0)); user.is_banned = True
    user.ban_expiry = None if days == 0 else datetime.utcnow() + timedelta(days=days)
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/unban-user', methods=['POST'])
def admin_unban_user():
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    user = User.query.filter_by(email=request.json.get('email')).first()
    if user: user.is_banned = False; user.ban_expiry = None; db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/reply-ticket', methods=['POST'])
def admin_reply_ticket():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; ticket = SupportTicket.query.get(data.get('ticket_id'))
    if ticket: ticket.admin_reply = data.get('reply'); ticket.status = 'Closed'; db.session.add(Notification(email=ticket.email, title="Ticket Replied 🛠️", message=f"Staff replied to: {ticket.subject}")); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/approve-submission', methods=['POST'])
def approve_submission():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; item_id = data.get('id'); item_type = data.get('type')
    if item_type == 'premium': obj = PremiumCode.query.get(item_id)
    elif item_type == 'free': obj = FreeCode.query.get(item_id)
    elif item_type == 'prompt': obj = AIPrompt.query.get(item_id)
    else: return jsonify({"error": "Invalid type"}), 400
    
    if obj: 
        obj.is_approved = True
        db.session.add(Notification(email=getattr(obj, 'creator_email', 'admin'), title="Approved! 🌟", message=f"Your {item_type} '{obj.title}' is now live!"))
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        def get_c_name(e):
            if e == 'admin': return 'Admin 👑'
            u = User.query.filter_by(email=e).first(); return u.name if u else 'Unknown'
        c_list = [{"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "code": c.code, "views": getattr(c, 'views', 0), "likes": getattr(c, 'likes', 0), "creator": get_c_name(getattr(c, 'creator_email', 'admin')), "creator_email": getattr(c, 'creator_email', 'admin')} for c in FreeCode.query.all() if getattr(c, 'is_approved', True)]
        p_list = [{"id": p.id, "title": p.title, "category": p.category, "price": p.price, "code": p.code, "views": getattr(p, 'views', 0), "likes": getattr(p, 'likes', 0), "creator": get_c_name(getattr(p, 'creator_email', 'admin')), "creator_email": getattr(p, 'creator_email', 'admin')} for p in PremiumCode.query.all() if getattr(p, 'is_approved', True)]
        pr_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text} for p in AIPrompt.query.all() if getattr(p, 'is_approved', True)]
        return jsonify({"codes": c_list, "premium_codes": p_list, "prompts": pr_list})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/admin/add-code', methods=['POST'])
def admin_add_code():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(FreeCode(title=request.json.get('title'), category=request.json.get('category'), code=request.json.get('code'), is_approved=True))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-premium', methods=['POST'])
def admin_add_premium():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(PremiumCode(title=request.json.get('title'), category=request.json.get('category'), price=int(request.json.get('price')), code=request.json.get('code'), is_approved=True))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/add-prompt', methods=['POST'])
def admin_add_prompt():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    db.session.add(AIPrompt(title=request.json.get('title'), prompt_text=request.json.get('prompt_text'), is_approved=True))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/delete-submission', methods=['POST'])
def delete_submission():
    if get_user_role() not in ['admin', 'owner']: return jsonify({"error": "Unauthorized"}), 403
    data = request.json; item_id = data.get('id'); item_type = data.get('type')
    if item_type == 'premium': obj = PremiumCode.query.get(item_id)
    elif item_type == 'free': obj = FreeCode.query.get(item_id)
    elif item_type == 'prompt': obj = AIPrompt.query.get(item_id)
    if obj: db.session.delete(obj); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.after_request
def add_cache_control(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__': 
    app.run(debug=True)