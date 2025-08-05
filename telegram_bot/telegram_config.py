
import json

with open("telegram_bot/telegram_config.json", "r") as file:
    config = json.load(file)

TELEGRAM_TOKEN = config["bot_token"]
CHAT_ID = config["chat_id"]
