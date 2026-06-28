import json
import os
from datetime import datetime, date
from calendar import monthrange

from transaction import Transaction


class RecurringDeposit:
    """Recurring deposit record linked to a bank account."""

    def __init__(
        self,
        rd_id,
        account_no,
        holder_name,
        monthly_installment,
        rate,
        tenure_months,
        status="Active",
        start_date=None,
        maturity_date=None,
        installments_paid=0,
        total_deposited=0,
        interest_amount=None,
        maturity_amount=None,
        payment_history=None,
        closed_date=None,
    ):
        self.rd_id = rd_id
        self.account_no = account_no
        self.holder_name = holder_name
        self.monthly_installment = monthly_installment
        self.rate = rate
        self.tenure_months = tenure_months
        self.status = status
        self.start_date = start_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.maturity_date = maturity_date or self.calculate_maturity_date()
        self.installments_paid = installments_paid
        self.total_deposited = total_deposited
        self.interest_amount = interest_amount if interest_amount is not None else self.calculate_interest()
        expected_principal = self.monthly_installment * self.tenure_months
        self.maturity_amount = maturity_amount if maturity_amount is not None else expected_principal + self.interest_amount
        self.payment_history = payment_history or []
        self.closed_date = closed_date

    def calculate_interest(self):
        """Approximate RD interest using the standard simple-interest style method."""
        n = int(self.tenure_months)
        return (self.monthly_installment * n * (n + 1) * self.rate) / (2 * 12 * 100)

    def calculate_maturity_date(self):
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
        return self.installments_paid >= self.tenure_months

    def record_installment(self, amount):
        if self.status != "Active":
            return False
        if amount <= 0:
            return False
        if amount != self.monthly_installment:
            return False
        if self.installments_paid >= self.tenure_months:
            return False

        self.installments_paid += 1
        self.total_deposited += amount
        self.payment_history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "installment_no": self.installments_paid,
        })
        return True

    def refresh_summary(self):
        self.interest_amount = self.calculate_interest()
        self.maturity_amount = (self.monthly_installment * self.tenure_months) + self.interest_amount

    def to_dict(self):
        self.refresh_summary()
        return {
            "rd_id": self.rd_id,
            "account_no": self.account_no,
            "holder_name": self.holder_name,
            "monthly_installment": self.monthly_installment,
            "rate": self.rate,
            "tenure_months": self.tenure_months,
            "status": self.status,
            "start_date": self.start_date,
            "maturity_date": self.maturity_date,
            "installments_paid": self.installments_paid,
            "total_deposited": self.total_deposited,
            "interest_amount": self.interest_amount,
            "maturity_amount": self.maturity_amount,
            "payment_history": self.payment_history,
            "closed_date": self.closed_date,
        }

    @staticmethod
    def from_dict(data):
        return RecurringDeposit(
            data.get("rd_id", ""),
            data.get("account_no", ""),
            data.get("holder_name", ""),
            data.get("monthly_installment", 0),
            data.get("rate", 0),
            data.get("tenure_months", 0),
            data.get("status", "Active"),
            data.get("start_date"),
            data.get("maturity_date"),
            data.get("installments_paid", 0),
            data.get("total_deposited", 0),
            data.get("interest_amount"),
            data.get("maturity_amount"),
            data.get("payment_history", []),
            data.get("closed_date"),
        )


class RecurringDepositManager:
    """Manage recurring deposits and installments."""

    FILE_NAME = "recurring_deposits.json"
    COUNTER_FILE = "rd_counter.json"

    def __init__(self, bank):
        self.bank = bank
        self.recurring_deposits = []
        self.load_rds()

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip()

    def load_rds(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                if isinstance(data, list):
                    self.recurring_deposits = [RecurringDeposit.from_dict(item) for item in data if isinstance(item, dict)]
            except (json.JSONDecodeError, ValueError):
                self.recurring_deposits = []
        else:
            self.recurring_deposits = []

    def save_rds(self):
        with open(self.FILE_NAME, "w") as file:
            json.dump([rd.to_dict() for rd in self.recurring_deposits], file, indent=4)

    def get_next_rd_id(self):
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
        return f"RD{str(counter).zfill(6)}"

    def find_rd(self, rd_id):
        rd_id = self._clean(rd_id)
        for rd in self.recurring_deposits:
            if self._clean(rd.rd_id) == rd_id:
                return rd
        return None

    def get_rds_by_account(self, account_no):
        account_no = self._clean(account_no)
        return [rd for rd in self.recurring_deposits if self._clean(rd.account_no) == account_no]

    def open_rd(self, account_no, holder_name, monthly_installment, rate, tenure_months):
        account_no = self._clean(account_no)
        holder_name = self._clean(holder_name)

        if not account_no or not holder_name:
            return None
        if monthly_installment <= 0 or rate < 0 or tenure_months <= 0:
            return None

        account = self.bank.find_account(account_no)
        if not account:
            return None

        rd = RecurringDeposit(
            self.get_next_rd_id(),
            account_no,
            holder_name,
            monthly_installment,
            rate,
            tenure_months,
        )
        self.recurring_deposits.append(rd)
        self.save_rds()
        return rd

    def pay_installment(self, rd_id):
        rd = self.find_rd(rd_id)
        if not rd or rd.status != "Active":
            return None
        if rd.installments_paid >= rd.tenure_months:
            return None

        account = self.bank.find_account(rd.account_no)
        if not account or account.get_balance() < rd.monthly_installment:
            return None

        if not rd.record_installment(rd.monthly_installment):
            return None

        account.balance -= rd.monthly_installment
        account.transactions.append(Transaction("RD Installment", rd.monthly_installment))

        rd.refresh_summary()
        self.bank.save_accounts()
        self.save_rds()
        return rd

    def close_rd(self, rd_id):
        rd = self.find_rd(rd_id)
        if not rd or rd.status != "Active":
            return None
        if rd.installments_paid < rd.tenure_months:
            return None

        account = self.bank.find_account(rd.account_no)
        if not account:
            return None

        rd.refresh_summary()
        payout = rd.maturity_amount
        account.balance += payout
        account.transactions.append(Transaction("RD Matured", payout))

        rd.status = "Closed"
        rd.closed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.bank.save_accounts()
        self.save_rds()
        return rd
