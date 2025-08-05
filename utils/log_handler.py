def get_log_text():
    try:
        with open("trades/trades.csv", "r") as file:
            lines = file.readlines()[-5:]
        return "🧾 Last Trades:\n" + "".join(lines)
    except Exception as e:
        return f"Failed to fetch log: {e}"
