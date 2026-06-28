import json
import os
from datetime import datetime
from transaction import Transaction


class Loan:
    """Loan class for managing customer loans"""
    
    def __init__(self, loan_id, account_no, customer_name, principal, rate, tenure_months, status="Active"):
        self.loan_id = loan_id
        self.account_no = account_no
        self.customer_name = customer_name
        self.principal = principal  # Original loan amount
        self.rate = rate  # Interest rate per annum
        self.tenure_months = tenure_months
        self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status = status  # Active, Closed, Pending
        self.outstanding_amount = principal
        self.monthly_emi = self.calculate_emi()
        self.paid_amount = 0
        self.payments = []  # List of payment records

    def calculate_emi(self):
        """Calculate monthly EMI using formula: EMI = P(r/12)(1+r/12)^n / ((1+r/12)^n - 1)"""
        if self.tenure_months == 0:
            return 0
        
        monthly_rate = self.rate / 12 / 100
        if monthly_rate == 0:
            return self.principal / self.tenure_months
        
        numerator = self.principal * monthly_rate * ((1 + monthly_rate) ** self.tenure_months)
        denominator = ((1 + monthly_rate) ** self.tenure_months) - 1
        return numerator / denominator

    def make_payment(self, amount):
        """Record a loan payment"""
        if amount <= 0:
            return False
        
        if amount > self.outstanding_amount:
            return False
        
        self.outstanding_amount -= amount
        self.paid_amount += amount
        
        payment_record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "outstanding": self.outstanding_amount
        }
        self.payments.append(payment_record)
        
        if self.outstanding_amount <= 0:
            self.status = "Closed"
        
        return True

    def get_remaining_payments(self):
        """Get number of remaining EMI payments"""
        if self.monthly_emi == 0:
            return 0
        return max(0, int((self.outstanding_amount / self.monthly_emi) + 0.5))

    def get_interest_paid(self):
        """Calculate total interest paid"""
        return self.paid_amount - (self.principal - self.outstanding_amount)

    def get_total_payable(self):
        """Calculate total amount payable across the full tenure."""
        return self.monthly_emi * self.tenure_months

    def get_total_interest(self):
        """Calculate total interest across the full tenure."""
        return self.get_total_payable() - self.principal

    def to_dict(self):
        """Convert loan to dictionary for JSON serialization"""
        return {
            "loan_id": self.loan_id,
            "account_no": self.account_no,
            "customer_name": self.customer_name,
            "principal": self.principal,
            "rate": self.rate,
            "tenure_months": self.tenure_months,
            "created_date": self.created_date,
            "status": self.status,
            "outstanding_amount": self.outstanding_amount,
            "monthly_emi": self.monthly_emi,
            "paid_amount": self.paid_amount,
            "payments": self.payments
        }

    @staticmethod
    def from_dict(data):
        """Create loan object from dictionary"""
        loan = Loan(
            data.get("loan_id", ""),
            data.get("account_no", ""),
            data.get("customer_name", ""),
            data.get("principal", 0),
            data.get("rate", 0),
            data.get("tenure_months", 0),
            data.get("status", "Active")
        )
        loan.outstanding_amount = data.get("outstanding_amount", loan.principal)
        loan.monthly_emi = data.get("monthly_emi", loan.calculate_emi())
        loan.paid_amount = data.get("paid_amount", 0)
        loan.payments = data.get("payments", [])
        loan.created_date = data.get("created_date", loan.created_date)
        return loan


class LoanManager:
    """Manager class for handling all loan operations"""
    
    FILE_NAME = "loans.json"
    COUNTER_FILE = "loan_counter.json"

    def __init__(self):
        self.loans = []
        self.load_loans()

    def load_loans(self):
        """Load all loans from JSON file"""
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        self.loans = [Loan.from_dict(item) for item in data]
            except (json.JSONDecodeError, ValueError):
                self.loans = []
        else:
            self.loans = []

    def save_loans(self):
        """Save all loans to JSON file"""
        data = [loan.to_dict() for loan in self.loans]
        with open(self.FILE_NAME, "w") as file:
            json.dump(data, file, indent=4)

    def get_next_loan_id(self):
        """Generate next loan ID"""
        counter = 0
        if os.path.exists(self.COUNTER_FILE):
            try:
                with open(self.COUNTER_FILE, "r") as file:
                    data = json.load(file)
                    counter = data.get("counter", 0)
            except:
                counter = 0
        
        counter += 1
        with open(self.COUNTER_FILE, "w") as file:
            json.dump({"counter": counter}, file)
        
        return f"LOAN{str(counter).zfill(5)}"

    def create_loan(self, account_no, customer_name, principal, rate, tenure_months):
        """Create a new loan"""
        loan_id = self.get_next_loan_id()
        loan = Loan(loan_id, account_no, customer_name, principal, rate, tenure_months)
        self.loans.append(loan)
        self.save_loans()
        return loan

    def find_loan(self, loan_id):
        """Find loan by ID"""
        for loan in self.loans:
            if loan.loan_id == loan_id:
                return loan
        return None

    def get_loans_by_account(self, account_no):
        """Get all loans for a specific account"""
        return [loan for loan in self.loans if loan.account_no == account_no]

    def get_active_loans(self):
        """Get all active loans"""
        return [loan for loan in self.loans if loan.status == "Active"]

    def make_loan_payment(self, loan_id, amount):
        """Make a payment towards a loan"""
        loan = self.find_loan(loan_id)
        if loan:
            if loan.make_payment(amount):
                self.save_loans()
                return True
        return False

    def close_loan(self, loan_id):
        """Close a loan (mark as paid off)"""
        loan = self.find_loan(loan_id)
        if loan:
            loan.status = "Closed"
            loan.outstanding_amount = 0
            self.save_loans()
            return True
        return False

    def delete_loan(self, loan_id):
        """Delete a loan"""
        self.loans = [loan for loan in self.loans if loan.loan_id != loan_id]
        self.save_loans()

    def get_total_outstanding(self):
        """Get total outstanding loan amount across all active loans"""
        return sum(loan.outstanding_amount for loan in self.loans if loan.status == "Active")


class EMICalculator:
    """Calculate EMI and repayment schedule before creating a loan."""

    @staticmethod
    def calculate_emi(principal, rate, tenure_months):
        if tenure_months <= 0:
            return 0

        monthly_rate = rate / 12 / 100
        if monthly_rate == 0:
            return principal / tenure_months

        numerator = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months)
        denominator = ((1 + monthly_rate) ** tenure_months) - 1
        return numerator / denominator

    @classmethod
    def calculate_summary(cls, principal, rate, tenure_months):
        monthly_emi = cls.calculate_emi(principal, rate, tenure_months)
        total_payable = monthly_emi * tenure_months
        total_interest = total_payable - principal
        return {
            "monthly_emi": monthly_emi,
            "total_payable": total_payable,
            "total_interest": total_interest,
        }

    @classmethod
    def generate_schedule(cls, principal, rate, tenure_months):
        monthly_emi = cls.calculate_emi(principal, rate, tenure_months)
        monthly_rate = rate / 12 / 100
        balance = principal
        schedule = []

        for month in range(1, tenure_months + 1):
            interest = balance * monthly_rate
            principal_paid = monthly_emi - interest

            if month == tenure_months:
                principal_paid = balance
                monthly_payment = principal_paid + interest
                balance = 0
            else:
                monthly_payment = monthly_emi
                balance = max(0, balance - principal_paid)

            schedule.append({
                "Month": month,
                "EMI": monthly_payment,
                "Principal": principal_paid,
                "Interest": interest,
                "Balance": balance,
            })

        return schedule
