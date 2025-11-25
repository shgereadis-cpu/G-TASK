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

### Default Admin Account
- **Username**: Admin
- **Password**: password123
- **Note**: Change this password immediately in production!

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
- Workers earn $0.10 per verified task
- Minimum payout: $1.00
- Payment method: USDT (TRC20) wallet

## Recent Changes

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

## Notes
- Application uses Amharic language (Ethiopia)
- Database automatically initializes on first run
- All routes are protected with session-based authentication
