
import json
import uuid
from datetime import datetime
import os

WALLET_PATH = 'wallet_data.json'
WITHDRAW_HISTORY = 'withdraw_history.csv'

def load_wallet():
    with open(WALLET_PATH, 'r') as f:
        return json.load(f)

def save_wallet(data):
    with open(WALLET_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def generate_txid():
    return str(uuid.uuid4()).replace('-', '')[:16].upper()

def log_withdrawal(amount, txid, status='Processed'):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = f"{now},{amount},{txid},{status}\n"
    with open(WITHDRAW_HISTORY, 'a') as f:
        f.write(entry)

def request_withdrawal(amount):
    wallet = load_wallet()
    balance = wallet.get('balance', 0)

    if amount > balance:
        return f"Insufficient balance. Available: {balance}"

    txid = generate_txid()
    wallet['balance'] -= amount
    save_wallet(wallet)
    log_withdrawal(amount, txid)
    return f"Withdrawal of {amount} USDT successful!\nTXID: {txid}"
