
import pandas as pd

def generate_insight(csv_file='trades.csv'):
    df = pd.read_csv(csv_file)
    total_trades = len(df)
    total_profit = df['profit'].sum()
    win_rate = (df['profit'] > 0).mean() * 100
    avg_profit = df['profit'].mean()
    best_trade = df['profit'].max()
    worst_trade = df['profit'].min()

    insight = "🤖 AI Insight Report:\n"
    insight += f"- Trades Analyzed: {total_trades}\n"
    insight += f"- Win Rate: {win_rate:.2f}%\n"
    insight += f"- Avg Profit per Trade: {avg_profit:.2f}\n"
    insight += f"- Best Trade: {best_trade:.2f}, Worst Trade: {worst_trade:.2f}\n"

    if win_rate > 60:
        insight += "\n👍 Your strategy is profitable. Keep optimizing entry timing."
    elif win_rate > 45:
        insight += "\n⚠️ Moderate win rate. Focus on filtering out bad trades."
    else:
        insight += "\n🚨 Your strategy may need rework. Try limiting trading hours or use stop loss."

    return insight
