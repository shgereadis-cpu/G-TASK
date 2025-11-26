# G-Task Manager - Production Ready

## 🚀 Overview
G-Task Manager is a **Telegram Mini App** for managing Gmail account creation tasks with automatic worker payment via Telegram. **NOW DEPLOYED ON RENDER** with @GTASKpro_bot.

## ⚡ Current Status
- ✅ **Bot**: @GTASKpro_bot (Token: 8535083603:AAGAFlbMYewLE_bv_GIlXJ1Jzd0epHY_7M0)
- ✅ **Deployment**: Render.com (https://g-task.onrender.com)
- ✅ **Database**: PostgreSQL with SSL
- ✅ **Frontend**: Telegram Mini App (No traditional login/signup)
- ✅ **Authentication**: Telegram Mini App SDK
- ✅ **Webhook**: Active at /webhook endpoint

## 📋 Technology Stack
- **Backend**: Flask 3.0+ with Gunicorn (Production WSGI)
- **Database**: PostgreSQL with SSL (sslmode=require)
- **Bot**: Telegram Bot API (Polling/Webhook)
- **Frontend**: Telegram Mini App (Web App SDK)
- **Deployment**: Render.com (autoscale)

## 🎯 Telegram Mini App Flow
```
User opens @GTASKpro_bot in Telegram
         ↓
  Mini App loads
         ↓
  User clicks "በ Telegram ይጀምሩ"
         ↓
  Telegram SDK sends user data
         ↓
  Auto-registers/logs in
         ↓
  Dashboard loads with tasks
         ↓
  Can take tasks, earn money, request payouts
```

## 📦 Production Environment Variables (Render)

| Variable | Value | Required |
|----------|-------|----------|
| `BOT_TOKEN` | `8535083603:AAGAFlbMYewLE_bv_GIlXJ1Jzd0epHY_7M0` | ✅ Yes |
| `TELEGRAM_BOT_USERNAME` | `GTASKpro_bot` | ✅ Yes |
| `WEBHOOK_URL` | `https://g-task.onrender.com/webhook` | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection string | ✅ Yes |
| `SECRET_KEY` | Random 32+ character string | ✅ Yes |
| `ADMIN_USERNAME` | `Admin` | ⏳ Optional |
| `ADMIN_PASSWORD` | `070781` | ⏳ Optional |
| `ENV` | `production` | ⏳ Optional |

## 🚀 Render Deployment Configuration

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
gunicorn --bind=0.0.0.0:5000 --workers=2 main:app
```

### Deployment Type
- **Type**: Web Service (autoscale)
- **Region**: Closest to users
- **Port**: 5000 (bound to 0.0.0.0)

## 🔧 Webhook Configuration (@BotFather)

```bash
/setwebhook
Select: @GTASKpro_bot
URL: https://g-task.onrender.com/webhook
```

## 💻 Routes & Endpoints

### Public Routes
- `GET /` - Home page (shows "በ Telegram ይጀምሩ" button)
- `GET /miniapp` - Telegram Mini App entry point
- `POST /miniapp_login` - Mini App authentication handler
- `POST /webhook` - Telegram webhook (receives bot messages)
- `POST /telegram/webhook` - Alternate webhook endpoint

### Protected Routes (Requires Authentication)
- `GET /dashboard` - User dashboard with tasks
- `POST /take_task` - Take a Gmail account task
- `POST /complete_task` - Submit completed task
- `GET /payout_request` - Request payout form
- `POST /submit_payout` - Submit payout request

### Admin Routes (Requires Admin Access)
- `GET /admin/dashboard` - Admin statistics
- `GET /admin/add_tasks` - Add tasks form
- `POST /admin/upload_tasks` - Bulk upload tasks
- `GET /admin/verify_tasks` - Verify completed tasks
- `GET /admin/payouts` - Manage payout requests

## 🔐 Security Features

- ✅ PostgreSQL SSL (sslmode=require)
- ✅ Connection pooling (pool_pre_ping, pool_recycle)
- ✅ Secure session management
- ✅ Telegram Mini App SDK authentication
- ✅ HMAC-SHA256 webhook verification
- ✅ Password hashing (Werkzeug)
- ✅ Timeout protection (10s database connect)

## 📊 Database Schema

### Users Table
- id (PK)
- username (unique)
- password_hash
- is_admin
- total_earned
- pending_payout
- telegram_id (unique)
- telegram_login_token
- telegram_token_expires

### Inventory Table
- id (PK)
- gmail_username (unique)
- gmail_password
- recovery_email
- status
- date_added

### Tasks Table
- id (PK)
- inventory_id (FK)
- user_id (FK)
- completion_code
- status
- date_assigned
- date_completed

### Payouts Table
- id (PK)
- user_id (FK)
- amount
- status
- payment_method
- recipient_name
- payment_details
- date_requested
- date_paid

## 💰 Payment Model
- **Earn per task**: ბር 10.00
- **Daily check-in**: ብር 0.20
- **Ad rewards**: Variable
- **Minimum payout**: ብር 40.00

## 🎯 File Structure
```
.
├── main.py                  # Flask app (Render-ready)
├── requirements.txt         # Python dependencies
├── Procfile                 # Gunicorn production config
├── templates/
│   ├── header.html         # Header with Telegram nav
│   ├── footer.html         # Footer
│   ├── index.html          # Home page
│   ├── miniapp.html        # Mini App login
│   ├── dashboard.html      # User dashboard
│   ├── payout_request.html # Payout form
│   ├── admin_*.html        # Admin templates
│   └── ...
└── static/
    └── style.css           # Styling with animations
```

## 📝 Recent Changes (Production)
- ✅ Removed traditional login/signup (replaced with Mini App)
- ✅ Updated bot to @GTASKpro_bot
- ✅ Configured Telegram Mini App SDK
- ✅ PostgreSQL SSL with connection pooling
- ✅ Webhook processing for bot messages
- ✅ Production-grade Gunicorn configuration
- ✅ Environment-based debug mode

## ✅ Production Readiness Checklist
- [x] Telegram Mini App configured
- [x] Webhook endpoints ready
- [x] Database SSL configured
- [x] Gunicorn production server
- [x] Environment variables documented
- [x] All errors handled gracefully
- [x] Bot auto-registers users
- [x] Database auto-initializes
- [x] Admin panel fully functional
- [x] Task management system
- [x] Payout tracking

## 🎊 Deployment Status
**PRODUCTION READY** ✅

All components tested and configured for Render.com deployment with @GTASKpro_bot.

Visit: https://g-task.onrender.com
Bot: @GTASKpro_bot (Telegram Mini App)
