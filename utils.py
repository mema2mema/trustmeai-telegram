
import pandas as pd
import matplotlib.pyplot as plt

def generate_summary(csv_file='trades.csv'):
    df = pd.read_csv(csv_file)
    total_trades = len(df)
    total_profit = df['profit'].sum()
    win_rate = (df['profit'] > 0).mean() * 100

    summary = (
        f"📊 Trade Summary:\n"
        f"Total Trades: {total_trades}\n"
        f"Total Profit: {total_profit:.2f}\n"
        f"Win Rate: {win_rate:.2f}%\n"
    )
    return summary

def generate_graph(csv_file='trades.csv', output_file='graph.png'):
    df = pd.read_csv(csv_file)
    df['equity'] = df['profit'].cumsum()
    plt.figure(figsize=(10, 5))
    plt.plot(df['timestamp'], df['equity'], marker='o')
    plt.title('Equity Curve')
    plt.xlabel('Timestamp')
    plt.ylabel('Cumulative Profit')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()

def analyze_backtest(file_path):
    df = pd.read_csv(file_path)
    total_trades = len(df)
    total_profit = df['profit'].sum()
    win_rate = (df['profit'] > 0).mean() * 100
    max_drawdown = df['profit'].cumsum().min()
    best_trade = df['profit'].max()
    worst_trade = df['profit'].min()

    summary = (
        f"📥 Backtest Analysis:\n"
        f"Total Trades: {total_trades}\n"
        f"Net Profit: {total_profit:.2f}\n"
        f"Win Rate: {win_rate:.2f}%\n"
        f"Max Drawdown: {max_drawdown:.2f}\n"
        f"Best Trade: {best_trade:.2f}\n"
        f"Worst Trade: {worst_trade:.2f}"
    )
    return summary
