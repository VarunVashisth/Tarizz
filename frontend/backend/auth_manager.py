"""
auth_manager.py  —  Tarizz Authentication Layer
=================================================
Responsibility : Master-password creation (first run), verification on
                 every subsequent launch, session-key lifetime, and
                 brute-force lockout.

Why a separate auth module?
---------------------------
Authentication is a *policy* concern (how many attempts? what hash?).
Encryption is a *mechanism* concern (which algorithm? what parameters?).
Mixing them makes auditing dangerous.  This module calls crypto_engine
for primitives but owns all decisions about *when* and *why* those
primitives are invoked.

Disk layout — auth artefacts
-----------------------------
Inside the Tarizz data directory (see storage_manager for the path):

  auth.dat
    [ salt (16 B) ][ scrypt-derived key hash (32 B) ]
    
    The "key hash" is NOT the master password.  It is:
      scrypt(password, salt)  →  32 B key
      then SHA-256(key)       →  32 B hash
    This two-step design means:
      • We never store the derivation key itself (which would unlock
        the vault).
      • SHA-256 of the key is a simple fingerprint; even if auth.dat
        leaks, an attacker only has a *hash* of the key, not the key.

  keycheck.dat  (encrypted with the session key)
    A known plaintext sentinel (the bytes "TARIZZ_KEY_OK").
    On login we decrypt this file; if decryption succeeds (GCM tag
    validates) AND the plaintext matches the sentinel, the password
    is correct.  This gives us *authenticated* verification — the GCM
    tag already catches wrong-key attempts, but the sentinel adds an
    extra, human-auditable layer.

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

from . import crypto_engine as crypto

# ---------------------------------------------------------------------------
# Policy constants
# ---------------------------------------------------------------------------
MAX_ATTEMPTS   = 5      # consecutive failures before lockout
LOCKOUT_SECS   = 60     # seconds

AUTH_FILENAME  = "auth.dat"
KEYCHECK_FILE  = "keycheck.dat"
SENTINEL       = b"TARIZZ_KEY_OK"   # known-plaintext for key verification


class AuthManager:
    """
    Singleton-style manager: one instance lives for the entire app session.

    Attributes (public, read-only after init)
      data_dir      – path to the Tarizz encrypted data directory.
      session_key   – 32-byte AES key, set after a successful login.
                      None before login.
    """

    def __init__(self, data_dir: str):
        """
        Inputs
          data_dir – absolute path to the encrypted storage root (created
                     by StorageManager before AuthManager is instantiated).
        Side-effects
          Resets the in-memory attempt counter and lock timestamp.
        """
        self.data_dir     = data_dir
        self.session_key  = None          # populated on successful login

        # In-memory lockout state  (volatile — resets on restart)
        self._attempts    = 0
        self._locked_until = 0.0          # epoch timestamp

    # ------------------------------------------------------------------
    # Public API  (called by the bootstrap / auth-UI layer)
    # ------------------------------------------------------------------

    def is_first_run(self) -> bool:
        """
        Returns True when no auth.dat exists — i.e., the user has never
        created a master password.  The UI uses this to decide whether to
        show "Create Password" or "Login".

        Inputs  : None
        Output  : bool
        Side-effects: None
        """
        return not os.path.isfile(os.path.join(self.data_dir, AUTH_FILENAME))

    def create_password(self, password: str) -> None:
        """
        First-run setup.  Derives the session key, persists the auth
        artefacts, and activates the session.

        Inputs
          password – the master password chosen by the user (must be
                     validated by the UI before calling — see
                     validate_password_strength).
        Output  : None  (success implied; IOError propagates on failure).
        Side-effects
          • Writes auth.dat  (salt + key-hash).
          • Writes keycheck.dat (encrypted sentinel).
          • Sets self.session_key.
        """
        salt = crypto.generate_salt()
        key  = crypto.derive_key(password, salt)

        # 1) Persist the salt + SHA-256(key) — never the key itself
        key_hash = hashlib.sha256(key).digest()
        auth_path = os.path.join(self.data_dir, AUTH_FILENAME)
        with open(auth_path, "wb") as fh:
            fh.write(salt + key_hash)       # 16 + 32 = 48 bytes, fixed

        # 2) Persist an encrypted sentinel (for login verification)
        keycheck_blob = crypto.encrypt(SENTINEL, key)
        keycheck_path = os.path.join(self.data_dir, KEYCHECK_FILE)
        with open(keycheck_path, "wb") as fh:
            fh.write(keycheck_blob)

        # 3) Activate session
        self.session_key = key
        self._reset_lockout()

    def login(self, password: str) -> bool:
        """
        Verify the password and, on success, activate the session key.

        Inputs
          password – the password entered by the user.
        Output
          True   – password correct; session_key is now set.
          False  – wrong password OR locked out.
        Side-effects
          • On failure: increments attempt counter; may set lockout.
          • On success: sets session_key, resets counter.

        Security notes
          • We do NOT reveal whether the failure was "wrong password" or
            "locked out" — both return False.  The UI may show a generic
            "Invalid password" message.
          • The key-hash check (fast) is done first as an early-exit.
            The sentinel decrypt (slower, authenticated) is the binding
            proof.  Both must pass.
        """
        # --- lockout check (fast, no crypto) ---
        if self._is_locked():
            return False

        # --- derive the candidate key ---
        salt, stored_key_hash = self._read_auth_file()
        candidate_key = crypto.derive_key(password, salt)

        # --- fast check: SHA-256(candidate_key) == stored hash? ---
        if hashlib.sha256(candidate_key).digest() != stored_key_hash:
            self._record_failure()
            return False

        # --- slow check: decrypt the sentinel blob ---
        keycheck_path = os.path.join(self.data_dir, KEYCHECK_FILE)
        with open(keycheck_path, "rb") as fh:
            blob = fh.read()
        try:
            plaintext = crypto.decrypt(blob, candidate_key)
        except Exception:
            # GCM tag failure — key is definitely wrong (shouldn't reach
            # here if the hash matched, but belt-and-suspenders)
            self._record_failure()
            return False

        if plaintext != SENTINEL:
            self._record_failure()
            return False

        # --- success ---
        self.session_key = candidate_key
        self._reset_lockout()
        return True

    def is_locked(self) -> bool:
        """Public accessor for the UI to show a lockout message."""
        return self._is_locked()

    def lockout_remaining_seconds(self) -> float:
        """How many seconds until the lock lifts.  0 if not locked."""
        remaining = self._locked_until - time.time()
        return max(0.0, remaining)

    # ------------------------------------------------------------------
    # Static helper  (UI can call before create_password)
    # ------------------------------------------------------------------
    @staticmethod
    def validate_password_strength(password: str) -> tuple:
        """
        Basic strength check.  Returns (is_ok: bool, reason: str).

        Rules (deliberately simple — this is a local vault, not a web
        service; the main risk is the user forgetting, not an attacker
        cracking online):
          • At least 8 characters.
          • Contains at least one digit.
          • Contains at least one uppercase letter.
          • Contains at least one lowercase letter.

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _read_auth_file(self) -> tuple:
        """
        Parse auth.dat → (salt: 16 bytes, key_hash: 32 bytes).
        Raises FileNotFoundError if auth.dat is missing (shouldn't happen
        after first run, but fails loudly rather than silently).
        """
        auth_path = os.path.join(self.data_dir, AUTH_FILENAME)
        with open(auth_path, "rb") as fh:
            raw = fh.read()
        salt      = raw[:16]
        key_hash  = raw[16:48]
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
        self._attempts     = 0
        self._locked_until = 0.0
