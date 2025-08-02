import pandas as pd
import time
import os
import telegram

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"
CHAT_ID = "PASTE_YOUR_CHAT_ID_HERE"

def send_alert(msg):
    bot = telegram.Bot(token=BOT_TOKEN)
    bot.send_message(chat_id=CHAT_ID, text=msg)

def tail_csv(file_path, last_line):
    if not os.path.exists(file_path):
        return [], last_line
    with open(file_path, "r") as f:
        lines = f.readlines()
    if last_line < len(lines):
        new_lines = lines[last_line:]
        return new_lines, len(lines)
    return [], last_line

def main():
    print("🔌 Live Trade Log Viewer started...")
    last_line = 1  # Skip header
    while True:
        new_logs, last_line = tail_csv("trades.csv", last_line)
        for log in new_logs:
            send_alert(f"📈 New Trade: {log.strip()}")
        time.sleep(30)

if __name__ == "__main__":
    main()
