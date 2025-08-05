import pandas as pd

def generate_summary(csv_file):
    try:
        df = pd.read_csv(csv_file)
        if df.empty:
            return "No trade data available."

        total_trades = len(df)
        total_profit = df["profit"].sum()
        win_rate = (df["profit"] > 0).mean() * 100

        summary = (
            f"📊 Trade Summary:\n"
            f"Total Trades: {total_trades}\n"
            f"Total Profit: {total_profit:.2f} USDT\n"
            f"Win Rate: {win_rate:.2f}%"
        )
        return summary
    except Exception as e:
        return f"Error generating summary: {e}"
