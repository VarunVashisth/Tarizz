"""
Single-user authentication with password reset.

A random data key encrypts the database. That key is wrapped twice:
with the password and with the security-answer key, so resetting the
password does not destroy stored projects.
"""

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

from backend import crypto_engine as crypto

AUTH_FILENAME = "auth.json"
MAX_ATTEMPTS = 5
LOCKOUT_SECS = 60


class SimpleAuthManager:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "media").mkdir(exist_ok=True)

        self.auth_file = self.data_dir / AUTH_FILENAME
        self.is_authenticated = False
        self.username = None
        self.session_key = None

        self._attempts = 0
        self._locked_until = 0.0

    def is_first_run(self) -> bool:
        return not self.auth_file.exists()

    def create_account(self, username: str, password: str,
                       security_question: str, security_answer: str) -> bool:
        if not self.is_first_run():
            return False

        ok, _ = self.validate_password_strength(password)
        if not ok:
            return False

        salt = crypto.generate_salt()
        answer_salt = crypto.generate_salt()
        pwd_key = crypto.derive_key(password, salt)
        ans_key = crypto.derive_key(security_answer.strip().lower(), answer_salt)
        data_key = os.urandom(32)

        auth_data = {
            "username": username.strip(),
            "salt": salt.hex(),
            "answer_salt": answer_salt.hex(),
            "password_hash": hashlib.sha256(pwd_key).hexdigest(),
            "security_question": security_question.strip(),
            "security_answer_hash": hashlib.sha256(ans_key).hexdigest(),
            "data_key_pwd": crypto.encrypt(data_key, pwd_key).hex(),
            "data_key_ans": crypto.encrypt(data_key, ans_key).hex(),
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
        self._write_auth(auth_data)

        self.is_authenticated = True
        self.username = auth_data["username"]
        self.session_key = data_key
        self._reset_lockout()
        return True

    def login(self, username: str, password: str) -> bool:
        if self._is_locked():
            return False
        if self.is_first_run():
            return False

        auth_data = self._read_auth()
        if auth_data["username"] != username.strip():
            self._record_failure()
            return False

        salt = bytes.fromhex(auth_data["salt"])
        pwd_key = crypto.derive_key(password, salt)
        if hashlib.sha256(pwd_key).hexdigest() != auth_data["password_hash"]:
            self._record_failure()
            return False

        try:
            data_key = crypto.decrypt(bytes.fromhex(auth_data["data_key_pwd"]), pwd_key)
        except Exception:
            self._record_failure()
            return False

        self.is_authenticated = True
        self.username = auth_data["username"]
        self.session_key = data_key
        self._reset_lockout()
        return True

    def reset_password(self, username: str, security_answer: str,
                       new_password: str) -> bool:
        if self.is_first_run():
            return False

        ok, _ = self.validate_password_strength(new_password)
        if not ok:
            return False

        auth_data = self._read_auth()
        if auth_data["username"] != username.strip():
            return False

        answer_salt = bytes.fromhex(auth_data["answer_salt"])
        ans_key = crypto.derive_key(security_answer.strip().lower(), answer_salt)
        if hashlib.sha256(ans_key).hexdigest() != auth_data["security_answer_hash"]:
            return False

        try:
            data_key = crypto.decrypt(bytes.fromhex(auth_data["data_key_ans"]), ans_key)
        except Exception:
            return False

        salt = crypto.generate_salt()
        pwd_key = crypto.derive_key(new_password, salt)
        auth_data["salt"] = salt.hex()
        auth_data["password_hash"] = hashlib.sha256(pwd_key).hexdigest()
        auth_data["data_key_pwd"] = crypto.encrypt(data_key, pwd_key).hex()
        auth_data["last_password_change"] = datetime.now().isoformat()
        self._write_auth(auth_data)

        self.is_authenticated = True
        self.username = auth_data["username"]
        self.session_key = data_key
        self._reset_lockout()
        return True

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.is_authenticated or not self.username:
            return False
        ok, _ = self.validate_password_strength(new_password)
        if not ok:
            return False

        auth_data = self._read_auth()
        salt = bytes.fromhex(auth_data["salt"])
        old_key = crypto.derive_key(old_password, salt)
        if hashlib.sha256(old_key).hexdigest() != auth_data["password_hash"]:
            return False

        new_salt = crypto.generate_salt()
        new_key = crypto.derive_key(new_password, new_salt)
        auth_data["salt"] = new_salt.hex()
        auth_data["password_hash"] = hashlib.sha256(new_key).hexdigest()
        auth_data["data_key_pwd"] = crypto.encrypt(self.session_key, new_key).hex()
        auth_data["last_password_change"] = datetime.now().isoformat()
        self._write_auth(auth_data)
        return True

    def get_security_question(self, username: str):
        if self.is_first_run():
            return None
        auth_data = self._read_auth()
        if auth_data["username"] == username.strip():
            return auth_data["security_question"]
        return None

    def stored_username(self):
        if self.is_first_run():
            return None
        return self._read_auth().get("username")

    def logout(self):
        self.is_authenticated = False
        self.username = None
        self.session_key = None
        self._reset_lockout()

    def get_database_path(self) -> str:
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated — cannot access database")
        return str(self.data_dir / "tarizz.db")

    def get_media_directory(self) -> str:
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated — cannot access media")
        media_dir = self.data_dir / "media"
        media_dir.mkdir(exist_ok=True)
        return str(media_dir)

    def get_session_key(self) -> bytes:
        if not self.session_key:
            raise RuntimeError("No active session. Please login first.")
        return self.session_key

    def is_locked(self) -> bool:
        return self._is_locked()

    def lockout_remaining_seconds(self) -> float:
        return max(0.0, self._locked_until - time.time())

    @staticmethod
    def validate_password_strength(password: str) -> tuple:
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit."
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."
        return True, ""

    def _read_auth(self) -> dict:
        with open(self.auth_file, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write_auth(self, data: dict):
        with open(self.auth_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _is_locked(self) -> bool:
        if time.time() < self._locked_until:
            return True
        if self._attempts >= MAX_ATTEMPTS:
            self._attempts = 0
        return False

    def _record_failure(self):
        self._attempts += 1
        if self._attempts >= MAX_ATTEMPTS:
            self._locked_until = time.time() + LOCKOUT_SECS

    def _reset_lockout(self):
        self._attempts = 0
        self._locked_until = 0.0
