import pandas as pd
import matplotlib.pyplot as plt

def generate_summary():
    df = pd.read_csv("trades.csv")
    total_profit = df["Profit"].sum()
    win_rate = (df["Profit"] > 0).mean() * 100
    num_trades = len(df)
    return f"📊 Total Profit: ${total_profit:.2f}\n🏆 Win Rate: {win_rate:.1f}%\n📈 Total Trades: {num_trades}"

def generate_graph():
    df = pd.read_csv("trades.csv")
    df["Equity"] = df["Profit"].cumsum()
    plt.figure(figsize=(10, 4))
    plt.plot(df["Equity"])
    plt.title("Equity Curve")
    plt.xlabel("Trade #")
    plt.ylabel("Equity ($)")
    plt.grid()
    plt.tight_layout()
    plt.savefig("equity_curve.png")