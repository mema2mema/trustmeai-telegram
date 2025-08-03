import json
def get_balance():
    with open('balance.json') as f:
        return json.load(f)['balance']

def request_withdraw():
    return '✅ Withdrawal request received. Processing...'
