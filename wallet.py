
import json
import os

BALANCE_FILE = "balance.json"

def get_balance():
    if not os.path.exists(BALANCE_FILE):
        return 0.0
    with open(BALANCE_FILE) as f:
        data = json.load(f)
    return data.get("balance", 0.0)

def request_withdraw(amount):
    if not os.path.exists(BALANCE_FILE):
        return "❌ No balance record found."
    with open(BALANCE_FILE) as f:
        data = json.load(f)
    balance = data.get("balance", 0.0)
    if amount > balance:
        return "❌ Insufficient funds."
    data["balance"] = round(balance - amount, 2)
    with open(BALANCE_FILE, "w") as f:
        json.dump(data, f)
    return f"✅ Withdraw request submitted: ${amount:.2f}"
