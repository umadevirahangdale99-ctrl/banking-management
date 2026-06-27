import json
import os
from datetime import datetime, date
from calendar import monthrange

from transaction import Transaction


class FixedDeposit:
    """Fixed deposit record linked to a bank account."""

    def __init__(
        self,
        fd_id,
        account_no,
        holder_name,
        principal,
        rate,
        tenure_months,
        status="Active",
        start_date=None,
        maturity_date=None,
        maturity_amount=None,
        interest_amount=None,
        closed_date=None,
    ):
        self.fd_id = fd_id
        self.account_no = account_no
        self.holder_name = holder_name
        self.principal = principal
        self.rate = rate
        self.tenure_months = tenure_months
        self.status = status
        self.start_date = start_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.maturity_date = maturity_date or self.calculate_maturity_date()
        self.interest_amount = interest_amount if interest_amount is not None else self.calculate_interest()
        self.maturity_amount = maturity_amount if maturity_amount is not None else self.principal + self.interest_amount
        self.closed_date = closed_date

    def calculate_interest(self):
        """Simple interest for the full FD tenure."""
        return (self.principal * self.rate * self.tenure_months) / (12 * 100)

    def calculate_maturity_date(self):
        """Calculate maturity date by adding tenure months to the start date."""
        try:
            start_dt = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            start_dt = datetime.now()

        month = start_dt.month - 1 + int(self.tenure_months)
        year = start_dt.year + month // 12
        month = month % 12 + 1
        day = min(start_dt.day, monthrange(year, month)[1])
        return date(year, month, day).strftime("%Y-%m-%d")

    def is_matured(self):
        try:
            return datetime.now().date() >= datetime.strptime(self.maturity_date, "%Y-%m-%d").date()
        except ValueError:
            return False

    def to_dict(self):
        return {
            "fd_id": self.fd_id,
            "account_no": self.account_no,
            "holder_name": self.holder_name,
            "principal": self.principal,
            "rate": self.rate,
            "tenure_months": self.tenure_months,
            "status": self.status,
            "start_date": self.start_date,
            "maturity_date": self.maturity_date,
            "maturity_amount": self.maturity_amount,
            "interest_amount": self.interest_amount,
            "closed_date": self.closed_date,
        }

    @staticmethod
    def from_dict(data):
        return FixedDeposit(
            data.get("fd_id", ""),
            data.get("account_no", ""),
            data.get("holder_name", ""),
            data.get("principal", 0),
            data.get("rate", 0),
            data.get("tenure_months", 0),
            data.get("status", "Active"),
            data.get("start_date"),
            data.get("maturity_date"),
            data.get("maturity_amount"),
            data.get("interest_amount"),
            data.get("closed_date"),
        )


class FixedDepositManager:
    """Manage fixed deposit creation, closure and persistence."""

    FILE_NAME = "fixed_deposits.json"
    COUNTER_FILE = "fd_counter.json"

    def __init__(self, bank):
        self.bank = bank
        self.fixed_deposits = []
        self.load_fds()

    def load_fds(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                if isinstance(data, list):
                    self.fixed_deposits = [FixedDeposit.from_dict(item) for item in data if isinstance(item, dict)]
            except (json.JSONDecodeError, ValueError):
                self.fixed_deposits = []
        else:
            self.fixed_deposits = []

    def save_fds(self):
        with open(self.FILE_NAME, "w") as file:
            json.dump([fd.to_dict() for fd in self.fixed_deposits], file, indent=4)

    def get_next_fd_id(self):
        counter = 0
        if os.path.exists(self.COUNTER_FILE):
            try:
                with open(self.COUNTER_FILE, "r") as file:
                    counter = json.load(file).get("counter", 0)
            except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
                counter = 0

        counter += 1
        with open(self.COUNTER_FILE, "w") as file:
            json.dump({"counter": counter}, file, indent=4)
        return f"FD{str(counter).zfill(6)}"

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip()

    def find_fd(self, fd_id):
        fd_id = self._clean(fd_id)
        for fd in self.fixed_deposits:
            if self._clean(fd.fd_id) == fd_id:
                return fd
        return None

    def get_fds_by_account(self, account_no):
        account_no = self._clean(account_no)
        return [fd for fd in self.fixed_deposits if self._clean(fd.account_no) == account_no]

    def get_active_fds(self):
        return [fd for fd in self.fixed_deposits if fd.status == "Active"]

    def open_fd(self, account_no, holder_name, principal, rate, tenure_months):
        account_no = self._clean(account_no)
        holder_name = self._clean(holder_name)

        if not account_no or not holder_name:
            return None
        if principal <= 0 or rate < 0 or tenure_months <= 0:
            return None

        account = self.bank.find_account(account_no)
        if not account or account.get_balance() < principal:
            return None

        account.balance -= principal
        account.transactions.append(Transaction("Fixed Deposit Opened", principal))

        fd = FixedDeposit(
            self.get_next_fd_id(),
            account_no,
            holder_name,
            principal,
            rate,
            tenure_months,
        )
        self.fixed_deposits.append(fd)
        self.bank.save_accounts()
        self.save_fds()
        return fd

    def close_fd(self, fd_id):
        fd = self.find_fd(fd_id)
        if not fd or fd.status != "Active":
            return None

        account = self.bank.find_account(fd.account_no)
        if not account:
            return None

        payout = fd.maturity_amount
        account.balance += payout
        account.transactions.append(Transaction("Fixed Deposit Matured", payout))

        fd.status = "Closed"
        fd.closed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.bank.save_accounts()
        self.save_fds()
        return fd
