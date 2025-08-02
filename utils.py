def generate_summary():
    return "📊 Dummy summary: No trades yet."

def generate_graph():
    import matplotlib.pyplot as plt
    import pandas as pd
    import io

    df = pd.DataFrame({"Day": [1, 2, 3], "Profit": [10, 15, 20]})
    fig, ax = plt.subplots()
    ax.plot(df["Day"], df["Profit"], marker='o')
    ax.set_title("Dummy Equity Curve")
    ax.set_xlabel("Day")
    ax.set_ylabel("Profit")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    return buf
