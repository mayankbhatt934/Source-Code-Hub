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

def check_admin_access():
    if 'user_email' in session:
        u = User.query.filter_by(email=session['user_email']).first()
        if u and u.role in ['staff', 'admin', 'owner']: return True
    return False

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
def logout(): session.pop('user_email', None); return jsonify({"status": "success"})

def get_user_badges(user):
    badges = []
    if user.is_banned: badges.append({"name": "Banned 🚫", "class": "badge-banned"})
    else:
        if user.role == 'owner': badges.append({"name": "Owner 👑", "class": "badge-owner"})
        elif user.role == 'admin': badges.append({"name": "Admin 🛡️", "class": "badge-admin"})
        elif user.role == 'staff': badges.append({"name": "Staff 🛠️", "class": "badge-staff"})
        if user.is_friend: badges.append({"name": "Friend 🤝", "class": "badge-friend"})
        if user.role not in ['owner', 'admin']:
            if user.is_premium: badges.append({"name": "Premium ⭐", "class": "badge-premium"})
            elif user.role == 'member': badges.append({"name": "Member", "class": "badge-basic"})
    return badges

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_email' not in session: return jsonify({"error": "Not logged in"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if not user: session.pop('user_email', None); return jsonify({"error": "User deleted"}), 401
    if user.is_banned and user.ban_expiry and datetime.utcnow() > user.ban_expiry: user.is_banned = False; user.ban_expiry = None; db.session.commit()
    if user.is_premium and user.premium_expiry and datetime.utcnow() > user.premium_expiry: user.is_premium = False; db.session.commit()
    expiry_str = user.premium_expiry.strftime('%B %d, %Y') if user.premium_expiry else ("Lifetime Access" if user.is_premium else None)
    return jsonify({"name": user.name, "email": user.email, "is_premium": user.is_premium, "expiry": expiry_str, "photo": user.profile_photo, "is_banned": user.is_banned, "badges": get_user_badges(user), "role": user.role, "has_staff_access": user.role in ['staff', 'admin', 'owner'], "ref_code": user.referral_code, "earnings": user.earnings})

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
    send_system_email(email, "Password Reset Code", f"Your code is: {code}")
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
    if action == 'view': code.views += 1; db.session.commit(); return jsonify({"status": "success", "views": code.views})
    elif action == 'like':
        if 'user_email' not in session: return jsonify({"error": "Login to like"}), 401
        if CodeLike.query.filter_by(email=session['user_email'], code_type=c_type, code_id=c_id).first(): return jsonify({"error": "Already liked!"}), 400
        db.session.add(CodeLike(email=session['user_email'], code_type=c_type, code_id=c_id)); code.likes += 1; db.session.commit(); return jsonify({"status": "success", "likes": code.likes})

@app.route('/api/creator/upload', methods=['POST'])
def creator_upload():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    if not user.is_premium and user.role not in ['admin', 'owner', 'staff']: return jsonify({"error": "Must be premium!"}), 403
    
    data = request.json
    sub_type = data.get('sub_type')
    
    if sub_type == 'premium':
        db.session.add(PremiumCode(title=data.get('title'), category=data.get('category'), price=int(data.get('price') or 0), code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'free':
        db.session.add(FreeCode(title=data.get('title'), category=data.get('category'), code=data.get('code'), creator_email=user.email, is_approved=False))
    elif sub_type == 'prompt':
        db.session.add(AIPrompt(title=data.get('title'), prompt_text=data.get('code'), creator_email=user.email, is_approved=False))

    db.session.add(Notification(email=user.email, title="Submission Sent 🚀", message="Your content was sent to the Staff for approval!"))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/api/creator/payout', methods=['POST'])
def request_payout():
    if 'user_email' not in session: return jsonify({"error": "Unauthorized"}), 401
    user = User.query.filter_by(email=session['user_email']).first()
    amount = int(request.json.get('amount', 0))
    if amount < 100: return jsonify({"error": "Minimum payout is ₹100"}), 400
    if user.earnings < amount: return jsonify({"error": "Insufficient balance"}), 400
    user.earnings -= amount
    db.session.add(PayoutRequest(email=user.email, amount=amount, upi_id=request.json.get('upi')))
    db.session.add(Notification(email=user.email, title="Payout Requested 💸", message=f"Your request for ₹{amount} is pending admin approval."))
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/api/public-profile/<email>', methods=['GET'])
def public_profile(email):
    u = User.query.filter_by(email=email).first()
    if not u: return jsonify({"error": "User not found"}), 404
    codes = PremiumCode.query.filter_by(creator_email=email, is_approved=True).all() + FreeCode.query.filter_by(creator_email=email, is_approved=True).all()
    code_list = [{"id": c.id, "title": c.title, "type": "Premium" if hasattr(c, 'price') else "Free"} for c in codes]
    return jsonify({"name": u.name, "photo": u.profile_photo or f"https://ui-avatars.com/api/?name={u.name}&background=00d2ff&color=fff", "badges": get_user_badges(u), "codes": code_list})

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    creators = {}
    for c in FreeCode.query.filter_by(is_approved=True).all() + PremiumCode.query.filter_by(is_approved=True).all():
        if c.creator_email != 'admin':
            if c.creator_email not in creators:
                u = User.query.filter_by(email=c.creator_email).first()
                creators[c.creator_email] = {"name": u.name if u else "Unknown", "email": c.creator_email, "score": 0}
            creators[c.creator_email]['score'] += c.likes + (c.views // 10)
    top = sorted(creators.values(), key=lambda x: x['score'], reverse=True)[:5]
    return jsonify(top)

# --- ADMIN ROUTES ---
@app.route('/admin')
def admin_dashboard():
    if not check_admin_access(): return redirect('/#page-login')
    return render_template('admin.html', logged_in=True)

@app.route('/api/admin-data')
def admin_data():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    revenue = sum([t.amount for t in Transaction.query.filter_by(status='Success').all()])
    pending_list = [{"id": t.id, "email": t.email, "plan": t.plan, "amount": t.amount, "sender_upi": t.sender_upi, "is_gift": t.is_gift, "gift_email": t.gift_recipient_email} for t in Transaction.query.filter_by(status='Pending').all()]
    banned_users = [{"email": u.email, "expiry": u.ban_expiry.strftime('%b %d') if u.ban_expiry else "Perm"} for u in User.query.filter_by(is_banned=True).all()]
    open_tickets = [{"id": t.id, "email": t.email, "subject": t.subject, "message": t.message} for t in SupportTicket.query.filter_by(status='Open').all()]
    payouts = [{"id": p.id, "email": p.email, "amount": p.amount, "upi": p.upi_id} for p in PayoutRequest.query.filter_by(status='Pending').all()]
    
    # NEW: Unified pending codes
    pend_prem = [{"id": c.id, "title": c.title, "creator": c.creator_email, "type": "premium"} for c in PremiumCode.query.filter_by(is_approved=False).all()]
    pend_free = [{"id": c.id, "title": c.title, "creator": c.creator_email, "type": "free"} for c in FreeCode.query.filter_by(is_approved=False).all()]
    pend_prompt = [{"id": p.id, "title": p.title, "creator": p.creator_email, "type": "prompt"} for p in AIPrompt.query.filter_by(is_approved=False).all()]
    
    return jsonify({"total_users": User.query.count(), "premium_users": User.query.filter_by(is_premium=True).count(), "total_revenue": revenue, "page_views": SiteAnalytics.query.first().page_views, "pending_payments": pending_list, "banned_users": banned_users, "tickets": open_tickets, "pending_codes": pend_prem + pend_free + pend_prompt, "payouts": payouts})

@app.route('/admin/approve-payment/<int:tx_id>', methods=['POST'])
def approve_payment(tx_id):
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
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
                if code and code.creator_email != 'admin':
                    creator = User.query.filter_by(email=code.creator_email).first()
                    if creator: creator.earnings += int(tx.amount * 0.8); db.session.add(Notification(email=creator.email, title="New Sale! 💰", message=f"Someone bought {code.title}! ₹{int(tx.amount * 0.8)} added to your wallet."))
            db.session.add(Notification(email=user.email, title="Approved! 🎉", message=f"Access to {tx.plan} granted!"))
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/approve-payout/<int:pid>', methods=['POST'])
def approve_payout(pid):
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    p = PayoutRequest.query.get(pid)
    if p: p.status = 'Paid'; db.session.add(Notification(email=p.email, title="Payout Sent! 💸", message=f"Your payout of ₹{p.amount} has been processed to {p.upi_id}.")); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/admin/gift', methods=['POST'])
def admin_gift():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
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
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error", "message": "User not found!"}), 404
    user.role = data.get('role', 'member'); user.is_friend = data.get('is_friend', False); db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/ban-user', methods=['POST'])
def admin_ban_user():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; user = User.query.filter_by(email=data.get('email')).first()
    if not user: return jsonify({"status": "error"}), 404
    days = int(data.get('duration_days', 0)); user.is_banned = True
    user.ban_expiry = None if days == 0 else datetime.utcnow() + timedelta(days=days)
    db.session.commit(); return jsonify({"status": "success"})

@app.route('/admin/unban-user', methods=['POST'])
def admin_unban_user():
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
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
        db.session.add(Notification(email=obj.creator_email, title="Approved! 🌟", message=f"Your {item_type} '{obj.title}' is now live!"))
        db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/content', methods=['GET'])
def get_content():
    try:
        def get_c_name(e):
            if e == 'admin': return 'Admin'
            u = User.query.filter_by(email=e).first(); return u.name if u else 'Unknown'
        c_list = [{"id": c.id, "title": c.title, "category": getattr(c, 'category', 'Single Page'), "code": c.code, "views": c.views, "likes": c.likes, "creator": get_c_name(c.creator_email), "creator_email": c.creator_email} for c in FreeCode.query.filter_by(is_approved=True).all()]
        p_list = [{"id": p.id, "title": p.title, "category": p.category, "price": p.price, "code": p.code, "views": p.views, "likes": p.likes, "creator": get_c_name(p.creator_email), "creator_email": p.creator_email} for p in PremiumCode.query.filter_by(is_approved=True).all()]
        pr_list = [{"id": p.id, "title": p.title, "prompt_text": p.prompt_text} for p in AIPrompt.query.filter_by(is_approved=True).all()]
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
    if not check_admin_access(): return jsonify({"error": "Unauthorized"}), 401
    data = request.json; item_id = data.get('id'); item_type = data.get('type')
    if item_type == 'premium': obj = PremiumCode.query.get(item_id)
    elif item_type == 'free': obj = FreeCode.query.get(item_id)
    elif item_type == 'prompt': obj = AIPrompt.query.get(item_id)
    if obj: db.session.delete(obj); db.session.commit(); return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404

if __name__ == '__main__': app.run(debug=True)