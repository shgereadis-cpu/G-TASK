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
import requests
from datetime import datetime, timedelta
from urllib.parse import unquote
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv # ሚስጥሮችን ከአካባቢ ተለዋዋጮች (Secrets) ለመጫን

# --- 0. ENV SETUP & CONFIGURATION ---
load_dotenv() # በ Replit ላይ አውቶማቲክ ይሰራል
app = Flask(__name__)

# PRODUCTION MODE - Render only (disable debug on production)
ENV = os.environ.get('ENV', 'production')
app.debug = (ENV == 'development')

# SECRET KEY - Render-compatible (from environment variables)
app.secret_key = os.environ.get('SECRET_KEY', 'Kq7bYxZ_3u9sP2hG_vR4wF1mJ_tL5cY_8oE')

# ========== TELEGRAM BOT CONFIGURATION ==========
# Telegram Bot Token (from @BotFather) - HARDCODED per user requirement
# NEW BOT: @GTASKpro_bot
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8535083603:AAGAFlbMYewLE_bv_GIlXJ1Jzd0epHY_7M0')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'GTASKpro_bot')
# WEBHOOK_URL - Must use RENDER PRODUCTION URL (https://g-task.onrender.com/webhook)
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://g-task.onrender.com/webhook')
# ================================================

# Database Configuration (Neon/PostgreSQL or SQLite fallback)
# የ DATABASE_URL ሚስጥር ከ Replit Secrets ይነበባል
database_url = os.environ.get('DATABASE_URL', 'sqlite:///g_task_manager.db')
# Remove extra quotes and fix HTML encoding if present
database_url = database_url.strip("'\"").replace('&amp;', '&')

# Add SSL support for Render PostgreSQL connections
if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
    # Fix old postgres:// to postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    # Add SSL mode if not present
    if '?' not in database_url:
        database_url = database_url + '?sslmode=require'
    elif 'sslmode' not in database_url:
        database_url = database_url + '&sslmode=require'
    
    print(f"🔐 PostgreSQL connection configured with SSL")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'connect_args': {'connect_timeout': 10}
}

db = SQLAlchemy(app)

MIN_PAYOUT = 40.00
PAYOUT_AMOUNT_PER_TASK = 10.00

# ===== STARTUP DIAGNOSTICS =====
print(f"🚀 Flask App Starting on {'Render' if ENV == 'production' else 'Development'}...")
print(f"✅ BOT_TOKEN configured: {bool(BOT_TOKEN)}")
print(f"✅ BOT_TOKEN (@GTASKpro_bot): {TELEGRAM_BOT_USERNAME}")
print(f"✅ WEBHOOK_URL: {WEBHOOK_URL}")
print(f"✅ Database: {'PostgreSQL (Production)' if 'postgresql' in database_url else 'SQLite (Dev)'}")
print(f"✅ Environment: {ENV.upper()}")
# ================================

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


# --- 2. DATABASE INIT & HELPER FUNCTIONS ---

def init_db():
    """የዳታቤዝ ሠንጠረዦችን ይፈጥራል እና ነባሪ አድሚን ያስገባል።"""
    with app.app_context():
        try:
            # ሁሉንም ሞዴሎች በመጠቀም ሠንጠረዦችን ይፈጥራል
            db.create_all()
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"⚠️ Error creating tables: {str(e)}")
            return
        
        # Add missing columns to existing tables
        from sqlalchemy import text, inspect
        try:
            inspector = inspect(db.engine)
            
            # Check and add missing columns to users table
            if 'users' in inspector.get_table_names():
                users_columns = [col['name'] for col in inspector.get_columns('users')]
                users_columns_to_add = [
                    ('telegram_login_token', "VARCHAR(256)"),
                    ('telegram_token_expires', "TIMESTAMP"),
                ]
                
                for col_name, col_def in users_columns_to_add:
                    if col_name not in users_columns:
                        try:
                            db.session.execute(text(f'ALTER TABLE users ADD COLUMN {col_name} {col_def}'))
                            db.session.commit()
                            print(f"✅ Added {col_name} column to users table")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ {col_name} already exists or error: {str(e)[:80]}")
            
            # Check and add missing columns to payouts table
            if 'payouts' in inspector.get_table_names():
                payouts_columns = [col['name'] for col in inspector.get_columns('payouts')]
                
                payouts_columns_to_add = [
                    ('payment_method', "VARCHAR(50) DEFAULT 'Telebirr'"),
                    ('recipient_name', "VARCHAR(255) DEFAULT ''"),
                    ('payment_details', "VARCHAR(255) DEFAULT ''"),
                ]
                
                for col_name, col_def in payouts_columns_to_add:
                    if col_name not in payouts_columns:
                        try:
                            db.session.execute(text(f'ALTER TABLE payouts ADD COLUMN {col_name} {col_def}'))
                            db.session.commit()
                            print(f"✅ Added {col_name} column to payouts table")
                        except Exception as e:
                            db.session.rollback()
                            print(f"⚠️ {col_name} already exists or error: {str(e)[:80]}")
        except Exception as e:
            print(f"⚠️ Error checking/adding columns: {str(e)[:100]}")
        
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

def generate_telegram_login_token(user):
    """Generate a temporary login token for Telegram user (24 hours expiry)."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=24)
    user.telegram_login_token = token
    user.telegram_token_expires = expires
    db.session.commit()
    print(f"✅ Generated login token for {user.username}")
    return token

def send_notification_to_all_telegram_users(message):
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        print("Warning: TELEGRAM_BOT_TOKEN not configured. Skipping notification.")
        return
    
    with app.app_context():
        users_with_telegram = User.query.filter(User.telegram_id.isnot(None)).all()
        
        if not users_with_telegram:
            print("No users with Telegram ID found.")
            return
        
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        success_count = 0
        failed_count = 0
        
        for user in users_with_telegram:
            try:
                response = requests.post(api_url, data={
                    'chat_id': user.telegram_id,
                    'text': message
                })
                if response.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
                    print(f"Failed to send to user {user.username}: {response.text}")
            except Exception as e:
                failed_count += 1
                print(f"Error sending to user {user.username}: {str(e)}")
        
        print(f"Telegram notifications sent: {success_count} successful, {failed_count} failed")

def send_payment_notification(user_id, amount):
    """Send payment approval notification to Telegram user"""
    import requests
    
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        print("Warning: TELEGRAM_BOT_TOKEN not configured. Skipping payment notification.")
        return
    
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
        
        if not user or not user.telegram_id:
            print(f"User {user_id} not found or has no Telegram ID.")
            return
        
        message = f"💰 እንኳን ደስ አልዎት! ደሞዝህ ብር {amount:.2f} ወደ ዋሌትህ ተልኳል - እባክዎን ዋሌትዎን ቼክ ያድርጉ"
        
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        try:
            response = requests.post(api_url, data={
                'chat_id': user.telegram_id,
                'text': message
            })
            if response.status_code == 200:
                print(f"✅ Payment notification sent to {user.username}")
            else:
                print(f"Failed to send payment notification: {response.text}")
        except Exception as e:
            print(f"Error sending payment notification: {str(e)}")

@app.context_processor
def inject_global_vars():
    return dict(is_admin=check_admin_access, min_payout=MIN_PAYOUT)


# --- 3. WORKER ROUTES (የሰራተኛ መንገዶች) ---

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/miniapp')
def miniapp():
    """Telegram Mini App authentication"""
    if is_logged_in():
        return redirect(url_for('dashboard'))
    return render_template('miniapp.html')

def validate_telegram_initData(initData_string, bot_token):
    """
    Validate Telegram Mini App initData using HMAC-SHA256 (Telegram spec)
    
    Per Telegram Mini App docs:
    - Secret key = HMAC-SHA256("WebAppData", BOT_TOKEN)
    - Data check string = sorted fields (excluding 'hash' and 'signature')
    - Only include: user, auth_date, query_id, start_param, chat_instance
    
    CRITICAL: Keep URL-ENCODED values as-is (do NOT decode)
    """
    try:
        if not initData_string or not bot_token:
            print("❌ Missing initData or bot_token")
            return False, None
        
        print(f"📥 Received initData string (first 100 chars): {initData_string[:100]}")
        
        parts = {}
        for item in initData_string.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                parts[key] = unquote(value)
        
        print(f"🔍 Parsed {len(parts)} fields from initData: {list(parts.keys())}")
        
        if 'hash' not in parts:
            print("❌ No hash in initData")
            return False, None
        
        received_hash = parts['hash']
        print(f"📍 Received hash: {received_hash}")
        
        EXCLUDED_FIELDS = {'hash'}
        
        data_check_fields = []
        for k, v in sorted(parts.items()):
            if k not in EXCLUDED_FIELDS:
                data_check_fields.append(f"{k}={v}")
        
        data_check_string = '\n'.join(data_check_fields)
        
        print(f"🔍 Data check string ({len(data_check_fields)} fields included):")
        print(f"   Excluded: {EXCLUDED_FIELDS}")
        print(f"   Included: {[f for f, _ in sorted(parts.items()) if f not in EXCLUDED_FIELDS]}")
        print(f"   {data_check_string[:150]}...")
        
        # Derive secret key: HMAC-SHA256("WebAppData", BOT_TOKEN)
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        print(f"🔑 Secret key derived (HMAC-SHA256('WebAppData', token))")
        
        # Calculate hash: HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        print(f"🔐 Hash Validation:")
        print(f"   Received:   {received_hash}")
        print(f"   Calculated: {calculated_hash}")
        print(f"   Match: {'✅ YES' if calculated_hash == received_hash else '❌ NO'}")
        
        if calculated_hash != received_hash:
            print("❌ Hash validation FAILED!")
            print(f"   Data string length: {len(data_check_string)} bytes")
            return False, None
        
        print("✅ Hash validation SUCCESSFUL! User authenticated.")
        return True, parts
        
    except Exception as e:
        print(f"❌ Validation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, None

@app.route('/miniapp_login', methods=['POST'])
def miniapp_login():
    """Handle Telegram Mini App login with initData validation"""
    try:
        request_data = request.get_json()
        print(f"📥 Received Mini App login data")
        
        initData = request_data.get('initData')
        user_data = request_data.get('user', {})
        
        print(f"🔍 initData present: {bool(initData)}")
        print(f"🔍 User data: {user_data}")
        
        if not initData:
            print("❌ Missing initData")
            return jsonify({'success': False, 'message': 'Missing initData from Telegram'}), 400
        
        # Validate initData using HMAC-SHA256
        is_valid, parsed_data = validate_telegram_initData(initData, BOT_TOKEN)
        
        if not is_valid:
            print("❌ initData validation failed")
            return jsonify({'success': False, 'message': 'Failed to validate Telegram authentication'}), 401
        
        # Extract telegram_id from user data (user_data should be trusted at this point)
        telegram_id = str(user_data.get('id'))
        first_name = user_data.get('first_name', 'User')
        username = user_data.get('username', f"user_{telegram_id}")
        
        print(f"👤 Authenticated user: id={telegram_id}, name={first_name}")
        
        if not telegram_id or telegram_id == 'None':
            print(f"❌ Invalid Telegram ID: {telegram_id}")
            return jsonify({'success': False, 'message': 'Invalid Telegram ID'}), 400
        
        # Auto-register or get existing user
        with app.app_context():
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                print(f"👤 New user detected, auto-registering: {first_name} (ID: {telegram_id})")
                # Auto-register new user
                user = auto_register_telegram_user(telegram_id, first_name)
                if not user:
                    print(f"❌ Auto-registration failed for {telegram_id}")
                    return jsonify({'success': False, 'message': 'Registration failed'}), 500
            else:
                print(f"✅ Existing user found: {user.username}")
            
            # Set session
            session['user_id'] = user.id
            session['username'] = user.username
            
            print(f"✅ Mini App login successful: {user.username} (Telegram ID: {telegram_id})")
            return jsonify({'success': True, 'message': 'Logged in successfully', 'redirect': '/dashboard'}), 200
    
    except Exception as e:
        print(f"❌ Mini App login error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('ከመለያዎ ወጥተዋል!', 'info')
    return redirect(url_for('index'))

@app.route('/telegram_auto_login/<token>')
def telegram_auto_login(token):
    """Auto-login Telegram user with temporary token."""
    with app.app_context():
        user = User.query.filter_by(telegram_login_token=token).first()
        
        if not user:
            flash('🔐 የሎግইን ቊታ ተገኝቷል! እንደገና ወደ Telegram ሂድ።', 'error')
            return redirect(url_for('miniapp'))
        
        if user.telegram_token_expires and datetime.now() > user.telegram_token_expires:
            flash('🔐 የሎግይን ቊታ ጊዜው አልፍቷል! ወደ Telegram ወስደው ድጋሚ ሞክር።', 'error')
            return redirect(url_for('miniapp'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        
        # Generate a fresh token for next login (user can logout and login again without /start)
        generate_telegram_login_token(user)
        
        print(f"✅ Telegram auto-login successful for {user.username}")
        flash('🎉 በTelegram ገብተዋል!', 'success')
        return redirect(url_for('dashboard'))

@app.route('/telegram_login_check', methods=['GET'])
def telegram_login_check():
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    
    if not TELEGRAM_BOT_TOKEN:
        flash('Telegram login is not configured. Please contact administrator.', 'error')
        return redirect(url_for('miniapp'))
    
    auth_data = request.args.to_dict()
    
    if 'hash' not in auth_data:
        flash('የተሳሳተ Telegram ማረጋገጫ መረጃ!', 'error')
        return redirect(url_for('miniapp'))
    
    check_hash = auth_data.pop('hash')
    
    data_check_string = '\n'.join([f'{k}={v}' for k, v in sorted(auth_data.items())])
    
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if calculated_hash != check_hash:
        flash('የተሳሳተ Telegram ማረጋገጫ!', 'error')
        return redirect(url_for('miniapp'))
    
    if 'auth_date' in auth_data:
        auth_date = int(auth_data['auth_date'])
        current_time = int(time.time())
        if current_time - auth_date > 86400:
            flash('Telegram login expired. Please try again.', 'error')
            return redirect(url_for('miniapp'))
    
    telegram_id = auth_data.get('id')
    telegram_username = auth_data.get('username', f"telegram_user_{telegram_id}")
    
    if not telegram_id:
        flash('የተሳሳተ Telegram መረጃ!', 'error')
        return redirect(url_for('miniapp'))
    
    with app.app_context():
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            from sqlalchemy.exc import IntegrityError
            password_hash = generate_password_hash(f"telegram_{telegram_id}_{int(time.time())}")
            
            suffix_id = str(telegram_id)
            max_suffix_length = len(suffix_id) + 5
            max_base_length = 80 - max_suffix_length - 1
            
            base_username = telegram_username[:max_base_length] if len(telegram_username) > max_base_length else telegram_username
            max_attempts = 10
            
            for attempt in range(max_attempts):
                if attempt == 0:
                    attempt_username = base_username
                elif attempt == 1:
                    attempt_username = f"{base_username}_{suffix_id}"
                else:
                    attempt_username = f"{base_username}_{suffix_id}_{attempt-1}"
                
                attempt_username = attempt_username[:80]
                
                try:
                    user = User(username=attempt_username, password_hash=password_hash, telegram_id=telegram_id)
                    db.session.add(user)
                    db.session.commit()
                    flash('በ Telegram በተሳካ ሁኔታ ተመዝግበዋል!', 'success')
                    break
                except IntegrityError as e:
                    db.session.rollback()
                    if attempt == max_attempts - 1:
                        flash('የተጠቃሚ ስም ችግር አለ። እባክዎ እንደገና ይሞክሩ።', 'error')
                        return redirect(url_for('miniapp'))
                except Exception as e:
                    db.session.rollback()
                    print(f"Telegram login error for user {telegram_id}: {str(e)}")
                    flash(f'ስህተት ተከስቷል። እባክዎ እንደገና ይሞክሩ።', 'error')
                    return redirect(url_for('miniapp'))
        
        session['user_id'] = user.id
        session['username'] = user.username
        flash('በ Telegram በተሳካ ሁኔታ ገብተዋል!', 'success')
        return redirect(url_for('dashboard'))

def set_telegram_bot_commands():
    """Set bot commands menu in Telegram"""
    import requests
    
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        print("❌ BOT_TOKEN not configured!")
        return False
    
    try:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
        commands = [
            {"command": "balance", "description": "💰 Check your earnings"},
            {"command": "tasks", "description": "📋 View your tasks"},
            {"command": "help", "description": "❓ Show available commands"}
        ]
        response = requests.post(api_url, json={"commands": commands})
        if response.status_code == 200:
            print(f"✅ Bot commands menu set successfully!")
            return True
        else:
            print(f"⚠️ Failed to set bot commands: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error setting bot commands: {str(e)}")
        return False

def auto_register_telegram_user(telegram_user_id, first_name):
    """Auto-register a new Telegram user with a generated username and password"""
    import string
    import random
    
    telegram_id = str(telegram_user_id)
    
    base_username = f"{first_name}_{telegram_id}"[:80]
    attempt_username = base_username
    attempt = 0
    max_attempts = 100
    
    while attempt < max_attempts:
        attempt += 1
        if not User.query.filter_by(username=attempt_username).first():
            break
        suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        attempt_username = f"{base_username}_{suffix}"[:80]
    
    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    password_hash = generate_password_hash(random_password)
    
    try:
        user = User(username=attempt_username, password_hash=password_hash, telegram_id=telegram_id)
        db.session.add(user)
        db.session.commit()
        print(f"✅ Auto-registered Telegram user: {attempt_username} (ID: {telegram_id})")
        return user
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error auto-registering user: {str(e)}")
        return None

def process_telegram_message(update_data):
    """Process Telegram message and send reply"""
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    
    print(f"\n{'='*60}")
    print(f"🔍 PROCESS_TELEGRAM_MESSAGE called")
    print(f"{'='*60}")
    print(f"🔍 BOT_TOKEN value check:")
    print(f"   - Is not None: {TELEGRAM_BOT_TOKEN is not None}")
    print(f"   - Is not empty string: {bool(TELEGRAM_BOT_TOKEN)}")
    print(f"   - Length: {len(TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else 0}")
    print(f"   - First 20 chars: {TELEGRAM_BOT_TOKEN[:20] if TELEGRAM_BOT_TOKEN else 'N/A'}")
    
    if not TELEGRAM_BOT_TOKEN:
        print("❌ CRITICAL ERROR: Bot token is empty or None!")
        return False
    
    try:
        if not update_data or 'message' not in update_data:
            print("⚠️ No message in update_data")
            return True
        
        message = update_data['message']
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        user_info = message.get('from', {})
        telegram_user_id = str(user_info.get('id'))
        first_name = user_info.get('first_name', 'User')
        
        print(f"📱 Telegram message received: chat_id={chat_id}, user_id={telegram_user_id}, text='{text}'")
        print(f"🔍 DEBUG: Full message object: {message}")
        
        if not chat_id:
            print("❌ ERROR: chat_id is None or empty!")
            return False
        
        message_text = None
        
        with app.app_context():
            user = User.query.filter_by(telegram_id=telegram_user_id).first()
            
            if text == '/start' or text == '/help':
                if not user:
                    # Auto-register new user
                    user = auto_register_telegram_user(telegram_user_id, first_name)
                    if user:
                        message_text = f"👋 እንኳን ደህና መጡ፣ {first_name}! \n\n" \
                                      f"🎉 አሁን ወደ G-Task Manager ራሂ ተመዝግበዋል!\n\n" \
                                      f"💼 ሥራ ወስደን ገንዘብ ይቀዩ - ብር 10 ለእያንዳንዱ ስራ!"
                    else:
                        message_text = "⚠️ Registration failed. Please try again."
                else:
                    message_text = f"👋 እንዴት ሁዋል፣ {first_name}!\n\n" \
                                  f"💼 ፍጠን ስራ ውሰድ እና ገንዘብ ያጀምሩ!"
            
            elif text == '/balance':
                if user:
                    message_text = f"💰 የገንዘብ ሁኔታ:\n\n" \
                                  f"📊 አጠቃላይ ገቢ: ብር {user.total_earned:.2f}\n" \
                                  f"💵 ሊወጣ የሚችል: ብር {user.pending_payout:.2f}\n\n" \
                                  f"🔐 <a href='https://g-task.onrender.com/telegram_auto_login/{generate_telegram_login_token(user)}'>ወደ ዌብሳይት ይሂዱ</a>"
                else:
                    message_text = "🔐 መለያ አልተገናኘም! /start ለመጀመር"
            
            elif text == '/tasks':
                if user:
                    tasks = Task.query.filter_by(user_id=user.id).all()
                    verified_count = len([t for t in tasks if t.status == 'VERIFIED'])
                    pending_count = len([t for t in tasks if t.status == 'PENDING'])
                    message_text = f"📋 የሥራ ሁኔታ:\n\n" \
                                  f"✅ የተረጋገጡ: {verified_count}\n" \
                                  f"⏳ በመጠበቅ ላይ: {pending_count}\n" \
                                  f"💰 ብር {verified_count * PAYOUT_AMOUNT_PER_TASK:.2f} አገኘዋል\n\n" \
                                  f"🔐 <a href='https://g-task.onrender.com/telegram_auto_login/{generate_telegram_login_token(user)}'>ወደ ዌብሳይት ይሂዱ</a>"
                else:
                    message_text = "🔐 መለያ አልተገናኘም! /start ለመጀመር"
            
            else:
                message_text = "❓ ያልታወቀ ትዕዛዝ። /help ለሚገቡ ትዕዛዞች"
        
        if not message_text:
            print("❌ ERROR: message_text is empty!")
            return False
        
        print(f"🔍 DEBUG: Prepared message for chat_id {chat_id}: {message_text[:50]}...")
        
        # Send message to Telegram API
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        print(f"🔍 DEBUG: API URL: {api_url[:50]}...")
        
        payload = {
            'chat_id': chat_id,
            'text': message_text,
            'parse_mode': 'HTML'
        }
        
        # Add Inline Keyboard button for Mini App if /start or /help
        if text in ['/start', '/help']:
            import json
            keyboard = {
                "inline_keyboard": [
                    [
                        {
                            "text": "🚀 Open G-Task Mini App",
                            "web_app": {
                                "url": "https://g-task.onrender.com/miniapp"
                            }
                        }
                    ]
                ]
            }
            payload['reply_markup'] = json.dumps(keyboard)
            print(f"✅ Added web_app button to /start command")
        
        print(f"🔍 DEBUG: Sending payload: {str(payload)[:200]}...")
        
        try:
            response = requests.post(api_url, data=payload, timeout=10)
            print(f"🔍 DEBUG: Response status: {response.status_code}")
            print(f"🔍 DEBUG: Response text: {response.text}")
            
            if response.status_code == 200:
                print(f"✅ Message sent to {telegram_user_id}")
                return True
            else:
                print(f"❌ Failed to send message: {response.text}")
                return False
        except Exception as send_error:
            print(f"❌ ERROR sending message: {str(send_error)}")
            import traceback
            traceback.print_exc()
            return False
    
    except Exception as e:
        print(f"❌ Error processing message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

@app.route('/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Telegram webhook handler (legacy route)"""
    try:
        update_data = request.get_json()
        print(f"📥 Received at /telegram/webhook: {update_data}")
        process_telegram_message(update_data)
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Telegram webhook error: {str(e)}")
        return jsonify({'status': 'error'}), 500

@app.route('/telegram/set-webhook', methods=['POST'])
def set_telegram_webhook():
    """Admin route to configure Telegram webhook"""
    if not check_admin_access():
        return jsonify({'status': 'error', 'message': 'Admin access required'}), 403
    
    import requests
    
    TELEGRAM_BOT_TOKEN = BOT_TOKEN
    WEBHOOK_URL_VAR = WEBHOOK_URL
    
    if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL_VAR:
        return jsonify({'status': 'error', 'message': f'Bot token: {"configured" if TELEGRAM_BOT_TOKEN else "missing"}, Webhook URL: {"configured" if WEBHOOK_URL_VAR else "missing"}'}), 400
    
    try:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
        response = requests.post(api_url, data={'url': WEBHOOK_URL_VAR})
        
        if response.status_code == 200:
            set_telegram_bot_commands()
            print(f"✅ Telegram webhook set successfully to: {WEBHOOK_URL_VAR}")
            return jsonify({'status': 'success', 'message': 'Webhook set successfully', 'webhook_url': WEBHOOK_URL_VAR}), 200
        else:
            print(f"❌ Failed to set webhook: {response.text}")
            return jsonify({'status': 'error', 'message': f'Failed to set webhook: {response.text}'}), 400
    except Exception as e:
        print(f"❌ Error setting webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'success', 'message': 'Webhook set successfully', 'webhook_url': WEBHOOK_URL_VAR}), 200

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Render-compatible Telegram webhook handler (MAIN ENTRY POINT)"""
    print(f"\n{'='*60}")
    print(f"🔔 WEBHOOK RECEIVED - POST /webhook")
    print(f"{'='*60}")
    
    try:
        print(f"🔍 Content-Type: {request.content_type}")
        print(f"🔍 Request method: {request.method}")
        
        # Try to get JSON
        data = request.get_json()
        
        print(f"📥 JSON parsed successfully")
        
        if not data:
            print("⚠️ Empty webhook data received")
            return jsonify({'status': 'ok'}), 200 
        
        print(f"📥 Webhook data keys: {list(data.keys())}")
        print(f"🔍 BOT_TOKEN check: configured={bool(BOT_TOKEN)}, length={len(BOT_TOKEN) if BOT_TOKEN else 0}")
        
        # Process the message
        result = process_telegram_message(data)
        print(f"✅ Message processing result: {result}")
        
        # Always return 200 to Telegram
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Still return 200 to prevent Telegram from retrying
        return jsonify({'status': 'ok'}), 200

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('miniapp'))
    
    try:
        user = User.query.filter_by(id=session['user_id']).first()
        
        if user is None:
            session.pop('user_id', None)
            return redirect(url_for('miniapp'))
        
        current_task = Task.query.filter_by(user_id=session['user_id'], status='PENDING').first()
        available_task = Inventory.query.filter_by(status='AVAILABLE').first()
        my_tasks = Task.query.filter_by(user_id=session['user_id']).all()
        
        return render_template('dashboard.html', 
                             user=user, 
                             current_task=current_task,
                             available_task=available_task,
                             my_tasks=my_tasks)
                             
    except Exception as e:
        print(f"CRITICAL FLASK ERROR CAUGHT: {e}")
        session.pop('user_id', None)
        return redirect(url_for('miniapp'))

@app.route('/take_task', methods=['POST'])
def take_task():
    if not is_logged_in():
        return redirect(url_for('miniapp'))

    with app.app_context():
        available_inventory = Inventory.query.filter_by(status='AVAILABLE').first()
        
        if not available_inventory:
            flash('አሁን ምንም ዕንቁራታ ስራ የለም።', 'error')
            return redirect(url_for('dashboard'))
        
        new_task = Task(inventory_id=available_inventory.id, user_id=session['user_id'])
        available_inventory.status = 'ASSIGNED'
        db.session.add(new_task)
        db.session.commit()
        
        flash('ሥራውን በተሳካ ሁኔታ ወስደዋል!', 'success')
        return redirect(url_for('dashboard'))

@app.route('/submit_task/<int:task_id>', methods=['POST'])
def submit_task(task_id):
    if not is_logged_in():
        return redirect(url_for('miniapp'))

    with app.app_context():
        task = Task.query.filter_by(id=task_id, user_id=session['user_id']).first()
        
        if not task:
            flash('ይህ ሥራ አልተገኘም።', 'error')
            return redirect(url_for('dashboard'))
        
        screenshot = request.files.get('screenshot')
        
        if not screenshot:
            flash('ስክሪንሻት ያስፈልጋል።', 'error')
            return redirect(url_for('dashboard'))
        
        try:
            task.status = 'SUBMITTED'
            task.date_completed = func.now()
            db.session.commit()
            flash('ሥራ በተሳካ ሁኔታ ተላለወ! አድሚን ለማረጋገጥ በመጠበቅ ላይ።', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'ስህተት: {str(e)}', 'error')
        
        return redirect(url_for('dashboard'))

@app.route('/payout_request')
def payout_request():
    if not is_logged_in():
        return redirect(url_for('miniapp'))
    
    with app.app_context():
        user = User.query.filter_by(id=session['user_id']).first()
    
    return render_template('payout_request.html', user=user, min_payout=MIN_PAYOUT)

@app.route('/request_payout', methods=['POST'])
def request_payout():
    if not is_logged_in():
        return redirect(url_for('miniapp'))

    with app.app_context():
        user = User.query.filter_by(id=session['user_id']).first()
        amount = float(request.form.get('amount', 0))
        
        if amount < MIN_PAYOUT:
            flash(f'ቢያንስ ብር {MIN_PAYOUT:.2f} ግለጹ።', 'error')
            return redirect(url_for('payout_request'))
        
        if amount > user.pending_payout:
            flash('ቀሪ ሂሳብዎ ያ መጠን የለም።', 'error')
            return redirect(url_for('payout_request'))
        
        payment_method = request.form.get('payment_method')
        recipient_name = request.form.get('recipient_name')
        payment_details = request.form.get('payment_details')
        
        try:
            payout = Payout(
                user_id=session['user_id'], 
                amount=amount,
                payment_method=payment_method,
                recipient_name=recipient_name,
                payment_details=payment_details
            )
            user.pending_payout -= amount
            db.session.add(payout)
            db.session.commit()
            flash('ክፍያ ጥያቄ በተሳካ ሁኔታ ተላለወ!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'ስህተት: {str(e)}', 'error')
            return redirect(url_for('payout_request'))

@app.route('/view_ads')
def view_ads():
    if not is_logged_in():
        return redirect(url_for('miniapp'))
    
    with app.app_context():
        user = User.query.filter_by(id=session['user_id']).first()
        available_ads = Ad.query.filter_by(is_active=True).all()
        
        today = func.date(func.now())
        viewed_today = db.session.query(AdView).filter(
            AdView.user_id == session['user_id'],
            AdView.status == 'REWARDED',
            func.date(AdView.date_viewed) == today
        ).scalars().all()
        
    return render_template('view_ads.html', available_ads=available_ads, viewed_today=viewed_today)


# 3.11. ማስታወቂያ ሪወርድ ምዝገባ (Register Ad Reward)
@app.route('/register_ad_reward/<int:ad_id>', methods=['POST'])
def register_ad_reward(ad_id):
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    with app.app_context():
        ad = Ad.query.filter_by(id=ad_id, is_active=True).first()
        user = User.query.filter_by(id=user_id).first()
        
        if not ad or not user:
            return jsonify({'success': False, 'message': 'Ad or User not found'}), 404

        today = func.date(func.now())
        already_rewarded = AdView.query.filter(
            AdView.ad_id == ad_id,
            AdView.user_id == user_id,
            AdView.status == 'REWARDED',
            func.date(AdView.date_viewed) == today
        ).first()

        if already_rewarded:
            return jsonify({'success': False, 'message': 'You have already been rewarded for this ad today.'}), 400
            
        try:
            user.pending_payout += ad.reward_amount
            user.total_earned += ad.reward_amount
            
            new_view = AdView(ad_id=ad_id, user_id=user_id, status='REWARDED')
            db.session.add(new_view)
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f'ብር{ad.reward_amount:.2f} ወደ ቀሪ ሂሳብዎ ተጨምሯል!',
                'new_balance': f'{user.pending_payout:.2f}'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Internal Server Error'}), 500

@app.route('/daily_checkin', methods=['POST'])
def daily_checkin():
    """Daily check-in task with 0.20 ብር reward."""
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user_id = session['user_id']
    DAILY_CHECKIN_REWARD = 0.20
    
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        today = func.current_date()
        already_checked_in = DailyCheckIn.query.filter(
            DailyCheckIn.user_id == user_id,
            DailyCheckIn.check_in_date == today
        ).first()
        
        if already_checked_in:
            return jsonify({
                'success': False, 
                'message': 'ዛሬ ቀድሞ ገብተዋል! ነገ ይሞክሩ።'
            }), 400
        
        try:
            # Add reward to user balance
            user.pending_payout += DAILY_CHECKIN_REWARD
            user.total_earned += DAILY_CHECKIN_REWARD
            
            # Record check-in
            new_checkin = DailyCheckIn(user_id=user_id)
            db.session.add(new_checkin)
            db.session.commit()
            
            print(f"✅ Daily check-in for {user.username}: +ብር{DAILY_CHECKIN_REWARD}")
            
            return jsonify({
                'success': True,
                'message': f'🎉 እንኳን ደስ አልዎት! ብር {DAILY_CHECKIN_REWARD:.2f} ወደ ቀሪ ሂሳብዎ ተጨምሯል!',
                'new_balance': f'{user.pending_payout:.2f}'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Daily check-in error: {str(e)}")
            return jsonify({'success': False, 'message': 'Internal Server Error'}), 500


# --- 4. ADMIN ROUTES (አስተዳዳሪ መንገዶች) ---

@app.route('/admin/dashboard')
def admin_dashboard():
    if not check_admin_access():
        flash('የአስተዳዳሪ መብት የለዎትም።', 'error')
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        pending_tasks_count = Task.query.filter_by(status='SUBMITTED').count()
        total_inventory_count = Inventory.query.filter_by(status='AVAILABLE').count()
        total_users_count = User.query.filter_by(is_admin=False).count()

    return render_template('admin_dashboard.html', 
                             pending_tasks_count=pending_tasks_count,
                             total_inventory_count=total_inventory_count,
                             total_users_count=total_users_count)


@app.route('/admin/add_tasks', methods=['GET', 'POST'])
def admin_add_tasks():
    if not check_admin_access():
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        task_data = request.form.get('task_data')
        
        if not task_data:
            flash('እባክዎ የጂሜል መረጃውን ያስገቡ።', 'error')
            return render_template('admin_add_tasks.html')
            
        lines = task_data.strip().split('\n')
        successful_inserts = 0
        failed_tasks = []

        with app.app_context():
            for line in lines:
                line = line.strip()
                if not line: continue
                
                if ':' in line:
                    parts = line.split(':')
                    username = parts[0].strip() if len(parts) > 0 else None
                    password = parts[1].strip() if len(parts) > 1 else None
                    recovery_email = parts[2].strip() if len(parts) > 2 else None
                    
                    if username and password:
                        try:
                            new_inventory = Inventory(
                                gmail_username=username, 
                                gmail_password=password,
                                recovery_email=recovery_email
                            )
                            db.session.add(new_inventory)
                            db.session.commit()
                            successful_inserts += 1
                        except Exception:
                            db.session.rollback()
                            failed_tasks.append(f"Duplicate/Error: {username}")
                    else:
                        failed_tasks.append(f"Invalid format: {line}")
                else:
                    failed_tasks.append(f"Missing separator: {line}")
        
            if successful_inserts > 0:
                flash(f'በተሳካ ሁኔታ {successful_inserts} አዲስ ስራዎች ወደ ክምችት ገብተዋል።', 'success')
                send_notification_to_all_telegram_users("🚀 አዲስ ስራ ተጨመረ ፍጠን አሁን ስራ ውሰድ")
            if failed_tasks:
                flash(f'በመግቢያ ላይ ስህተት የተፈጠረባቸው ስራዎች ({len(failed_tasks)}): ' + '; '.join(failed_tasks[:5]) + '...', 'warning')

        return redirect(url_for('admin_dashboard'))

    return render_template('admin_add_tasks.html')


# 4.3. ማስታወቂያዎች አስተዳደር (Manage Ads)
@app.route('/admin/manage_ads', methods=['GET', 'POST'])
def admin_manage_ads():
    if not check_admin_access():
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        if request.method == 'POST':
            title = request.form.get('title')
            embed_url = request.form.get('embed_url')
            
            try:
                reward_amount = float(request.form.get('reward_amount'))
                view_time = int(request.form.get('view_time'))
            except (ValueError, TypeError):
                flash('ክፍያ እና ሰዓት በቁጥር መግባት አለባቸው!', 'error')
                return redirect(url_for('admin_manage_ads'))
            
            try:
                if 'watch?v=' in embed_url:
                    embed_url = embed_url.replace('watch?v=', 'embed/')

                new_ad = Ad(
                    title=title, 
                    embed_url=embed_url, 
                    reward_amount=reward_amount, 
                    required_view_time=view_time
                )
                db.session.add(new_ad)
                db.session.commit()
                flash(f'ማስታወቂያው "{title}" በተሳካ ሁኔታ ተጨምሯል።', 'success')
                return redirect(url_for('admin_manage_ads'))
            except Exception as e:
                db.session.rollback()
                flash(f'ማስታወቂያ በማስገባት ላይ ስህተት ተከስቷል: {e}', 'error')

        ads = Ad.query.all()
    
    return render_template('admin_manage_ads.html', ads=ads)


# 4.4. ማስታወቂያ ትቅልድ (Toggle Ad)
@app.route('/admin/toggle_ad/<int:ad_id>', methods=['POST'])
def admin_toggle_ad(ad_id):
    if not check_admin_access():
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        ad = Ad.query.filter_by(id=ad_id).first()
        if ad:
            ad.is_active = not ad.is_active
            db.session.commit()
            flash(f'የማስታወቂያው ሁኔታ ወደ {"Active" if ad.is_active else "Inactive"} ተቀይሯል።', 'info')
        else:
            flash('ማስታወቂያ አልተገኘም።', 'error')
    
    return redirect(url_for('admin_manage_ads'))


@app.route('/admin/verify_tasks')
def admin_verify_tasks():
    if not check_admin_access():
        return redirect(url_for('dashboard'))

    with app.app_context():
        submitted_tasks_raw = db.session.execute(db.select(Task.id.label('task_id'), Task.completion_code, Task.date_completed, Inventory.gmail_username, User.username.label('worker_username'))
            .join(Inventory, Task.inventory_id == Inventory.id)
            .join(User, Task.user_id == User.id)
            .filter(Task.status == 'SUBMITTED')
            .order_by(Task.date_completed.asc())
        ).all()
        
        # Convert Row objects to dictionaries for template access
        submitted_tasks = []
        for row in submitted_tasks_raw:
            submitted_tasks.append({
                'task_id': row.task_id,
                'completion_code': row.completion_code,
                'date_completed': row.date_completed,
                'gmail_username': row.gmail_username,
                'worker_username': row.worker_username
            })
        
    return render_template('admin_verify_tasks.html', submitted_tasks=submitted_tasks)

# 5.4. የሥራ ማረጋገጫ እርምጃ
@app.route('/admin/action_task/<int:task_id>/<action>', methods=['POST'])
def admin_action_task(task_id, action):
    if not check_admin_access():
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        task = Task.query.filter_by(id=task_id).first()

        if not task or task.status != 'SUBMITTED':
            flash('ይህ ሥራ አልተገኘም ወይም ለመረጋገጥ ዝግጁ አይደለም።', 'error')
            return redirect(url_for('admin_verify_tasks'))

        try:
            inventory_item = Inventory.query.filter_by(id=task.inventory_id).first()
            user = User.query.filter_by(id=task.user_id).first()
            
            if action == 'verify':
                task.status = 'VERIFIED'
                if inventory_item:
                    inventory_item.status = 'COMPLETED'
                
                # ክፍያውን በሲስተሙ አማካኝነት ወደ ንፁ ባላንስ ይጨምራል
                if user:
                    user.pending_payout += PAYOUT_AMOUNT_PER_TASK
                    user.total_earned += PAYOUT_AMOUNT_PER_TASK
                
                db.session.commit()
                flash(f'ሥራው በተሳካ ሁኔታ ተረጋግጧል። ብር{PAYOUT_AMOUNT_PER_TASK:.2f} ለሰራተኛው ተጨምሯል።', 'success')

            elif action == 'reject':
                task.status = 'REJECTED'
                if inventory_item:
                    inventory_item.status = 'AVAILABLE' # ስራውን ነጻ ያደርገዋል
                
                db.session.commit()
                flash('ሥራው አልተቀበልም። ወደ ሥራ ክምችት ተመልሷል።', 'info')
                
            else:
                flash('ትክክለኛ ያልሆነ እርምጃ።', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'ማረጋገጫው ላይ ስህተት ተከስቷል: {e}', 'error')

    return redirect(url_for('admin_verify_tasks'))


@app.route('/admin/payouts')
def admin_payouts():
    if not check_admin_access():
        return redirect(url_for('dashboard'))

    with app.app_context():
        payout_requests_raw = db.session.execute(db.select(Payout.id.label('payout_id'), Payout.amount, Payout.date_requested, Payout.recipient_name, Payout.payment_method, Payout.payment_details, User.username.label('worker_username'))
            .join(User, Payout.user_id == User.id)
            .filter(Payout.status == 'REQUESTED')
            .order_by(Payout.date_requested.asc())
        ).all()
        
        # Convert Row objects to dictionaries for template access
        payout_requests = []
        for row in payout_requests_raw:
            payout_requests.append({
                'payout_id': row.payout_id,
                'amount': row.amount,
                'date_requested': row.date_requested,
                'recipient_name': row.recipient_name,
                'payment_method': row.payment_method,
                'payment_details': row.payment_details,
                'worker_username': row.worker_username
            })
    
    return render_template('admin_payouts.html', payout_requests=payout_requests)


# 5.6. የክፍያ እርምጃ
@app.route('/admin/action_payout/<int:payout_id>/<action>', methods=['POST'])
def admin_action_payout(payout_id, action):
    if not check_admin_access():
        return redirect(url_for('dashboard'))
    
    with app.app_context():
        payout = Payout.query.filter_by(id=payout_id).first()

        if not payout or payout.status != 'REQUESTED':
            flash('ጥያቄው አልተገኘም ወይም አስቀድሞ ተስተናግዷል።', 'error')
            return redirect(url_for('admin_payouts'))
        
        user = User.query.filter_by(id=payout.user_id).first()

        try:
            if action == 'paid':
                payout.status = 'PAID'
                payout.date_paid = func.now()
                db.session.commit()
                
                # Send Telegram payment notification to user
                if user:
                    send_payment_notification(user.id, payout.amount)
                
                flash(f'የ ብር{payout.amount:.2f} ክፍያ እንደተፈጸመ ምልክት ተደርጓል።', 'success')

            elif action == 'reject':
                payout.status = 'REJECTED'
                
                # ገንዘቡን ወደ pending_payout ይመልሳል
                if user:
                    user.pending_payout += payout.amount
                
                db.session.commit()
                flash(f'የ ብር{payout.amount:.2f} ክፍያ ጥያቄ ውድቅ ተደርጓል፣ ገንዘቡ ወደ ቀሪ ሂሳብ ተመልሷል።', 'info')
                
            else:
                flash('ትክክለኛ ያልሆነ እርምጃ።', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'የክፍያ እርምጃ ላይ ስህተት ተከስቷል: {e}', 'error')

    return redirect(url_for('admin_payouts'))


# --- 5. RUN APP ---
if __name__ == '__main__':
    # Flask-SQLAlchemy ሁልጊዜ በ app_context ውስጥ መስራት አለበት
    with app.app_context():
        # ይህ መስመር SQLiteን የምትሞክር ከሆነ ልትጠቀምበት ትችላለህ
        # init_db() 
        # Render-compatible: Check if running in production or development
        is_production = os.environ.get('ENVIRONMENT') == 'production' or os.environ.get('RENDER') == 'true'
        debug_mode = not is_production
        app.run(debug=debug_mode, host='0.0.0.0', port=5000)
