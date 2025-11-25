# G-Task Manager

## Overview
G-Task Manager is a Flask-based web application for managing Gmail account creation tasks. Workers can take tasks, complete them, and earn payments. Administrators can manage the task inventory, verify completed tasks, and process payouts.

## Project Architecture

### Technology Stack
- **Backend**: Flask 3.0+ with SQLAlchemy 2.0+
- **Database**: PostgreSQL (Neon or Render-provided) with SQLite fallback for development
- **Authentication**: Werkzeug password hashing + Telegram Bot API
- **Frontend**: HTML templates with Jinja2, CSS3, Font Awesome icons, smooth animations
- **Deployment**: Gunicorn WSGI server on Render

### Directory Structure
```
.
├── main.py                 # Main Flask application (Render-compatible)
├── requirements.txt        # Python dependencies (cleaned, no duplicates)
├── Procfile               # Render deployment config
├── templates/             # HTML templates
│   ├── header.html
│   ├── footer.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   ├── payout_request.html
│   ├── admin_dashboard.html
│   ├── admin_add_tasks.html
│   ├── admin_verify_tasks.html
│   └── admin_payouts.html
└── static/                # Static assets
    └── style.css          # Main stylesheet with animations
```

### Database Models
- **User**: User accounts (workers and admins) with Telegram integration
  - `telegram_id`: Unique Telegram user ID
  - `telegram_login_token`: 24-hour temporary login token
- **Inventory**: Gmail account credentials with recovery emails
- **Task**: Task assignments to workers
- **Payout**: Payout request tracking
- **Device**: Device fingerprinting for fraud detection
- **DailyCheckIn**: Daily reward tracking
- **Ad**: Video ad configuration
- **AdView**: Ad view tracking

## ⚡ Render Deployment (Complete Guide)

### Step 1: Prepare GitHub Repository
```bash
# Make sure all changes are committed:
git add .
git commit -m "Render deployment ready - webhook compatible"
git push origin main
```

### Step 2: Create Render Service
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Select your GitHub repository
4. Configure:
   - **Name**: `g-task` (or your preferred name)
   - **Environment**: Python 3
   - **Region**: Choose closest to users
   - **Branch**: `main`

### Step 3: Set Build & Start Commands
In Render dashboard under "Build & Deploy":
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind=0.0.0.0:5000 --workers=2 main:app`

### Step 4: Add Environment Variables
In Render dashboard under "Environment":

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | PostgreSQL connection string | From Render Postgres or Neon |
| `SECRET_KEY` | Any random 32+ character string | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `BOT_TOKEN` | Your Telegram Bot Token | From @BotFather on Telegram |
| `TELEGRAM_BOT_USERNAME` | `GtaskManager_bot` | Your bot's username |
| `WEBHOOK_URL` | `https://your-render-url.onrender.com/webhook` | Your Render app URL + /webhook |
| `ADMIN_USERNAME` | `Admin` | Default admin username |
| `ADMIN_PASSWORD` | `070781` | Default admin password (change in production!) |

### Step 5: Database Setup (Render Postgres)
1. In Render dashboard, create a new "PostgreSQL" service
2. Copy the connection string
3. Paste as `DATABASE_URL` environment variable in web service
4. Wait for service to start (may take 1-2 minutes)

### Step 6: Deploy & Test
1. Click "Deploy" in Render dashboard
2. Watch logs for deployment progress
3. Once deployed, visit your Render URL
4. Login with:
   - **Username**: Admin
   - **Password**: 070781

### Step 7: Configure Telegram Webhook
After deployment is live:
1. Login to admin dashboard
2. Call: `https://your-render-url.onrender.com/telegram/set-webhook`
3. You should see: `{"status": "success", "message": "Webhook set successfully"}`
4. Test bot by sending `/start` to your Telegram bot

## 🔐 Telegram Bot Setup

### Create Telegram Bot
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions to name your bot
4. Copy the **BOT_TOKEN** provided
5. Send `/setusername` and choose username (e.g., GtaskManager_bot)

### Enable Features
1. Message @BotFather again
2. Send `/setcommands`
3. Select your bot
4. Copy-paste commands (format: `command - description`):
   ```
   balance - 💰 Check your earnings
   tasks - 📋 View your tasks
   help - ❓ Show available commands
   ```

### Webhook Details
- **Route**: `/webhook` (POST only)
- **URL**: `https://your-render-url.onrender.com/webhook`
- **Render-Compatible**: ✅ Handles all Telegram updates
- **Error Handling**: Always returns HTTP 200 (Telegram compatibility)

## Configuration Files

### environment Variables (Development - Replit)
Create `.env` file in root:
```
DATABASE_URL=sqlite:///g_task_manager.db
SECRET_KEY=Kq7bYxZ_3u9sP2hG_vR4wF1mJ_tL5cY_8oE
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_USERNAME=GtaskManager_bot
WEBHOOK_URL=https://your-replit-url.repl.co/webhook
ADMIN_USERNAME=Admin
ADMIN_PASSWORD=070781
```

### Procfile (Render)
Already configured:
```
web: gunicorn --bind=0.0.0.0:5000 --workers=2 main:app
```

### Requirements.txt (Render-Ready)
Cleaned and production-ready:
```
Flask>=3.0.0
Flask-SQLAlchemy>=3.0.0
SQLAlchemy>=2.0.0
gunicorn>=21.0.0
python-dotenv>=1.0.0
psycopg2-binary>=2.9.0
werkzeug>=3.0.0
requests>=2.28.0
Flask-Bcrypt>=1.0.1
Flask-Login>=0.6.2
Flask-Mail>=0.9.1
```

## 🎯 Features

### Worker Features
- ✅ User registration and login (email/Telegram)
- ✅ One-click Telegram login with auto-registration
- ✅ View available Gmail account tasks
- ✅ Take and complete tasks
- ✅ Request payouts (minimum ብር 40.00)
- ✅ View earnings and task history
- ✅ Daily check-in rewards (ብር 0.20/day)
- ✅ Video ad rewards
- ✅ Device-based fraud detection (one device per user)
- ✅ Telegram notifications for new tasks

### Admin Features
- ✅ Dashboard with statistics
- ✅ Add Gmail account tasks (bulk upload with recovery emails)
- ✅ Verify and approve completed tasks
- ✅ Manage payout requests
- ✅ Telegram payment notifications to workers
- ✅ Ad management and tracking

## 💰 Payment System
- **Earn**: ብር 10.00 per verified task
- **Daily Check-in**: ብር 0.20 per day
- **Ad Rewards**: Variable per ad
- **Minimum Payout**: ብር 40.00
- **Payment Method**: USDT (TRC20) wallet address

## 🔒 Security Features

### Device Fraud Detection
- SHA256 fingerprint of IP + User-Agent
- One device per user enforcement
- Prevents multiple accounts from same device
- Automatic device registration on first login

### Telegram Security
- HMAC-SHA256 hash verification
- 24-hour token expiry for auto-login
- Webhook validation from Telegram
- Secure password hashing (Werkzeug)

### Database Security
- PostgreSQL with secure connection strings
- Environment variables for all secrets
- No hardcoded credentials in code
- Session-based authentication

## 🚀 Deployment Status

### Latest Changes (2025-11-25)
- ✅ Render-compatible webhook at `/webhook`
- ✅ Environment variables support for SECRET_KEY
- ✅ Cleaned requirements.txt (no duplicates)
- ✅ Procfile configured for Render Gunicorn
- ✅ Proper error handling in webhook
- ✅ Request library imported for Telegram API calls
- ✅ Production-ready app configuration

### Production Readiness Checklist
- [x] Database models defined with relationships
- [x] Flask app with Gunicorn configuration
- [x] Telegram webhook properly configured
- [x] Environment variables for all secrets
- [x] Device fraud detection implemented
- [x] Admin panel with task/payout management
- [x] Worker dashboard with earnings tracking
- [x] Daily rewards system
- [x] Ad viewing system
- [x] Error handling and logging
- [x] HTML templates with smooth animations

## Notes
- Language: Amharic (ኦሮሞ) with English fallback
- Database auto-initializes on first run
- All routes protected with session-based authentication
- Webhook requires BOT_TOKEN and WEBHOOK_URL configuration
- Telegram notifications sent in real-time via Telegram Bot API
