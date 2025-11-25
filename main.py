# ======================================================
# G-TASK MANAGER: GMAIL ACCOUNT CREATION TASK MANAGER
# Version: 2.0 (FINAL BACKEND: PostgreSQL/SQLAlchemy)
# Author: Gemini (AI)
# ======================================================

import os
import time
import hashlib
import hmac
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
app.secret_key = 'Kq7bYxZ_3u9sP2hG_vR4wF1mJ_tL5cY_8oE'

# Database Configuration (Neon/PostgreSQL or SQLite fallback)
# የ DATABASE_URL ሚስጥር ከ Replit Secrets ይነበባል
database_url = os.environ.get('DATABASE_URL', 'sqlite:///g_task_manager.db')
# Remove extra quotes and fix HTML encoding if present
database_url = database_url.strip("'\"").replace('&amp;', '&')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

MIN_PAYOUT = 9.00
PAYOUT_AMOUNT_PER_TASK = 9.00

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
        username = request.form['username']
        password = request.form['password']
        with app.app_context():
            user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('በተሳካ ሁኔታ ገብተዋል!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('ትክክለኛ ያልሆነ የተጠቃሚ ስም ወይም የይለፍ ቃል!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('ከመለያዎ ወጥተዋል!', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
        
        current_task_obj = Task.query.filter(Task.user_id == user_id, Task.status.in_(['PENDING', 'SUBMITTED'])).first()
        
        # Prepare current_task with inventory data
        current_task = None
        if current_task_obj:
            inventory = Inventory.query.filter_by(id=current_task_obj.inventory_id).first()
            current_task = {
                'id': current_task_obj.id,
                'gmail_username': inventory.gmail_username if inventory else '',
                'gmail_password': inventory.gmail_password if inventory else ''
            }

        available_task = Inventory.query.filter_by(status='AVAILABLE').first()

        my_tasks_obj = Task.query.filter(Task.user_id == user_id).order_by(Task.date_assigned.desc()).all()
        my_tasks = []
        for task in my_tasks_obj:
            inventory = Inventory.query.filter_by(id=task.inventory_id).first()
            my_tasks.append({
                'id': task.id,
                'gmail_username': inventory.gmail_username if inventory else '',
                'status': task.status,
                'date_assigned': task.date_assigned
            })
    
    return render_template('dashboard.html', 
                             user=user, 
                             my_tasks=my_tasks,
                             available_task=available_task,
                             current_task=current_task)

@app.route('/take_task', methods=['POST'])
def take_task():
    if not is_logged_in(): return redirect(url_for('login'))
    user_id = session['user_id']
    
    with app.app_context():
        try:
            has_active_task = Task.query.filter(Task.user_id == user_id, Task.status.in_(['PENDING', 'SUBMITTED'])).first()
            if has_active_task:
                flash('ሌላ ስራ ከመውሰድዎ በፊት አሁን የያዙትን ስራ ማጠናቀቅ አለብዎት!', 'error')
                return redirect(url_for('dashboard'))

            available_task = Inventory.query.filter_by(status='AVAILABLE').first()
            
            if available_task:
                available_task.status = 'ASSIGNED'
                new_task = Task(inventory_id=available_task.id, user_id=user_id, status='PENDING')
                db.session.add(new_task)
                db.session.commit()
                flash(f'አዲስ ሥራ ተሰጥቷችኋል! የጂሜል ስም: {available_task.gmail_username}', 'success')
            else:
                flash('ይቅርታ! ሥራው ቀድሞ ተወስዷል ወይም አዲስ ሥራ የለም።', 'info')
                
        except Exception as e:
            db.session.rollback()
            flash(f'ሥራውን በመውሰድ ላይ ስህተት ተከስቷል: {e}', 'error')
            
    return redirect(url_for('dashboard'))

@app.route('/submit_task/<int:task_id>', methods=['POST'])
def submit_task(task_id):
    if not is_logged_in(): return redirect(url_for('login'))
    user_id = session['user_id']
    
    # Check if screenshot file is uploaded
    if 'screenshot' not in request.files:
        flash('ስክሪንሻት ምስል ማስገባት አለብዎት።', 'error')
        return redirect(url_for('dashboard'))
    
    screenshot_file = request.files['screenshot']
    if screenshot_file.filename == '':
        flash('ስክሪንሻት ምስል ምረጥ።', 'error')
        return redirect(url_for('dashboard'))

    with app.app_context():
        task = Task.query.filter_by(id=task_id).first()
        
        if not task or task.user_id != user_id:
            flash('ይህ ሥራ የእርስዎ አይደለም ወይም አልተገኘም።', 'error')
            return redirect(url_for('dashboard'))

        if task.status in ('SUBMITTED', 'VERIFIED'):
            flash('ይህ ሥራ አስቀድሞ ገብቷል ወይም ተረጋግጧል።', 'info')
            return redirect(url_for('dashboard'))

        try:
            # Save screenshot file to a secure location
            os.makedirs('static/screenshots', exist_ok=True)
            filename = f"task_{task_id}_{user_id}_{int(time.time())}.png"
            screenshot_path = os.path.join('static/screenshots', filename)
            screenshot_file.save(screenshot_path)
            
            # Store the filename as the completion code
            task.completion_code = filename
            task.status = 'SUBMITTED'
            task.date_completed = func.now()
            db.session.commit()
            flash('ሥራዎ በተሳካ ሁኔታ ገብቷል። የአስተዳዳሪ ማረጋገጫን ይጠብቁ!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'ሥራውን በማስረከብ ላይ ስህተት ተከስቷል: {e}', 'error')
            
    return redirect(url_for('dashboard'))

# 4.7. ክፍያ መጠየቅ (Payout Request)
@app.route('/payout_request', methods=['GET', 'POST'])
def payout_request():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    with app.app_context():
        user = User.query.filter_by(id=user_id).first()
    
        if request.method == 'POST':
            try:
                amount = float(request.form['amount'])
                recipient_name = request.form.get('recipient_name', '')
                payment_method = request.form.get('payment_method', '')
                payment_details = request.form.get('payment_details', '')
                
                if amount < MIN_PAYOUT:
                    flash(f'ዝቅተኛው የክፍያ መጠን ብር{MIN_PAYOUT:.2f} ነው።', 'error')
                elif amount > user.pending_payout:
                    flash('ሊወጣ ከሚችለው ቀሪ ሂሳብ በላይ ጠይቀዋል።', 'error')
                elif not recipient_name or len(recipient_name.strip()) == 0:
                    flash('የአካውንት ባለቤት ስም ያስገቡ።', 'error')
                elif not payment_method or len(payment_method.strip()) == 0:
                    flash('ክፍያ ዘዴ ምረጥ።', 'error')
                elif not payment_details or len(payment_details.strip()) == 0:
                    flash('ክፍያ መረጃ ያስገቡ (ስልክ ቁጥር ወይም የባንክ ሂሳብ)።', 'error')
                else:
                    try:
                        # 1. የክፍያ ጥያቄ ወደ payouts ሠንጠረዥ ያስገባል
                        new_payout = Payout(
                            user_id=user_id, 
                            amount=amount, 
                            recipient_name=recipient_name.strip(),
                            payment_method=payment_method.strip(),
                            payment_details=payment_details.strip()
                        )
                        db.session.add(new_payout)
                        db.session.flush()
                        
                        # 2. ከሰራተኛው ቀሪ ሂሳብ ላይ ይቀንሳል
                        user.pending_payout -= amount
                        db.session.commit()
                        
                        flash(f'የ ብር{amount:.2f} ክፍያ ጥያቄ ገብቷል ({payment_method})። አስተዳዳሪ እስኪያረጋግጥ ይጠብቁ።', 'success')
                        return redirect(url_for('dashboard'))
                    except Exception as db_err:
                        db.session.rollback()
                        error_msg = str(db_err)
                        print(f"Database error: {error_msg}")
                        flash(f'ክፍያ ጥያቄ ሲወጣ ስህተት ተከስቷል። እባክዎ ደግሞ ይሞክሩ።', 'error')

            except ValueError:
                flash('ትክክለኛ መጠን ያስገቡ።', 'error')
            except Exception as e:
                db.session.rollback()
                print(f"Error: {e}")
                flash(f'ጥያቄውን በማስገባት ላይ ስህተት ተከስቷል።', 'error')
        
        # Convert user to dict to avoid detached instance error
        user_data = {
            'id': user.id,
            'username': user.username,
            'total_earned': user.total_earned,
            'pending_payout': user.pending_payout
        }
                
        return render_template('payout_request.html', user=user_data)


# 3.9. የይለፍ ቃል መቀየር (Change Password)
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        with app.app_context():
            user = User.query.filter_by(id=user_id).first()
            
            if not user:
                flash('የተጠቃሚ መለያ አልተገኘም።', 'error')
                return redirect(url_for('dashboard'))

            if not check_password_hash(user.password_hash, current_password):
                flash('ያስገቡት የአሁኑ የይለፍ ቃል ትክክል አይደለም።', 'error')
            elif new_password != confirm_password:
                flash('አዲሱ የይለፍ ቃል እና የማረጋገጫው ቃል አይመሳሰሉም።', 'error')
            elif len(new_password) < 6:
                flash('አዲሱ የይለፍ ቃል ቢያንስ 6 ፊደላት መሆን አለበት።', 'error')
            else:
                try:
                    user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    flash('የይለፍ ቃልዎ በተሳካ ሁኔታ ተቀይሯል።', 'success')
                    return redirect(url_for('dashboard'))
                except Exception as e:
                    db.session.rollback()
                    flash(f'የይለፍ ቃል በመቀየር ላይ ስህተት ተከስቷል: {e}', 'error')
                    
    return render_template('change_password.html')


# 3.10. ማስታወቂያ ማየት (View Ads)
@app.route('/view_ads')
def view_ads():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    with app.app_context():
        available_ads = Ad.query.filter_by(is_active=True).all()
        
        today = func.date(func.now())
        viewed_today = db.session.execute(db.select(AdView.ad_id)
            .filter(AdView.user_id == user_id, AdView.status == 'REWARDED', func.date(AdView.date_viewed) == today)
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
                    parts = line.split(':', 1)
                    username = parts[0].strip()
                    password = parts[1].strip()
                    if username and password:
                        try:
                            new_inventory = Inventory(gmail_username=username, gmail_password=password)
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
                flash(f'ሥራው በተሳካ ሁኔታ ተረጋግጧል። ${PAYOUT_AMOUNT_PER_TASK:.2f} ለሰራተኛው ተጨምሯል።', 'success')

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
                flash(f'የ ${payout.amount:.2f} ክፍያ እንደተፈጸመ ምልክት ተደርጓል።', 'success')

            elif action == 'reject':
                payout.status = 'REJECTED'
                
                # ገንዘቡን ወደ pending_payout ይመልሳል
                if user:
                    user.pending_payout += payout.amount
                
                db.session.commit()
                flash(f'የ ${payout.amount:.2f} ክፍያ ጥያቄ ውድቅ ተደርጓል፣ ገንዘቡ ወደ ቀሪ ሂሳብ ተመልሷል።', 'info')
                
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
        app.run(debug=True, host='0.0.0.0', port=5000)
