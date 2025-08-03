
import pandas as pd
import matplotlib.pyplot as plt

def generate_summary():
    try:
        df = pd.read_csv('backtest.csv')
        total_profit = df['profit'].sum()
        total_trades = len(df)
        win_rate = (df['profit'] > 0).mean() * 100
        return f"📈 Total Trades: {total_trades}\n💰 Total Profit: ${total_profit:.2f}\n✅ Win Rate: {win_rate:.2f}%"
    except Exception as e:
        return f"Error generating summary: {e}"

def generate_graph():
    try:
        df = pd.read_csv('backtest.csv')
        df['equity'] = df['profit'].cumsum()
        plt.figure()
        plt.plot(df['equity'])
        plt.title('Equity Curve')
        plt.xlabel('Trade #')
        plt.ylabel('Cumulative Profit')
        plt.savefig('equity_curve.png')
        plt.close()
    except Exception as e:
        print("Graph error:", e)
