# ======================================================
# G-TASK MANAGER: GMAIL ACCOUNT CREATION TASK MANAGER
# Version: 2.0 (FINAL BACKEND: PostgreSQL/SQLAlchemy)
# Author: Gemini (AI)
# ======================================================

import os
import time
from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv # ሚስጥሮችን ከአካባቢ ተለዋዋጮች (Secrets) ለመጫን

# --- 0. ENV SETUP & CONFIGURATION ---
load_dotenv() # በ Replit ላይ አውቶማቲክ ይሰራል
app = Flask(__name__)

# Secret key from environment (required for production)
# Try SECRET_KEY first, fallback to SESSION_SECRET if available
secret_key = os.environ.get('SECRET_KEY') or os.environ.get('SESSION_SECRET')
if not secret_key:
    raise RuntimeError("SECRET_KEY or SESSION_SECRET environment variable must be set. Please add SECRET_KEY to Replit Secrets.")
app.secret_key = secret_key 

# Database Configuration (Neon/PostgreSQL or SQLite fallback)
# የ DATABASE_URL ሚስጥር ከ Replit Secrets ይነበባል
database_url = os.environ.get('DATABASE_URL', 'sqlite:///g_task_manager.db')
# Remove extra quotes and fix HTML encoding if present
database_url = database_url.strip("'\"").replace('&amp;', '&')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

MIN_PAYOUT = 0.10 
PAYOUT_AMOUNT_PER_TASK = 0.10 

# --- 1. DATABASE MODELS (SQLAlchemy Models) ---

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    total_earned = db.Column(db.Float, default=0.0)
    pending_payout = db.Column(db.Float, default=0.0)
    
    # Relationships
    tasks = db.relationship('Task', backref='worker', lazy='dynamic')
    payouts = db.relationship('Payout', backref='requester', lazy='dynamic')

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
    wallet_address = db.Column(db.String(255), nullable=False)
    date_requested = db.Column(db.DateTime, default=func.now())
    date_paid = db.Column(db.DateTime)

# --- 2. DATABASE INIT & HELPER FUNCTIONS ---

def init_db():
    """የዳታቤዝ ሠንጠረዦችን ይፈጥራል እና ነባሪ አድሚን ያስገባል።"""
    with app.app_context():
        # ሁሉንም ሞዴሎች በመጠቀም ሠንጠረዦችን ይፈጥራል
        db.create_all() 
        
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
                wallet_address = request.form['wallet_address']
                
                if amount < MIN_PAYOUT:
                    flash(f'ዝቅተኛው የክፍያ መጠን ${MIN_PAYOUT:.2f} ነው።', 'error')
                elif amount > user.pending_payout:
                    flash('ሊወጣ ከሚችለው ቀሪ ሂሳብ በላይ ጠይቀዋል።', 'error')
                elif not wallet_address:
                    flash('የUSDT Wallet አድራሻ ማስገባት አለብዎት።', 'error')
                else:
                    # 1. የክፍያ ጥያቄ ወደ payouts ሠንጠረዥ ያስገባል
                    new_payout = Payout(user_id=user_id, amount=amount, wallet_address=wallet_address)
                    db.session.add(new_payout)
                    
                    # 2. ከሰራተኛው ቀሪ ሂሳብ ላይ ይቀንሳል
                    user.pending_payout -= amount
                                         
                    db.session.commit()
                    flash(f'የ ${amount:.2f} ክፍያ ጥያቄ ገብቷል። አስተዳዳሪ እስኪያረጋግጥ ይጠብቁ።', 'success')
                    return redirect(url_for('dashboard'))

            except ValueError:
                flash('ትክክለኛ መጠን ያስገቡ።', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'ጥያቄውን በማስገባት ላይ ስህተት ተከስቷል: {e}', 'error')
                
    return render_template('payout_request.html', user=user)


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
        payout_requests = db.session.execute(db.select(Payout.id.label('payout_id'), Payout.amount, Payout.wallet_address, Payout.date_requested, User.username.label('worker_username'))
            .join(User, Payout.user_id == User.id)
            .filter(Payout.status == 'REQUESTED')
            .order_by(Payout.date_requested.asc())
        ).all()
    
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