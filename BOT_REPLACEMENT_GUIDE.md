# 🤖 Bot Replacement Guide - Complete Setup for Render Deployment

## 📋 Step 1: Create New Telegram Bot

### In Telegram App:
1. Message **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "G-Task Manager V2")
4. Choose a username (e.g., `GtaskManager_v2_bot`)
5. **Copy the NEW BOT TOKEN** - Save it!

**Example Output:**
```
🎉 Done! Congratulations on your new bot. You will find it at t.me/YourBotUsername.
Use this token to access the HTTP API:
123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
Keep your token secure and store it safely!
```

---

## 📝 Step 2: Update Code with NEW Bot Token

### Open `main.py` and find Line 29-32:

**Current (OLD BOT):**
```python
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8375512551:AAGigsQGGR8iE9kXMcSCVr9OlDCkwfCn2PY')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'GtaskManager_bot')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://g-task.onrender.com/webhook')
```

**Replace with NEW BOT (example):**
```python
BOT_TOKEN = os.environ.get('BOT_TOKEN', '987654321:XYZabcdefghijklmnopqrstuvwxyz123456')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'GtaskManager_v2_bot')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'https://g-task.onrender.com/webhook')
```

---

## 🚀 Step 3: Render Deployment Environment Variables

### Go to Render Dashboard:
1. Select your G-Task service
2. Click **Environment**
3. Add/Update these variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `BOT_TOKEN` | `YOUR_NEW_BOT_TOKEN_HERE` | From @BotFather |
| `TELEGRAM_BOT_USERNAME` | `your_new_bot_username` | From @BotFather (without @) |
| `WEBHOOK_URL` | `https://g-task.onrender.com/webhook` | Render app URL + /webhook |
| `DATABASE_URL` | `postgresql://...` | Your PostgreSQL connection |
| `SECRET_KEY` | `any_random_32char_string` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ADMIN_USERNAME` | `Admin` | Default admin |
| `ADMIN_PASSWORD` | `070781` | Default password (change in production!) |

---

## ✅ Step 4: Set Webhook with NEW Bot

### Message @BotFather:
```
/setwebhook
```

### Select your NEW bot:
```
GtaskManager_v2_bot
```

### Paste webhook URL:
```
https://g-task.onrender.com/webhook
```

---

## 🔐 Step 5: Configure Bot Commands

### Message @BotFather:
```
/setcommands
```

### Select your bot and add commands:
```
balance - 💰 Check your earnings
tasks - 📋 View your tasks
help - ❓ Show available commands
```

---

## 📤 Step 6: Deploy to Render

### Commit changes:
```bash
git add main.py
git commit -m "Update to new Telegram bot token for Render deployment"
git push origin main
```

### Render will auto-deploy

### Verify deployment:
1. Visit https://g-task.onrender.com
2. Click "በ Telegram ይጀምሩ"
3. Should open Mini App in @YourNewBotUsername
4. Test /start command

---

## 🎯 Summary

| Component | Old Bot | New Bot |
|-----------|---------|---------|
| Bot Token | `8375512551:AAGigsQGGR8iE9kXMcSCVr9OlDCkwfCn2PY` | `YOUR_NEW_TOKEN` |
| Bot Username | `@GtaskManager_bot` | `@YourNewBotUsername` |
| Webhook URL | `https://g-task.onrender.com/webhook` | `https://g-task.onrender.com/webhook` (same) |
| Code Changes | `main.py` line 29-32 | Update with new token + username |
| Environment | `BOT_TOKEN` and `TELEGRAM_BOT_USERNAME` | Set in Render dashboard |

---

## ⚠️ Important Notes

1. **Keep OLD bot running** until NEW bot is fully tested
2. **Test locally first** - Update main.py and test in Replit
3. **Update webhook** - NEW bot must have webhook configured at @BotFather
4. **Database persists** - All user data transfers automatically
5. **No code changes needed** - Only bot token and username change

**✅ READY FOR NEW BOT!**
