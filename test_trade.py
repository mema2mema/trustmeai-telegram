from telegram_bot import add_trade

# Example mock trade (fires a Telegram alert and saves to data/trades.csv)
# Run:  python test_trade.py
add_trade("BUY", "BTC/USDT", 28800.50, 1.25)
print("Mock trade sent.")
