# 🤖 NEW Bot Token & Setup Information

## 📝 Fill This Out With Your NEW Bot Details

### Step 1: Get NEW Bot from @BotFather

```
OLD BOT: @GtaskManager_bot (Token: 8375512551:AAGigsQGGR8iE9kXMcSCVr9OlDCkwfCn2PY)

NEW BOT: @_______________ (Token: _______________________________________________)
```

---

## 🔄 Replacement Instructions

### In `main.py` (Line 29-32):

#### BEFORE (Old Bot):
```python
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8375512551:AAGigsQGGR8iE9kXMcSCVr9OlDCkwfCn2PY')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', 'GtaskManager_bot')
```

#### AFTER (New Bot):
```python
BOT_TOKEN = os.environ.get('BOT_TOKEN', '___YOUR_NEW_TOKEN___')
TELEGRAM_BOT_USERNAME = os.environ.get('TELEGRAM_BOT_USERNAME', '___YOUR_NEW_USERNAME___')
```

---

## 📋 Render Environment Variables to Update

When deploying to Render, update these in the dashboard:

1. **BOT_TOKEN** = `___YOUR_NEW_TOKEN___`
2. **TELEGRAM_BOT_USERNAME** = `___YOUR_NEW_USERNAME___` (without @)
3. **WEBHOOK_URL** = `https://g-task.onrender.com/webhook` (stays same)

---

## ✅ Telegram Mini App Configuration

After deploying with NEW bot, configure in @BotFather:

1. Send `/setwebhook` to @BotFather
2. Select your NEW bot
3. Paste: `https://g-task.onrender.com/webhook`
4. Send `/setcommands` to add bot commands

---

## 🎯 Quick Checklist

- [ ] Create new bot in @BotFather
- [ ] Copy new bot token
- [ ] Copy new bot username
- [ ] Update main.py line 29-32
- [ ] Update Render environment variables
- [ ] Set webhook in @BotFather
- [ ] Test: Click "በ Telegram ይጀምሩ" on https://g-task.onrender.com
- [ ] Send `/start` to bot - should get welcome message

**✅ DONE!**
