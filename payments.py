from urllib.parse import quote_plus

from transaction import Transaction


class PaymentManager:
    """Handle QR code, UPI, bill, and recharge payments."""

    def __init__(self, bank):
        self.bank = bank

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip()

    def _get_account(self, account_no):
        account_no = self._clean(account_no)
        if not account_no:
            return None
        return self.bank.find_account(account_no)

    def _apply_payment(self, account_no, amount, transaction_type, details=None):
        account = self._get_account(account_no)
        if not account or amount <= 0:
            return None
        if account.get_balance() < amount:
            return None

        account.balance -= amount
        account.transactions.append(Transaction(transaction_type, amount, details=details or {}))
        self.bank.save_accounts()
        return account

    def build_upi_uri(self, payee_upi, payee_name, amount, note=""):
        payee_upi = self._clean(payee_upi)
        payee_name = self._clean(payee_name)
        note = self._clean(note)
        amount = float(amount)

        params = [
            f"pa={quote_plus(payee_upi)}",
            f"pn={quote_plus(payee_name)}",
            f"am={amount:.2f}",
            "cu=INR",
        ]
        if note:
            params.append(f"tn={quote_plus(note)}")

        return f"upi://pay?{'&'.join(params)}"

    def build_qr_payload(self, merchant_name, upi_id, amount, note=""):
        return self.build_upi_uri(upi_id, merchant_name, amount, note)

    def pay_via_qr(self, account_no, merchant_name, upi_id, amount, note=""):
        details = {
            "merchant_name": self._clean(merchant_name),
            "upi_id": self._clean(upi_id),
            "note": self._clean(note),
            "mode": "QR",
        }
        return self._apply_payment(account_no, amount, "QR Payment", details)

    def pay_via_upi(self, account_no, payee_upi, amount, note=""):
        details = {
            "payee_upi": self._clean(payee_upi),
            "note": self._clean(note),
            "mode": "UPI",
        }
        return self._apply_payment(account_no, amount, "UPI Payment", details)

    def pay_bill(self, account_no, biller_name, consumer_number, amount, bill_type="Bill"):
        details = {
            "biller_name": self._clean(biller_name),
            "consumer_number": self._clean(consumer_number),
            "bill_type": self._clean(bill_type),
        }
        return self._apply_payment(account_no, amount, "Bill Payment", details)

    def recharge(self, account_no, mobile_number, operator, amount):
        details = {
            "mobile_number": self._clean(mobile_number),
            "operator": self._clean(operator),
        }
        return self._apply_payment(account_no, amount, "Recharge", details)
