# telegram_bot/__init__.py
from flask import Flask

# Create Flask app at package import time so Gunicorn can import it
app = Flask(__name__)

# Health route (simple root)
@app.route("/", methods=["GET"])
def health():
    return "✅ TrustMe AI Telegram Bot is running!", 200

# Import modules that register routes/handlers AFTER app is created.
# If your project has a bot listener that attaches routes to `app`, import it here.
try:
    from . import bot_listener  # noqa: F401
except Exception as e:
    # Don't crash module import; log for visibility
    import sys
    print(f"[telegram_bot] Warning importing bot_listener: {e}", file=sys.stderr)
