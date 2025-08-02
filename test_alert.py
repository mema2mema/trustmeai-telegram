
from telegram_push import send_telegram_alert

if __name__ == "__main__":
    response = send_telegram_alert("🚀 Test Alert: RedHawk trade executed!")
    print("Alert sent:", response)
