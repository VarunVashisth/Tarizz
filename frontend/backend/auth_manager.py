"""
auth_manager.py  –  Tarizz Authentication Layer with Multi-Account Support
==========================================================================
Responsibility : Master-password creation (first run), verification on
                 every subsequent launch, session-key lifetime, and
                 brute-force lockout. NOW WITH MULTI-ACCOUNT SUPPORT.

Multi-Account Design
--------------------
Each unique password creates a separate encrypted vault:
  • Different password hash → different data directory
  • Each vault has its own database (projects, nodes, content, media)
  • Account list stored in a central accounts.json file
  • Switching accounts = logout + login with different password

Disk layout – multi-account structure
-------------------------------------
tarizz_data/
  accounts.json          # List of all accounts (metadata only, no passwords)
  vaults/
    vault_<hash>/        # One directory per account
      auth.dat           # Salt + key-hash for this account
      keycheck.dat       # Encrypted sentinel for verification
      tarizz.db          # SQLite database for this account's projects
      media/             # Media files for this account

accounts.json format:
{
  "accounts": [
    {
      "vault_id": "vault_abc123...",
      "created_at": "2026-02-12T10:30:00",
      "last_login": "2026-02-12T14:45:00",
      "display_name": "My Vault"  # Optional, can be set later
    }
  ],
  "last_used": "vault_abc123..."  # Auto-login to this vault
}

Why a separate auth module?
---------------------------
Authentication is a *policy* concern (how many attempts? what hash?).
Encryption is a *mechanism* concern (which algorithm? what parameters?).
Mixing them makes auditing dangerous.  This module calls crypto_engine
for primitives but owns all decisions about *when* and *why* those
primitives are invoked.

Lockout policy
--------------
  MAX_ATTEMPTS  = 5   wrong passwords in a row  →  lock
  LOCKOUT_SECS  = 60  seconds the lock is held

  The counter and lock-timestamp are kept *in memory only*.  A process
  restart resets them.  This is intentional: a desktop app that locks
  the user out of their own machine after a restart is worse than useless.
  The lockout is purely a "slow down a shoulder-surfer" measure.

Microsoft-Store compatibility
-----------------------------
  • No registry writes.
  • Lock state is volatile (RAM only).
  • All file I/O stays inside the app's own data directory.
"""

import os
import time
import hashlib
import json
from datetime import datetime
from pathlib import Path

from backend import crypto_engine as crypto

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------
MAX_ATTEMPTS   = 5      # consecutive failures before lockout
LOCKOUT_SECS   = 60     # seconds

AUTH_FILENAME  = "auth.dat"
KEYCHECK_FILE  = "keycheck.dat"
ACCOUNTS_FILE  = "accounts.json"
SENTINEL       = b"TARIZZ_KEY_OK"   # known-plaintext for key verification


class AuthManager:
    """
    Multi-account authentication manager.

    Attributes (public, read-only after init)
      root_dir      – path to the Tarizz root data directory
      current_vault_dir – path to the currently active vault directory
      session_key   – 32-byte AES key, set after a successful login
      vault_id      – unique identifier for the current vault
    """

    def __init__(self, root_dir: str):
        """
        Inputs
          root_dir – absolute path to the Tarizz root directory
                     (contains accounts.json and vaults/ subdirectory)
        Side-effects
          Creates root_dir and vaults/ subdirectory if they don't exist
          Resets the in-memory attempt counter and lock timestamp
        """
        self.root_dir = Path(root_dir)
        self.vaults_dir = self.root_dir / "vaults"
        
        # Ensure directories exist
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.vaults_dir.mkdir(exist_ok=True)
        
        # Current session state
        self.current_vault_dir = None
        self.session_key = None
        self.vault_id = None
        
        # In-memory lockout state (volatile – resets on restart)
        self._attempts = 0
        self._locked_until = 0.0

    # ------------------------------------------------------------------
    # Multi-Account Management
    # ------------------------------------------------------------------

    def get_accounts_file_path(self) -> Path:
        """Return path to accounts.json"""
        return self.root_dir / ACCOUNTS_FILE

    def load_accounts_metadata(self) -> dict:
        """
        Load accounts metadata from accounts.json.
        Returns empty structure if file doesn't exist.
        """
        accounts_path = self.get_accounts_file_path()
        if not accounts_path.exists():
            return {"accounts": [], "last_used": None}
        
        try:
            with open(accounts_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"accounts": [], "last_used": None}

    def save_accounts_metadata(self, metadata: dict):
        """Save accounts metadata to accounts.json"""
        accounts_path = self.get_accounts_file_path()
        with open(accounts_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def generate_vault_id(self, password: str) -> str:
        """
        Generate a deterministic vault ID from password.
        Same password always generates same vault ID.
        This allows us to find the correct vault directory.
        """
        # Use a quick hash to generate vault ID (not for security, just naming)
        vault_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()[:16]
        return f"vault_{vault_hash}"

    def get_vault_dir(self, vault_id: str) -> Path:
        """Get the directory path for a specific vault"""
        return self.vaults_dir / vault_id

    def vault_exists(self, vault_id: str) -> bool:
        """Check if a vault exists"""
        vault_dir = self.get_vault_dir(vault_id)
        auth_file = vault_dir / AUTH_FILENAME
        return auth_file.exists()

    def create_vault(self, vault_id: str):
        """Create a new vault directory structure"""
        vault_dir = self.get_vault_dir(vault_id)
        vault_dir.mkdir(parents=True, exist_ok=True)
        
        # Create media subdirectory for this vault
        (vault_dir / "media").mkdir(exist_ok=True)

    def register_account(self, vault_id: str, display_name: str = None):
        """
        Register a new account in accounts.json
        """
        metadata = self.load_accounts_metadata()
        
        # Check if account already exists
        for acc in metadata["accounts"]:
            if acc["vault_id"] == vault_id:
                # Update last login
                acc["last_login"] = datetime.now().isoformat()
                self.save_accounts_metadata(metadata)
                return
        
        # Add new account
        account = {
            "vault_id": vault_id,
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "display_name": display_name or "My Vault"
        }
        metadata["accounts"].append(account)
        metadata["last_used"] = vault_id
        
        self.save_accounts_metadata(metadata)

    def update_last_login(self, vault_id: str):
        """Update the last login time for a vault"""
        metadata = self.load_accounts_metadata()
        
        for acc in metadata["accounts"]:
            if acc["vault_id"] == vault_id:
                acc["last_login"] = datetime.now().isoformat()
                break
        
        metadata["last_used"] = vault_id
        self.save_accounts_metadata(metadata)

    def list_accounts(self) -> list:
        """
        Return list of all registered accounts
        Returns: list of dicts with vault_id, created_at, last_login, display_name
        """
        metadata = self.load_accounts_metadata()
        return metadata.get("accounts", [])

    def get_last_used_vault(self) -> str:
        """Get the vault ID that was last used (for auto-login convenience)"""
        metadata = self.load_accounts_metadata()
        return metadata.get("last_used")

    # ------------------------------------------------------------------
    # Public API  (called by the bootstrap / auth-UI layer)
    # ------------------------------------------------------------------

    def is_first_run(self) -> bool:
        """
        Returns True when no accounts exist at all.
        The UI uses this to decide whether to show "Create Password" or "Login".

        Inputs  : None
        Output  : bool
        Side-effects: None
        """
        metadata = self.load_accounts_metadata()
        return len(metadata.get("accounts", [])) == 0

    def has_vault_for_password(self, password: str) -> bool:
        """
        Check if a vault exists for the given password.
        Used to determine if this is a new account or existing account.
        """
        vault_id = self.generate_vault_id(password)
        return self.vault_exists(vault_id)

    def create_password(self, password: str, display_name: str = None) -> None:
        """
        Create a new account with a new vault.
        Derives the session key, persists the auth artefacts, and activates the session.

        Inputs
          password – the master password chosen by the user
          display_name – optional friendly name for this account
        Output  : None  (success implied; IOError propagates on failure).
        Side-effects
          • Creates new vault directory
          • Writes auth.dat (salt + key-hash)
          • Writes keycheck.dat (encrypted sentinel)
          • Registers account in accounts.json
          • Sets self.session_key and self.current_vault_dir
        """
        # Generate vault ID from password
        vault_id = self.generate_vault_id(password)
        
        # Check if vault already exists
        if self.vault_exists(vault_id):
            raise ValueError("An account with this password already exists. Please login instead.")
        
        # Create vault structure
        self.create_vault(vault_id)
        vault_dir = self.get_vault_dir(vault_id)
        
        # Generate crypto materials
        salt = crypto.generate_salt()
        key = crypto.derive_key(password, salt)

        # 1) Persist the salt + SHA-256(key) – never the key itself
        key_hash = hashlib.sha256(key).digest()
        auth_path = vault_dir / AUTH_FILENAME
        with open(auth_path, "wb") as fh:
            fh.write(salt + key_hash)  # 16 + 32 = 48 bytes, fixed

        # 2) Persist an encrypted sentinel (for login verification)
        keycheck_blob = crypto.encrypt(SENTINEL, key)
        keycheck_path = vault_dir / KEYCHECK_FILE
        with open(keycheck_path, "wb") as fh:
            fh.write(keycheck_blob)

        # 3) Register account in metadata
        self.register_account(vault_id, display_name)

        # 4) Activate session
        self.vault_id = vault_id
        self.current_vault_dir = str(vault_dir)
        self.session_key = key
        self._reset_lockout()

    def login(self, password: str) -> bool:
        """
        Verify the password and activate the session for the corresponding vault.

        Inputs
          password – the password entered by the user
        Output
          True   – password correct; session_key is now set
          False  – wrong password OR locked out OR no vault exists
        Side-effects
          • On failure: increments attempt counter; may set lockout
          • On success: sets session_key, current_vault_dir, vault_id, resets counter
        """
        # --- lockout check (fast, no crypto) ---
        if self._is_locked():
            return False

        # --- check if vault exists for this password ---
        vault_id = self.generate_vault_id(password)
        if not self.vault_exists(vault_id):
            self._record_failure()
            return False

        vault_dir = self.get_vault_dir(vault_id)

        # --- derive the candidate key ---
        salt, stored_key_hash = self._read_auth_file(vault_dir)
        candidate_key = crypto.derive_key(password, salt)

        # --- fast check: SHA-256(candidate_key) == stored hash? ---
        if hashlib.sha256(candidate_key).digest() != stored_key_hash:
            self._record_failure()
            return False

        # --- slow check: decrypt the sentinel blob ---
        keycheck_path = vault_dir / KEYCHECK_FILE
        with open(keycheck_path, "rb") as fh:
            blob = fh.read()
        try:
            plaintext = crypto.decrypt(blob, candidate_key)
        except Exception:
            self._record_failure()
            return False

        if plaintext != SENTINEL:
            self._record_failure()
            return False

        # --- success ---
        self.vault_id = vault_id
        self.current_vault_dir = str(vault_dir)
        self.session_key = candidate_key
        self._reset_lockout()
        
        # Update last login time
        self.update_last_login(vault_id)
        
        return True

    def logout(self):
        """
        Clear the current session (for account switching).
        """
        self.session_key = None
        self.current_vault_dir = None
        self.vault_id = None
        self._reset_lockout()

    def get_database_path(self) -> str:
        """
        Get the database path for the current vault.
        This is where the SQLite database should be created/loaded.
        
        Returns: absolute path to tarizz.db in the current vault directory
        Raises: RuntimeError if no vault is currently active
        """
        if not self.current_vault_dir:
            raise RuntimeError("No active vault. Please login first.")
        
        return os.path.join(self.current_vault_dir, "tarizz.db")

    def get_media_directory(self) -> str:
        """
        Get the media directory for the current vault.
        
        Returns: absolute path to media/ in the current vault directory
        Raises: RuntimeError if no active vault is currently active
        """
        if not self.current_vault_dir:
            raise RuntimeError("No active vault. Please login first.")
        
        media_dir = os.path.join(self.current_vault_dir, "media")
        os.makedirs(media_dir, exist_ok=True)
        return media_dir

    def is_locked(self) -> bool:
        """Public accessor for the UI to show a lockout message."""
        return self._is_locked()

    def lockout_remaining_seconds(self) -> float:
        """How many seconds until the lock lifts. 0 if not locked."""
        remaining = self._locked_until - time.time()
        return max(0.0, remaining)

    # ------------------------------------------------------------------
    # Static helper  (UI can call before create_password)
    # ------------------------------------------------------------------
    @staticmethod
    def validate_password_strength(password: str) -> tuple:
        """
        Basic strength check.  Returns (is_ok: bool, reason: str).

        Rules (deliberately simple – this is a local vault, not a web
        service; the main risk is the user forgetting, not an attacker
        cracking online):
          • At least 8 characters
          • Contains at least one digit
          • Contains at least one uppercase letter
          • Contains at least one lowercase letter

        Inputs  : password string
        Output  : (True, "") or (False, human-readable reason)
        Side-effects: None
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit."
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter."
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter."
        return True, ""
    

    def get_session_key(self) -> bytes:
        if not self.session_key:
            raise RuntimeError("No active session. Please login first.")
        return self.session_key

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _read_auth_file(self, vault_dir: Path) -> tuple:
        """
        Parse auth.dat → (salt: 16 bytes, key_hash: 32 bytes).
        Raises FileNotFoundError if auth.dat is missing.
        """
        auth_path = vault_dir / AUTH_FILENAME
        with open(auth_path, "rb") as fh:
            raw = fh.read()
        salt = raw[:16]
        key_hash = raw[16:48]
        return salt, key_hash

    def _is_locked(self) -> bool:
        if time.time() < self._locked_until:
            return True
        # Lock has expired; reset counter so the next failure starts fresh
        if self._attempts >= MAX_ATTEMPTS:
            self._attempts = 0
        return False

    def _record_failure(self) -> None:
        self._attempts += 1
        if self._attempts >= MAX_ATTEMPTS:
            self._locked_until = time.time() + LOCKOUT_SECS

    def _reset_lockout(self) -> None:
        self._attempts = 0
        self._locked_until = 0.0