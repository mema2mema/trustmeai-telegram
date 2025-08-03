
import pandas as pd
import matplotlib.pyplot as plt

def generate_summary():
    try:
        df = pd.read_csv("trade_log.csv")
        profit = df['profit'].sum()
        count = len(df)
        return f"📊 Total Trades: {count}\n💰 Total Profit: ${profit:.2f}"
    except:
        return "⚠️ Could not generate summary. No trade data found."

def generate_graph():
    try:
        df = pd.read_csv("trade_log.csv")
        df['equity'] = df['profit'].cumsum()
        plt.figure(figsize=(8,4))
        plt.plot(df['equity'])
        plt.title("Equity Curve")
        plt.xlabel("Trade")
        plt.ylabel("Profit")
        plt.tight_layout()
        plt.savefig("equity_curve.png")
        plt.close()
    except:
        pass
