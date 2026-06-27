import json
import os
from datetime import datetime


class CreditCard:
    """Credit card account linked to a bank account."""

    def __init__(
        self,
        card_no,
        account_no,
        holder_name,
        credit_limit,
        status="Active",
        outstanding_amount=0,
        transactions=None,
        created_date=None,
    ):
        self.card_no = card_no
        self.account_no = account_no
        self.holder_name = holder_name
        self.credit_limit = credit_limit
        self.status = status
        self.outstanding_amount = outstanding_amount
        self.transactions = transactions or []
        self.created_date = created_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def available_limit(self):
        return self.credit_limit - self.outstanding_amount

    def minimum_due(self):
        if self.outstanding_amount <= 0:
            return 0
        return max(100, self.outstanding_amount * 0.05)

    def make_purchase(self, amount, merchant):
        if amount <= 0 or self.status != "Active":
            return False
        if amount > self.available_limit():
            return False

        self.outstanding_amount += amount
        self.transactions.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Purchase",
            "merchant": merchant or "Card Purchase",
            "amount": amount,
            "outstanding": self.outstanding_amount,
        })
        return True

    def make_payment(self, amount):
        if amount <= 0 or amount > self.outstanding_amount:
            return False

        self.outstanding_amount -= amount
        self.transactions.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "Payment",
            "merchant": "Credit Card Payment",
            "amount": amount,
            "outstanding": self.outstanding_amount,
        })
        return True

    def to_dict(self):
        return {
            "card_no": self.card_no,
            "account_no": self.account_no,
            "holder_name": self.holder_name,
            "credit_limit": self.credit_limit,
            "status": self.status,
            "outstanding_amount": self.outstanding_amount,
            "transactions": self.transactions,
            "created_date": self.created_date,
        }

    @staticmethod
    def from_dict(data):
        return CreditCard(
            data.get("card_no", ""),
            data.get("account_no", ""),
            data.get("holder_name", ""),
            data.get("credit_limit", 0),
            data.get("status", "Active"),
            data.get("outstanding_amount", 0),
            data.get("transactions", []),
            data.get("created_date"),
        )


class CreditCardManager:
    """Manage credit card records and transactions."""

    FILE_NAME = "credit_cards.json"
    COUNTER_FILE = "credit_card_counter.json"

    def __init__(self):
        self.cards = []
        self.load_cards()

    def load_cards(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                self.cards = [CreditCard.from_dict(item) for item in data if isinstance(item, dict)]
            except (json.JSONDecodeError, ValueError):
                self.cards = []
        else:
            self.cards = []

    def save_cards(self):
        with open(self.FILE_NAME, "w") as file:
            json.dump([card.to_dict() for card in self.cards], file, indent=4)

    def get_next_card_no(self):
        counter = 0
        if os.path.exists(self.COUNTER_FILE):
            try:
                with open(self.COUNTER_FILE, "r") as file:
                    counter = json.load(file).get("counter", 0)
            except (json.JSONDecodeError, ValueError):
                counter = 0

        counter += 1
        with open(self.COUNTER_FILE, "w") as file:
            json.dump({"counter": counter}, file)

        return f"CC{str(counter).zfill(6)}"

    def create_card(self, account_no, holder_name, credit_limit):
        card = CreditCard(self.get_next_card_no(), account_no, holder_name, credit_limit)
        self.cards.append(card)
        self.save_cards()
        return card

    def find_card(self, card_no):
        for card in self.cards:
            if card.card_no == card_no:
                return card
        return None

    def get_cards_by_account(self, account_no):
        return [card for card in self.cards if card.account_no == account_no]

    def make_purchase(self, card_no, amount, merchant):
        card = self.find_card(card_no)
        if card and card.make_purchase(amount, merchant):
            self.save_cards()
            return card
        return None

    def make_payment(self, card_no, amount):
        card = self.find_card(card_no)
        if card and card.make_payment(amount):
            self.save_cards()
            return card
        return None

    def update_status(self, card_no, status):
        card = self.find_card(card_no)
        if not card:
            return None
        card.status = status
        self.save_cards()
        return card
