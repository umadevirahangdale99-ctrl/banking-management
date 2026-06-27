import json
import os
from typing import Any


class Auth:
    FILE_NAME = "users.json"

    @classmethod
    def _ensure_file(cls) -> None:
        if not os.path.exists(cls.FILE_NAME):
            with open(cls.FILE_NAME, "w") as file:
                json.dump([], file, indent=4)

    @classmethod
    def _load_users(cls) -> list[dict[str, Any]]:
        cls._ensure_file()
        with open(cls.FILE_NAME, "r") as file:
            try:
                users = json.load(file)
            except json.JSONDecodeError:
                users = []

        if not isinstance(users, list):
            users = []

        return users

    @classmethod
    def _save_users(cls, users: list[dict[str, Any]]) -> None:
        with open(cls.FILE_NAME, "w") as file:
            json.dump(users, file, indent=4)

    @classmethod
    def get_user(cls, username: str) -> dict[str, Any] | None:
        username = username.strip()
        for user in cls._load_users():
            if user.get("username", "").lower() == username.lower():
                return user
        return None

    @classmethod
    def reset_password(cls, username: str, full_name: str, new_password: str) -> bool:
        username = username.strip()
        full_name = full_name.strip()
        new_password = new_password.strip()
        if not username or not full_name or not new_password:
            return False

        users = cls._load_users()
        for user in users:
            if (
                user.get("username", "").lower() == username.lower()
                and user.get("full_name", "").strip().lower() == full_name.lower()
            ):
                user["password"] = new_password
                cls._save_users(users)
                return True
        return False

    @classmethod
    def change_password(cls, username: str, current_password: str, new_password: str) -> bool:
        username = username.strip()
        current_password = current_password.strip()
        new_password = new_password.strip()
        if not username or not current_password or not new_password:
            return False

        users = cls._load_users()
        for user in users:
            if (
                user.get("username", "").lower() == username.lower()
                and user.get("password", "") == current_password
            ):
                user["password"] = new_password
                cls._save_users(users)
                return True
        return False

    @classmethod
    def login(cls, username: str, password: str) -> bool:
        username = username.strip()
        password = password.strip()
        users = cls._load_users()
        for user in users:
            if user.get("username", "").lower() == username.lower() and user.get("password", "") == password:
                return True
        return False

    @classmethod
    def register(cls, username: str, password: str, full_name: str = "") -> bool:
        username = username.strip()
        password = password.strip()
        full_name = full_name.strip()
        if not username or not password:
            return False
        users = cls._load_users()
        if any(user.get("username", "").lower() == username.lower() for user in users):
            return False

        users.append({
            "username": username,
            "password": password,
            "full_name": full_name,
        })
        cls._save_users(users)
        return True

    @classmethod
    def user_exists(cls, username: str) -> bool:
        username = username.strip()
        return any(user.get("username", "").lower() == username.lower() for user in cls._load_users())

    @classmethod
    def get_users(cls) -> list[dict[str, Any]]:
        return cls._load_users()
