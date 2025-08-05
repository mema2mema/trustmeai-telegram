from flask import Flask
from telegram_bot.bot_listener import start_bot

app = Flask(__name__)

@app.route('/')
def home():
    return "TrustMe AI Telegram Bot is running!"

if __name__ == "__main__":
    start_bot()