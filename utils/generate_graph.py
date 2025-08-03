import matplotlib.pyplot as plt
def generate_graph():
    plt.plot([1, 2, 3], [100, 200, 150])
    plt.title('Equity Curve')
    plt.savefig('equity_curve.png')
    plt.close()
