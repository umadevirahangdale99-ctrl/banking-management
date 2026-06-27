class DepositManager:
    """Handle deposit transactions for bank accounts."""

    def __init__(self, bank):
        self.bank = bank

    def deposit(self, account_no, amount):
        """Deposit amount into an account and return the updated account."""
        if not account_no or amount <= 0:
            return None

        account = self.bank.find_account(account_no)
        if not account:
            return None

        if account.deposit(amount):
            self.bank.save_accounts()
            return account
        return None
