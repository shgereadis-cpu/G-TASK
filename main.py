# ======================================================
# G-TASK MANAGER: GMAIL ACCOUNT CREATION TASK MANAGER
# Version: 2.0 (FINAL BACKEND: PostgreSQL/SQLAlchemy)
# Author: Gemini (AI)
# ======================================================

import os
import time
import hashlib
import hmac
import secrets
import requests # <--- ታክሏል
import json     # <--- ታክሏል
from datetime import datetime, timedelta
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv # ሚስጥሮችን ከአካባቢ ተለዋዋጮች (Secrets) ለመጫን

# --- 0. ENV SETUP & CONFIGURATION ---
load_dotenv() # በ Replit ላይ አውቶማቲክ ይሰራል
app = Flask(__name__)

# !!! [ማስተካከያ] SECRET KEYን በቀጥታ ኮድ ውስጥ ማስገባት !!!
# ይህ ለጊዜያዊ Deployment ስህተትን ለመፍታት ብቻ ነው። ደህንነቱ ዝቅተኛ ነው።
# ⚠️ ለቋሚ አጠቃቀም SECRET_KEYን ከ os.environ.get('SECRET_KEY') እንዲወስድ ያድርጉ።
app.secret_key = 'Kq7bYxZ_3u9sP2hG_vR4wF1mJ_tL5cY_8oE'

# Database Configuration (Neon/PostgreSQL or SQLite fallback)
# የ DATABASE_URL ሚስጥር ከ Replit Secrets ይነበባል
database_url = os.environ.get('DATABASE_URL', 'sqlite:///g_task_manager.db')
# Remove extra quotes and fix HTML encoding if present
database_url = database_url.strip("'\"").replace('&amp;', '&')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

MIN_PAYOUT = 40.00
PAYOUT_AMOUNT_PER_TASK = 10.00

# --- 1. DATABASE MODELS (SQLAlchemy Models) ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    total_earned = db.Column(db.Float, default=0.0)
    pending_payout = db.Column(db.Float, default=0.0)
    telegram_id = db.Column(db.String(50), unique=True, nullable=True)
    telegram_login_token = db.Column(db.String(256), nullable=True)
    telegram_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    tasks = db.relationship('Task', backref='worker', lazy='dynamic')
    payouts = db.relationship('Payout', backref='requester', lazy='dynamic')
    ad_views = db.relationship('AdView', backref='viewer', lazy='dynamic')

class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    gmail_username = db.Column(db.String(120), unique=True, nullable=False)
    gmail_password = db.Column(db.String(120), nullable=False)
    recovery_email = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default='AVAILABLE') # AVAILABLE, ASSIGNED, COMPLETED
    date_added = db.Column(db.DateTime, default=func.now())
    
    # Relationship
    task = db.relationship('Task', backref='inventory_item', uselist=False)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    completion_code = db.Column(db.String(100))
    status = db.Column(db.String(20), default='PENDING') # PENDING, SUBMITTED, VERIFIED, REJECTED
    date_assigned = db.Column(db.DateTime, default=func.now())
    date_completed = db.Column(db.DateTime)

class Payout(db.Model):
    __tablename__ = 'payouts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='REQUESTED') # REQUESTED, PAID, REJECTED
    payment_method = db.Column(db.String(50), nullable=False) # Telebirr, CBE, M-Pesa
    recipient_name = db.Column(db.String(255), nullable=False)
    payment_details = db.Column(db.String(255), nullable=False)
    date_requested = db.Column(db.DateTime, default=func.now())
    date_paid = db.Column(db.DateTime)

# ማስታወቂያ ሞዴሎች (Ad Models)
class Ad(db.Model):
    __tablename__ = 'ads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    embed_url = db.Column(db.String(255), nullable=False)
    reward_amount = db.Column(db.Float, nullable=False)
    required_view_time = db.Column(db.Integer, default=60)
    is_active = db.Column(db.Boolean, default=True)
    views = db.relationship('AdView', backref='ad_item', lazy='dynamic')

class AdView(db.Model):
    __tablename__ = 'ad_views'
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('ads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='PENDING') # PENDING, REWARDED
    date_viewed = db.Column(db.DateTime, default=func.now())

class DailyCheckIn(db.Model):
    __tablename__ = 'daily_check_ins'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_in_date = db.Column(db.Date, default=func.current_date())
    date_checked_in = db.Column(db.DateTime, default=func.now())
    
    # Unique constraint: one check-in per user per day
    __table_args__ = (db.UniqueConstraint('user_id', 'check_in_date', name='unique_daily_checkin'),)

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    device_fingerprint = db.Column(db.String(256), nullable=False)  # Hash of device info
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text, nullable=False)
    device_name = db.Column(db.String(100), nullable=True)
    last_activity = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    date_added = db.Column(db.DateTime, default=func.now())
    is_verified = db.Column(db.Boolean, default=False)

# --- 2. DATABASE INIT & HELPER FUNCTIONS ---

def init_db():
    """የዳታቤዝ ሠንጠረዦችን ይፈጥራል እና ነባሪ አድሚን ያስገባል።"""
    with app.app_context():
        # ሁሉንም ሞዴሎች በመጠቀም ሠንጠረዦችን ይፈጥራል
        db.create_all() 
        
        # Add missing columns to payouts table
        from sqlalchemy import text, inspect
        try:
            inspector = inspect(db.engine)
            payouts_columns = [col['name'] for col in inspector.get_columns('payouts')]
            
            columns_to_add = [
                ('payment_method', "VARCHAR(50) DEFAULT 'Telebirr'"),
                ('recipient_name', "VARCHAR(255) DEFAULT ''"),
                ('payment_details', "VARCHAR(255) DEFAULT ''"),
            ]
            
            for col_name, col_def in columns_to_add:
                if col_name not in payouts_columns:
                    try:
                        db.session.execute(text(f'ALTER TABLE payouts ADD COLUMN {col_name} {col_def}'))
                        db.session.commit()
                        print(f"Added {col_name} column to payouts table")
                    except Exception as e:
                        db.session.rollback()
                        print(f"Column {col_name} already exists or error: {str(e)[:100]}")
        except Exception as e:
            print(f"Error checking columns: {str(e)[:100]}")
        
        # ነባሪ የአድሚን አካውንት - only if ADMIN_USERNAME and ADMIN_PASSWORD are set
        admin_username = os.environ.get('ADMIN_USERNAME')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if admin_username and admin_password:
            if not User.query.filter_by(username=admin_username).first():
                admin_user = User(
                    username=admin_username, 
                    password_hash=generate_password_hash(admin_password), 
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"Admin account created: {admin_username}")
        else:
            print("ማስጠንቀቂያ: ADMIN_USERNAME እና ADMIN_PASSWORD secrets አልተገኙም። የአድሚን account ለመፍጠር እነዚህን በSecrets ውስጥ ያስገቡ።")

init_db()


def is_logged_in():
    return 'user_id' in session

def check_admin_access():
    if not is_logged_in(): return False
    with app.app_context():
        user = User.query.filter_by(id=session['user_id']).with_entities(User.is_admin).first()
        return user and user.is_admin

def generate_device_fingerprint(request):
    """Generate device fingerprint from request headers."""
    ip = request.remote_addr or 'unknown'
    user_agent = request.headers.get('User-Agent', 'unknown')
    # Create hash of IP + User-Agent for device identification
    device_string = f"{ip}|{user_agent}"
    fingerprint = hashlib.sha256(device_string.encode()).hexdigest()
    return fingerprint, ip, user_agent

def validate_device(user_id, request):
    """Validate device and check for violations. Returns (is_valid, message)."""
    fingerprint, ip, user_agent = generate_device_fingerprint(request)
    
    with app.app_context():
        # Check if user already has this device
        existing_device = Device.query.filter_by(
            user_id=user_id, 
            device_fingerprint=fingerprint
        ).first()
        
        if existing_device:
            existing_device.last_activity = func.now()
            db.session.commit()
            return True, "Device recognized"
        
        # Check if this device is used by other users
        other_users = Device.query.filter_by(device_fingerprint=fingerprint).all()
        if other_users:
            print(f"🚨 FRAUD ALERT: Device {fingerprint} used by multiple users!")
            return False, f"⛔ ይህ устройство በሌላ ተጠቃሚ ተባዝቷል። ሊጠቀሙ አይችሉም።"
        
        # Register new device
        new_device = Device(
            user_id=user_id,
            device_fingerprint=fingerprint,
            ip_address=ip,
            user_agent=user_agent
        )
        db.session.add(new_device)
        db.session.commit()
        return True, "New device registered"

def generate_telegram_login_token(user):
    """Generate a temporary login token for Telegram user (24 hours expiry)."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=24)
    user.telegram_login_token = token
    user.telegram_token_expires = expires
    db.session.commit()
    print(f"✅ Generated login token for {user.username}")
    return token

# -----------------------------------------------------------
# ⭐ [አዲስ/የተስተካከለ] ቴሌግራም ኖቲፊኬሽን ተግባር (Inline Button and Formatting)
# -----------------------------------------------------------
def send_notification_to_all_telegram_users(message):
    import requests
    import json
    
    # ቶከኑን ከ BOT_TOKEN አካባቢ ተለዋዋጭ ያግኙ
    TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
    
    if not TELEGRAM_BOT_TOKEN:
        print("Warning: BOT_TOKEN not configured. Skipping notification.")
        return
    
    # ⚠️ እዚህ ላይ የRender ዌብሳይት ዩአርኤልዎን ያስገቡ! (በእርስዎ ትክክለኛ ዩአርኤል ይተኩ)
    WEBSITE_URL = 'https://g-task.onrender.com' 
    
    with app.app_context():
        users_with_telegram = User.query.filter(User.telegram_id.isnot(None)).all()
        
        if not users_with_telegram:
            print("No users with Telegram ID found for notification.")
            return
        
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # የ Inline Keyboard መዋቅር
        keyboard = {
            "inline_keyboard": [[{
                "text": "➡️ ዌብሳይቱን ይጎብኙ",
                "url": WEBSITE_URL
            }]]
        }
        
        # የተሻሻለው መልዕክት (በ Markdown)
        formatted_message = f"✨ **አዲስ ክምችት ገብቷል!** ✨\n\n{message}"
        
        success_count = 0
        failed_count = 0
        
        for user in users_with_telegram:
            try:
                response = requests.post(api_url, data={
                    'chat_id': user.telegram_id,
                    'text': formatted_message,
                    'parse_mode': 'Markdown', # Markdown formattingን አንቃ
                    'reply_markup': json.dumps(keyboard)
                })
                if response.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"Error sending to user {user.username}: {str(e)}")
        
        print(f"Telegram notifications sent: {success_count} successful, {failed_count} failed")

# -----------------------------------------------------------

@app.context_processor
def inject_global_vars():
    return dict(is_admin=check_admin_access, min_payout=MIN_PAYOUT)


# --- 3. WORKER ROUTES (የሰራተኛ መንገዶች) ---

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('እባክዎ ሁሉንም መስኮች ይሙሉ!', 'error')
        elif len(password) < 6:
            flash('የይለፍ ቃል ቢያንስ 6 ፊደላት መሆን አለበት።', 'error')
        else:
            try:
                with app.app_context():
                    password_hash = generate_password_hash(password)
                    new_user = User(username=username, password_hash=password_hash)
                    db.session.add(new_user)
                    db.session.commit()
                flash('በተሳካ ሁኔታ ተመዝግበዋል! አሁን መግባት ይችላሉ።', 'success')
                return redirect(url_for('login'))
            except Exception:
                flash(f'የተጠቃሚ ስም "{username}" ቀድሞውኑ አለ። ሌላ ይሞክሩ።', 'error')
    return render_template('signup.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form
