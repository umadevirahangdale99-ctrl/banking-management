class Account:
    def __init__(self,account_no,name,balance=0):
        self.account_no = account_no
        self.name = name
        self.balance = balance

    def deposite(self,amount):

        if amount > 0:
            self.balance += amount
            return True
        return False
    
    def withdraw(self,amount):
        if amount <= self.balance:
            self.balance -= amount
            return True
        return False
    
    def get_balance(self):
        return self.balance
    
    def to_dict(self):
        return {
            "account_no":self.account_no,
            "name":self.name,
            "balance":self.balance
        }
class SavingAccount(Account)  :
        def __init__(self, account_no, name, balance=0):
            super().__init__(account_no, name, balance)

class currentAccount(Account):
        def __init__(self, account_no, name, balance=0):
            super().__init__(account_no, name, balance)




        