import json
import os
from datetime import datetime


class KYC:
    """KYC (Know Your Customer) verification class"""
    
    def __init__(self, account_no, full_name, email, phone, address, city, state, pincode,
                 id_type, id_number, dob, photo_path="", status="Pending"):
        self.account_no = account_no
        self.full_name = full_name
        self.email = email
        self.phone = phone
        self.address = address
        self.city = city
        self.state = state
        self.pincode = pincode
        self.id_type = id_type  # Aadhar, PAN, Passport, DL
        self.id_number = id_number
        self.dob = dob  # Date of Birth
        self.photo_path = photo_path or ""
        self.status = status  # Pending, Approved, Rejected
        self.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.approved_date = None
        self.rejection_reason = ""

    def approve_kyc(self):
        """Approve KYC"""
        self.status = "Approved"
        self.approved_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return True

    def reject_kyc(self, reason=""):
        """Reject KYC"""
        self.status = "Rejected"
        self.rejection_reason = reason
        return True

    def to_dict(self):
        """Convert KYC to dictionary for JSON serialization"""
        return {
            "account_no": self.account_no,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "pincode": self.pincode,
            "id_type": self.id_type,
            "id_number": self.id_number,
            "dob": self.dob,
            "photo_path": self.photo_path,
            "status": self.status,
            "created_date": self.created_date,
            "approved_date": self.approved_date,
            "rejection_reason": self.rejection_reason
        }

    @staticmethod
    def from_dict(data):
        """Create KYC object from dictionary"""
        kyc = KYC(
            data.get("account_no", ""),
            data.get("full_name", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("address", ""),
            data.get("city", ""),
            data.get("state", ""),
            data.get("pincode", ""),
            data.get("id_type", ""),
            data.get("id_number", ""),
            data.get("dob", ""),
            data.get("photo_path", ""),
            data.get("status", "Pending")
        )
        kyc.created_date = data.get("created_date", kyc.created_date)
        kyc.approved_date = data.get("approved_date")
        kyc.rejection_reason = data.get("rejection_reason", "")
        return kyc


class KYCManager:
    """Manager class for handling all KYC operations"""
    
    FILE_NAME = "kyc_data.json"

    def __init__(self):
        self.kyc_records = []
        self.load_kyc()

    def load_kyc(self):
        """Load all KYC records from JSON file"""
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        self.kyc_records = [KYC.from_dict(item) for item in data]
            except (json.JSONDecodeError, ValueError):
                self.kyc_records = []
        else:
            self.kyc_records = []

    def save_kyc(self):
        """Save all KYC records to JSON file"""
        data = [kyc.to_dict() for kyc in self.kyc_records]
        with open(self.FILE_NAME, "w") as file:
            json.dump(data, file, indent=4)

    @staticmethod
    def _clean(value):
        if value is None:
            return ""
        return str(value).strip()

    def submit_kyc(self, account_no, full_name, email, phone, address, city, state, 
                   pincode, id_type, id_number, dob, photo_path=""):
        """Submit or update KYC for an account"""
        self.load_kyc()
        account_no = self._clean(account_no)
        full_name = self._clean(full_name)
        email = self._clean(email)
        phone = self._clean(phone)
        address = self._clean(address)
        city = self._clean(city)
        state = self._clean(state)
        pincode = self._clean(pincode)
        id_type = self._clean(id_type)
        id_number = self._clean(id_number)
        dob = self._clean(dob)
        photo_path = self._clean(photo_path)

        required_fields = [
            account_no,
            full_name,
            email,
            phone,
            address,
            city,
            state,
            pincode,
            id_type,
            id_number,
            dob,
        ]
        if any(not field for field in required_fields):
            return False

        # Check if KYC already exists
        existing_kyc = self.find_kyc_by_account(account_no)
        
        if existing_kyc:
            # Update existing KYC
            existing_kyc.full_name = full_name
            existing_kyc.email = email
            existing_kyc.phone = phone
            existing_kyc.address = address
            existing_kyc.city = city
            existing_kyc.state = state
            existing_kyc.pincode = pincode
            existing_kyc.id_type = id_type
            existing_kyc.id_number = id_number
            existing_kyc.dob = dob
            if photo_path:
                existing_kyc.photo_path = photo_path
            existing_kyc.status = "Pending"  # Reset to pending after update
            existing_kyc.approved_date = None
            existing_kyc.rejection_reason = ""
        else:
            # Create new KYC
            kyc = KYC(account_no, full_name, email, phone, address, city, state, 
                     pincode, id_type, id_number, dob, photo_path)
            self.kyc_records.append(kyc)
        
        self.save_kyc()
        return True

    def find_kyc_by_account(self, account_no):
        """Find KYC by account number"""
        account_no = str(account_no).strip()
        for kyc in self.kyc_records:
            if str(kyc.account_no).strip() == account_no:
                return kyc
        return None

    def get_pending_kyc(self):
        """Get all pending KYC applications"""
        return [kyc for kyc in self.kyc_records if kyc.status == "Pending"]

    def get_approved_kyc(self):
        """Get all approved KYC records"""
        return [kyc for kyc in self.kyc_records if kyc.status == "Approved"]

    def get_rejected_kyc(self):
        """Get all rejected KYC records"""
        return [kyc for kyc in self.kyc_records if kyc.status == "Rejected"]

    def approve_kyc(self, account_no):
        """Approve KYC for an account"""
        kyc = self.find_kyc_by_account(account_no)
        if kyc:
            kyc.approve_kyc()
            self.save_kyc()
            return True
        return False

    def reject_kyc(self, account_no, reason=""):
        """Reject KYC for an account"""
        kyc = self.find_kyc_by_account(account_no)
        if kyc:
            kyc.reject_kyc(reason)
            self.save_kyc()
            return True
        return False

    def get_kyc_status(self, account_no):
        """Get KYC status for an account"""
        kyc = self.find_kyc_by_account(account_no)
        if kyc:
            return kyc.status
        return "Not Submitted"

    def is_kyc_verified(self, account_no):
        """Check if account has verified KYC"""
        kyc = self.find_kyc_by_account(account_no)
        if kyc and kyc.status == "Approved":
            return True
        return False
