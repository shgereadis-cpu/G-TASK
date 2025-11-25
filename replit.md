# G-Task Manager

## Overview
G-Task Manager is a Flask-based web application for managing Gmail account creation tasks. Workers can take tasks, complete them, and earn payments. Administrators can manage the task inventory, verify completed tasks, and process payouts.

## Project Architecture

### Technology Stack
- **Backend**: Flask 3.0.3 with SQLAlchemy 2.0.25
- **Database**: PostgreSQL (with SQLite fallback for local development)
- **Authentication**: Werkzeug password hashing
- **Frontend**: HTML templates with Jinja2, CSS3, Font Awesome icons
- **Deployment**: Gunicorn WSGI server

### Directory Structure
```
.
├── main.py                 # Main Flask application
├── requirements.txt        # Python dependencies
├── Procfile               # Heroku deployment config
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
    └── style.css          # Main stylesheet
```

### Database Models
- **User**: Stores user accounts (workers and admins) with optional Telegram integration
  - `telegram_id`: Unique Telegram user ID for Telegram login
- **Inventory**: Gmail account credentials available for tasks
- **Task**: Assigned tasks to workers
- **Payout**: Payout requests from workers

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-provided by Replit)
- `SECRET_KEY`: Flask session secret (auto-generated)
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for authentication (required for Telegram login)
- `TELEGRAM_BOT_USERNAME`: Telegram bot username (set to: GtaskManager_bot)
- `WEBHOOK_URL`: Full webhook URL for Telegram (e.g., https://yourapp.replit.dev/telegram/webhook)

### Default Admin Account
- **Username**: Admin
- **Password**: 070781

## Development Workflow

### Running Locally
The Flask development server runs on port 5000:
```bash
python main.py
```

### Deployment
The application is configured for autoscale deployment using Gunicorn:
```bash
gunicorn --bind=0.0.0.0:5000 --reuse-port main:app
```

## Features

### Worker Features
- User registration and login (standard or via Telegram)
- Telegram Login Widget integration for one-click authentication
- View available tasks
- Take and complete tasks
- Submit completion codes
- Request payouts (minimum $1.00)
- View earnings and task history
- Receive Telegram notifications when new tasks are added

### Admin Features
- View dashboard with statistics
- Add Gmail account tasks in bulk
- Verify submitted tasks
- Approve/reject payout requests
- Manage task inventory

## Payment System
- Workers earn ብር 10.00 per verified task
- Minimum payout: ብር 40.00
- Payment method: USDT (TRC20) wallet

## Recent Changes

### 2025-11-25: Device Fraud Detection System (Latest)
- One device per user enforcement - prevents multiple accounts from same device
- Device fingerprinting based on IP address + User-Agent (SHA256 hash)
- Automatic device registration on first login
- Blocks accounts if device is already registered to another user
- Prevents balance/reward manipulation across multiple accounts
- Works on login and daily check-in routes
- Tracks device activity (last_activity timestamp)
- Database model: `Device` with device_fingerprint, ip_address, user_agent
- Error messages in Amharic for blocked users
- Security alerts logged when fraud detected

### 2025-11-25: Daily Check-In Task
- Added daily check-in task feature for workers
- Reward amount: ብር 0.20 per day (one check-in per user per day)
- Workers can check-in from dashboard to earn instant reward
- Reward is added directly to pending_payout balance
- Database model: `DailyCheckIn` with unique constraint (user_id, check_in_date)
- Route: `POST /daily_checkin` - AJAX-based instant completion
- Dashboard shows check-in button alongside video ads
- One-time check-in per day enforcement at database level

### 2025-11-25: Recovery Email Support
- Added recovery email field to Gmail account inventory
- Admin can now add tasks with format: `gmail_username:gmail_password:recovery_email`
- Recovery email is displayed to workers when they take tasks
- Stored securely in database for account recovery purposes
- Database migration: Added `recovery_email` column to inventory table

### 2025-11-25: Payment Notification
- Added Telegram payment notifications when worker payouts are approved
- Message: "💰 እንኳን ደስ አልዎት! ደሞዝህ ብር X.XX ወደ ዋሌትህ ተልኳል - እባክዎን ዋሌትዎን ቼክ ያድርጉ"
- Sent automatically when admin marks payout as PAID
- Only sent to workers with linked Telegram accounts
- Function: `send_payment_notification(user_id, amount)`

### 2025-11-25: Telegram Auto-Login
- Telegram users now automatically log in when clicking "🌐 Visit Website" button
- No need to enter username/password
- Temporary login tokens generated for each user (24-hour expiry)
- Tokens are secure (56-character URL-safe random strings)
- One-click login from Telegram to website dashboard
- Tokens are regenerated after each login (enables logout/login cycles)
- Users can logout and login again without needing to send /start command
- Database migration: Added `telegram_login_token` and `telegram_token_expires` columns

### 2025-11-25: Emoji Bot Messages
- All Telegram bot messages now include emojis for better UX
- New task notification: 🚀 "አዲስ ስራ ተጨመረ ፍጠን አሁን ስራ ውሰድ"
- Account not linked: 🔐 (when /balance or /tasks without account)
- Unknown command: ❓ (for unrecognized commands)
- Registration error: ⚠️ (if auto-registration fails)
- Existing messages retain their emojis: 💰 (balance), 📋 (tasks), 👋 (welcome), 🎉 (new user)

### 2025-11-25: Admin Credentials Configured
- Admin account: Username **Admin**, Password **070781**
- Environment variables set: ADMIN_USERNAME and ADMIN_PASSWORD
- Auto-created on app startup if not already in database
- Credentials stored securely as hashed passwords

### 2025-11-25: Bot Menu Commands
- Moved commands from welcome message to bot menu
- Users see `/balance`, `/tasks`, `/help` in Telegram command menu with descriptions
- Cleaner welcome messages without command clutter
- Commands appear when users click the "/" button in Telegram chat
- Professional and intuitive user experience

### 2025-11-25: Auto-Registration for Telegram Users
- New Telegram users are automatically registered when they send `/start` to the bot
- Username generated from: `FirstName_TelegramID` with collision handling
- Random password generated for security
- Instant access to commands: `/balance`, `/tasks`, `/help`
- Each welcome message includes a **"🌐 Visit Website"** button
- No need to visit website or use Telegram login widget - fully automatic!

### 2025-11-25: Telegram Button UI
- Updated welcome message to show login link as a clickable button instead of plain text
- Added `send_telegram_message_with_button()` function for inline keyboard markup
- Welcome message now displays: "🔐 Login & Link Account" button
- New users see a professional button-based interface

### 2025-11-25: Telegram Webhook Integration
- Added `/telegram/webhook` POST route for receiving Telegram updates
- Implemented bot commands: `/start`, `/help`, `/balance`, `/tasks`
- Created `send_telegram_message()` helper function for bot responses
- Added `/telegram/set-webhook` route for admin webhook configuration
- Bot can now respond directly to user messages via Telegram
- Webhook receives real-time updates from Telegram API

### 2025-11-25: Telegram Integration
- Added Telegram Login Widget to login page
- Implemented secure HMAC-SHA256 hash verification for Telegram authentication
- Added `telegram_id` column to User model for Telegram user linking
- Created `/telegram_login_check` route with 24-hour freshness validation
- Implemented `send_notification_to_all_telegram_users()` function
- Integrated automatic Telegram notifications when new tasks are added to inventory
- Added robust username collision handling for Telegram users
- Configured TELEGRAM_BOT_USERNAME environment variable (GtaskManager_bot)

### 2025-11-23: Initial Setup
- Imported from GitHub and set up for Replit environment
- Created proper Flask directory structure (templates, static folders)
- Created comprehensive CSS stylesheet
- Fixed database schema (password_hash VARCHAR(256))
- Configured Flask workflow on port 5000
- Set up deployment configuration with Gunicorn
- Added missing templates (payout_request.html, admin_payouts.html)

## Telegram Bot Setup

### Webhook Configuration
1. Set `WEBHOOK_URL` environment variable to your app's webhook URL (e.g., `https://yourapp.replit.dev/telegram/webhook`)
2. Call the admin endpoint to configure: `POST /telegram/set-webhook`
   - Requires admin login
   - Registers the webhook with Telegram API
   - Telegram will now send updates directly to your app

### Bot Commands
Users can interact with the bot via these commands:
- `/start` or `/help` - Display welcome message and available commands
- `/balance` - Show user's earnings and pending payout
- `/tasks` - View task statistics

### Webhook Features
- Receives real-time updates from Telegram when users message the bot
- Automatically links Telegram users to G-Task Manager accounts
- Sends instant responses to user commands
- Integrates with existing task notification system

## Notes
- Application uses Amharic language (Ethiopia)
- Database automatically initializes on first run
- All routes are protected with session-based authentication
- Webhook requires TELEGRAM_BOT_TOKEN and WEBHOOK_URL to be configured
