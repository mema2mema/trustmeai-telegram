
def handle_log():
    try:
        with open("trades/trades.csv", "r") as file:
            lines = file.readlines()
            return "".join(lines[-10:])  # last 10 trades
    except Exception as e:
        return f"Error reading log: {str(e)}"
