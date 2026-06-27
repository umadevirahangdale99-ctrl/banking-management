import json
import os
from datetime import datetime

from auth import Auth


class AdminPanelManager:
    """Manage admin dashboard data, branches, rates, and system settings."""

    FILE_NAME = "admin_panel.json"

    DEFAULT_DATA = {
        "branches": [
            {
                "branch_id": "BR001",
                "name": "Head Office",
                "city": "Main City",
                "state": "State",
                "manager": "Admin",
                "status": "Active",
            }
        ],
        "interest_rates": {
            "savings": 3.5,
            "loan": 11.5,
            "fd": 7.0,
            "rd": 6.5,
            "credit_card": 24.0,
        },
        "system_config": {
            "bank_name": "Banking Management System",
            "support_email": "support@bank.local",
            "maintenance_mode": False,
            "currency_symbol": "$",
        },
        "updated_at": None,
    }

    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, "r") as file:
                    data = json.load(file)
                if not isinstance(data, dict):
                    data = {}
            except (json.JSONDecodeError, ValueError):
                data = {}
        else:
            data = {}

        self.data = self._merge_defaults(data)
        return self.data

    def save(self):
        self.data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.FILE_NAME, "w") as file:
            json.dump(self.data, file, indent=4)

    def _merge_defaults(self, data):
        merged = json.loads(json.dumps(self.DEFAULT_DATA))
        merged.update({k: v for k, v in data.items() if k in merged})

        if not isinstance(merged.get("branches"), list):
            merged["branches"] = json.loads(json.dumps(self.DEFAULT_DATA["branches"]))
        if not isinstance(merged.get("interest_rates"), dict):
            merged["interest_rates"] = json.loads(json.dumps(self.DEFAULT_DATA["interest_rates"]))
        if not isinstance(merged.get("system_config"), dict):
            merged["system_config"] = json.loads(json.dumps(self.DEFAULT_DATA["system_config"]))
        if "updated_at" not in merged:
            merged["updated_at"] = None

        return merged

    def get_dashboard_metrics(self, bank, loan_manager, fd_manager, rd_manager, credit_card_manager):
        self.load()
        users = Auth.get_users()
        active_users = [user for user in users if user.get("username")]

        branches = self.data.get("branches", [])
        interest_rates = self.data.get("interest_rates", {})
        system_config = self.data.get("system_config", {})

        return {
            "total_users": len(active_users),
            "total_accounts": len(bank.accounts),
            "total_loans": len(loan_manager.loans),
            "total_fds": len(fd_manager.fixed_deposits),
            "total_rds": len(rd_manager.recurring_deposits),
            "total_cards": len(credit_card_manager.cards),
            "branches": len(branches),
            "active_branches": len([b for b in branches if b.get("status") == "Active"]),
            "interest_rates": interest_rates,
            "system_config": system_config,
        }

    def get_users(self):
        return Auth.get_users()

    def create_user(self, username, full_name, password):
        username = str(username).strip()
        full_name = str(full_name).strip()
        password = str(password).strip()
        if not username or not password:
            return False

        if Auth.user_exists(username):
            return False

        users = Auth.get_users()
        users.append(
            {
                "username": username,
                "password": password,
                "full_name": full_name,
            }
        )
        with open(Auth.FILE_NAME, "w") as file:
            json.dump(users, file, indent=4)
        return True

    def update_user_password(self, username, new_password):
        username = str(username).strip()
        new_password = str(new_password).strip()
        if not username or not new_password:
            return False

        users = Auth.get_users()
        for user in users:
            if user.get("username", "").lower() == username.lower():
                user["password"] = new_password
                with open(Auth.FILE_NAME, "w") as file:
                    json.dump(users, file, indent=4)
                return True
        return False

    def delete_user(self, username):
        username = str(username).strip()
        if not username:
            return False
        users = Auth.get_users()
        updated = [user for user in users if user.get("username", "").lower() != username.lower()]
        if len(updated) == len(users):
            return False
        with open(Auth.FILE_NAME, "w") as file:
            json.dump(updated, file, indent=4)
        return True

    def add_branch(self, name, city, state, manager, status="Active"):
        name = str(name).strip()
        city = str(city).strip()
        state = str(state).strip()
        manager = str(manager).strip()
        status = str(status).strip() or "Active"
        if not name or not city or not state:
            return False

        branches = self.data.get("branches", [])
        branch_id = f"BR{str(len(branches) + 1).zfill(3)}"
        branches.append(
            {
                "branch_id": branch_id,
                "name": name,
                "city": city,
                "state": state,
                "manager": manager,
                "status": status,
            }
        )
        self.data["branches"] = branches
        self.save()
        return True

    def update_branch(self, branch_id, name, city, state, manager, status):
        branch_id = str(branch_id).strip()
        for branch in self.data.get("branches", []):
            if str(branch.get("branch_id", "")).strip() == branch_id:
                branch["name"] = str(name).strip()
                branch["city"] = str(city).strip()
                branch["state"] = str(state).strip()
                branch["manager"] = str(manager).strip()
                branch["status"] = str(status).strip() or "Active"
                self.save()
                return True
        return False

    def delete_branch(self, branch_id):
        branch_id = str(branch_id).strip()
        branches = self.data.get("branches", [])
        updated = [branch for branch in branches if str(branch.get("branch_id", "")).strip() != branch_id]
        if len(updated) == len(branches):
            return False
        self.data["branches"] = updated
        self.save()
        return True

    def update_interest_rates(self, savings, loan, fd, rd, credit_card):
        try:
            self.data["interest_rates"] = {
                "savings": float(savings),
                "loan": float(loan),
                "fd": float(fd),
                "rd": float(rd),
                "credit_card": float(credit_card),
            }
            self.save()
            return True
        except (TypeError, ValueError):
            return False

    def update_system_config(self, bank_name, support_email, maintenance_mode, currency_symbol):
        self.data["system_config"] = {
            "bank_name": str(bank_name).strip(),
            "support_email": str(support_email).strip(),
            "maintenance_mode": bool(maintenance_mode),
            "currency_symbol": str(currency_symbol).strip() or "$",
        }
        self.save()
        return True
