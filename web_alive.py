from flask import Flask

app = Flask(__name__)

@app.route('/')
def alive():
    return "TrustMe AI Telegram Bot is alive!"