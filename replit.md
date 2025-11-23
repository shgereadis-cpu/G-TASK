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
- **User**: Stores user accounts (workers and admins)
- **Inventory**: Gmail account credentials available for tasks
- **Task**: Assigned tasks to workers
- **Payout**: Payout requests from workers

## Configuration

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-provided by Replit)
- `SECRET_KEY`: Flask session secret (auto-generated)

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
- User registration and login
- View available tasks
- Take and complete tasks
- Submit completion codes
- Request payouts (minimum $1.00)
- View earnings and task history

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

## Recent Changes (2025-11-23)
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
