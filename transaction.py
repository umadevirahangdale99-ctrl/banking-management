from datetime import datetime

class Transaction:
    def __init__(self, transaction_type, amount, date=None, details=None):
        self.transaction_type = transaction_type
        self.amount = amount
        self.date = date or datetime.now().strftime("%d-%m-%Y,%H:%M:%S")
        self.details = details or {}

    @classmethod
    def from_dict(cls, transaction_data):
        return cls(
            transaction_data.get("type", "Unknown"),
            transaction_data.get("amount", 0),
            transaction_data.get("date"),
            transaction_data.get("details", {}),
        )

    def to_dict(self):
        return {
            "type": self.transaction_type,
            "amount": self.amount,
            "date": self.date,
            "details": self.details,
        }
        
