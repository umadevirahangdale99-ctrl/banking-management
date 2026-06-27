import secrets

from transaction import Transaction

class Account:
    def __init__(self,account_no,name,balance=0, photo_path="", pin=None, generate_pin=False):
        self.account_no = account_no
        self.name = name
        self.balance = balance
        self.transactions = []
        self.photo_path = photo_path or ""
        self.pin = self._generate_pin() if generate_pin or pin is None else str(pin).strip()

    @staticmethod
    def _generate_pin():
        return f"{secrets.randbelow(10000):04d}"

    def deposit(self, amount):

        if amount > 0:
            self.balance += amount
            transaction = Transaction(
                 "Deposit",
                 amount

            )
            self.transactions.append(transaction)
            return True
        return False

    def deposite(self,amount):
        return self.deposit(amount)
    
    def withdraw(self,amount):
        if amount <= self.balance:
            self.balance -= amount
            transaction = Transaction(
                 "Withdraw",
                 amount

            )
            self.transactions.append(transaction)
            return True
        return False
    
    def get_balance(self):
        return self.balance
    
    def to_dict(self):
        return {
            "account_no": self.account_no,
            "name": self.name,
            "balance": self.balance,
            "photo_path": self.photo_path,
            "pin": self.pin,
            "transactions": [
                t.to_dict() if hasattr(t, "to_dict") else t
                for t in self.transactions
            ]
        }
    
class SavingAccount(Account)  :
        def __init__(self, account_no, name, balance=0, photo_path="", pin=None, generate_pin=False):
            super().__init__(account_no, name, balance, photo_path, pin, generate_pin)

class currentAccount(Account):
        def __init__(self, account_no, name, balance=0, photo_path="", pin=None, generate_pin=False):
            super().__init__(account_no, name, balance, photo_path, pin, generate_pin)




        
