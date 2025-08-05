from telegram_bot.bot_listener import start_bot
from web_alive import app
import threading

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=8000)