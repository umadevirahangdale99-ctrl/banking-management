import json
import os
import re
from account import SavingAccount
from transaction import Transaction

class Bank:
    FILE_NAME = "data.json"
    COUNTER_FILE = "account_counter.json"

    def __init__(self):
        self.accounts = []
        self.load_accounts()

    def load_accounts(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
            except (json.JSONDecodeError, ValueError):
                data = []

            if not isinstance(data, list):
                data = []

            for item in data:
                account = SavingAccount(
                    item.get("account_no", ""),
                    item.get("name", ""),
                    item.get("balance", 100),
                    item.get("photo_path", ""),
                    item.get("pin", None),
                    generate_pin=not bool(item.get("pin")),
                )
                if "transactions" in item:
                    for t in item["transactions"]:
                        if isinstance(t, dict):
                            account.transactions.append(Transaction.from_dict(t))
                        else:
                            account.transactions.append(t)
                self.accounts.append(account)

            self._sync_account_counter()

    def _load_counter(self):
        counter = 0
        if os.path.exists(self.COUNTER_FILE):
            try:
                with open(self.COUNTER_FILE, "r") as file:
                    data = json.load(file)
                    counter = int(data.get("counter", 0))
            except (json.JSONDecodeError, ValueError, TypeError, AttributeError):
                counter = 0
        return counter

    def _save_counter(self, counter):
        with open(self.COUNTER_FILE, "w") as file:
            json.dump({"counter": counter}, file, indent=4)

    def _sync_account_counter(self):
        counter = self._load_counter()
        for account in self.accounts:
            match = re.search(r"(\d+)$", account.account_no or "")
            if match:
                counter = max(counter, int(match.group(1)))
        self._save_counter(counter)

    def get_next_account_no(self):
        counter = self._load_counter() + 1
        self._save_counter(counter)
        return f"AC{str(counter).zfill(6)}"

    def save_accounts(self):

        data = []     
        for account in self.accounts:
            data.append(account.to_dict())  
        with open(self.FILE_NAME,"w") as file:
            json.dump(data, file,indent=4) 

    def create_account(self,account):
        if not getattr(account, "account_no", "").strip():
            account.account_no = self.get_next_account_no()
        else:
            existing = self.find_account(account.account_no)
            if existing:
                raise ValueError("Account number already exists")
        self.accounts.append(account)
        self.save_accounts()

    def create_account_auto(self, name, balance=0, photo_path="", account_no=None):
        if not account_no:
            account_no = self.get_next_account_no()
        account = SavingAccount(account_no, name, balance, photo_path, generate_pin=True)
        self.accounts.append(account)
        self.save_accounts()
        return account

    def find_account(self,account_no):
        account_no = str(account_no).strip()
        for account in self.accounts:
            if str(account.account_no).strip() == account_no:
                return account
        return None                        

    def transfer(self, from_account_no, to_account_no, amount):
        """Transfer amount from one account to another.

        Returns True on success, False if any check fails.
        """
        if amount <= 0:
            return False

        from_acc = self.find_account(from_account_no)
        to_acc = self.find_account(to_account_no)

        if not from_acc or not to_acc:
            return False

        if from_acc.get_balance() < amount:
            return False

        # perform transfer
        from_acc.balance -= amount
        from_acc.transactions.append(Transaction("Transfer Out", amount))

        to_acc.balance += amount
        to_acc.transactions.append(Transaction("Transfer In", amount))

        self.save_accounts()
        return True

    def delete_account(self, account_no):
        """Delete an account by account number. Returns True if deleted."""
        acc = self.find_account(account_no)
        if not acc:
            return False
        try:
            self.accounts.remove(acc)
            self.save_accounts()
            return True
        except ValueError:
            return False
                        
