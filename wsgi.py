# wsgi.py
# This shim ensures Gunicorn can find the Flask app
from telegram_bot import app as app
