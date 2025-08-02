
import json
import requests

def send_telegram_alert(message):
    with open('telegram_config.json') as f:
        config = json.load(f)
    bot_token = config['bot_token']
    chat_id = config['chat_id']
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.json()
