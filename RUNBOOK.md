
## Quick Runbook

### 0) Prereqs
- Railway service connected to this repo contents.
- Env var set in Railway: `TELEGRAM_BOT_TOKEN`.

### 1) Deploy on Railway
- Ensure Procfile is detected: `web: gunicorn wsgi:app --workers=1 --threads=8 --timeout=30`.
- Deploy; wait until Running.

### 2) Set webhook (Windows PowerShell)
```powershell
cd scripts
.\setup-webhook.ps1 -TELEGRAM_BOT_TOKEN "<YOUR_BOT_TOKEN>" -BASE "https://<your-subdomain>.up.railway.app"
```

### 3) Verify
```powershell
.\health.ps1 -BASE "https://<your-subdomain>.up.railway.app"
# Expect 200
```

### 4) Test in Telegram
Send `/start`, `/status`, `/trades` to your bot chat.
