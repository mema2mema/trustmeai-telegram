# wsgi.py
# Gunicorn entrypoint for Railway. Imports Flask app from the telegram_bot package.
from telegram_bot import app

if __name__ == "__main__":
    # Local run helper (not used on Railway)
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
