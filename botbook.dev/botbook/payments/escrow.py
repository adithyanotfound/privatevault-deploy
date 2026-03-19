class EscrowLedger:

    def __init__(self):
        self._balances = {}

    def deposit(self, member_id, amount):
        self._balances.setdefault(member_id, 0)
        self._balances[member_id] += amount

    def hold(self, member_id, amount):
        if self._balances.get(member_id,0) < amount:
            raise Exception("insufficient funds")
        self._balances[member_id] -= amount

    def release(self, member_id, amount):
        self._balances.setdefault(member_id,0)
        self._balances[member_id] += amount

    def balance(self, member_id):
        return self._balances.get(member_id,0)
