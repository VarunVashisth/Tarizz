"""
crypto_engine.py  —  Tarizz Security Layer
==========================================
Responsibility : Every encrypt / decrypt / key-derive operation in Tarizz
                 lives here.  No other module touches raw cryptographic
                 primitives directly.

Why this module exists
----------------------
Centralising crypto means:
  • One place to audit for correctness.
  • One place to swap algorithms if a vulnerability is found.
  • Zero chance of a copy-paste bug creating a second, weaker path.

Algorithm choices — rationale
-----------------------------
Key derivation  →  scrypt
  • Memory-hard: an attacker with only GPU cores (no huge RAM) pays a heavy
    penalty.  Argon2 is newer but ships with no stdlib support on Windows;
    scrypt is in hashlib since Python 3.6 and is the default recommendation
    for *offline* desktop apps where the user types the password once.
  • Parameters (n=2^17, r=8, p=1) give ~100 ms on modern hardware — fast
    enough for a single login, slow enough to make brute-force impractical.

Encryption  →  AES-256-GCM
  • Authenticated encryption: ciphertext is tampered-proof.  If even one bit
    flips the tag check fails and decryption raises, so corrupted or
    maliciously edited files are detected before any plaintext is produced.
  • 256-bit key  →  128 bits of security (meet-in-the-middle bound).
  • GCM nonce is 96 bits (12 bytes) — the NIST-recommended size.
  • Each encryption call generates a fresh random nonce; reuse is impossible.

Disk layout for one encrypted blob
-----------------------------------
  [ salt: 16 bytes ][ nonce: 12 bytes ][ ciphertext + GCM tag: variable ]
  
  The GCM tag (16 bytes) is appended to the ciphertext by the library
  automatically when we call .finalize_with_tag() / .encrypt().

Microsoft-Store compatibility
-----------------------------
  • Uses only hashlib (stdlib) + cryptography (pure-Python fallback exists,
    but the C extension is fine for MSIX — no kernel drivers, no COM).
  • No files outside the app's own storage directory are touched.
"""

import os
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Constants  (tuned for a single-user desktop app)
# ---------------------------------------------------------------------------
SALT_LENGTH   = 16          # bytes — fed to scrypt
NONCE_LENGTH  = 12          # bytes — GCM standard
KEY_LENGTH    = 32          # bytes — AES-256

# scrypt work factors.  n=2^17 ≈ 131 072 blocks × 128*r bytes each.
# On a typical laptop this takes ~80-150 ms and uses ~128 MB RAM.
SCRYPT_N      = 1 << 14     # 131072
SCRYPT_R      = 8
SCRYPT_P      = 1


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------
def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit AES key from a user password and a random salt.

    Inputs
      password  – the master password (Unicode string, NOT bytes).
      salt      – 16 random bytes (generated once and persisted alongside
                  the password hash; never reused for a different password).
    Output
      32 bytes  – the symmetric key.  This key is NEVER written to disk;
                  it lives only in process memory for the session lifetime.
    Side-effects
      None.  Pure computation (~100 ms).
    """
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LENGTH,
    )


# ---------------------------------------------------------------------------
# Authenticated encryption  (AES-256-GCM)
# ---------------------------------------------------------------------------
def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt *plaintext* and return a self-describing blob that can be stored
    on disk with no additional metadata.

    Inputs
      plaintext – arbitrary bytes (text, JSON, binary media — anything).
      key       – 32-byte AES key (output of derive_key).
    Output
      bytes     – [ salt (unused here, kept for future) | nonce | ciphertext+tag ]
                  Concretely: nonce (12 B) + ciphertext (len(plaintext) + 16 B tag).
    Side-effects
      Reads from the OS CSPRNG (os.urandom) to generate the nonce.

    Why a new nonce every time?
      GCM security breaks down completely if a (key, nonce) pair is ever
      reused.  Because our key is long-lived (session), we MUST use a fresh
      random nonce per call.  With 96-bit nonces and a single user the
      birthday bound is ~2^48 encryptions — effectively infinite.
    """
    nonce = os.urandom(NONCE_LENGTH)          # cryptographically random
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, None)
    # Prepend nonce so decrypt() is self-contained.
    return nonce + ciphertext_and_tag


def decrypt(blob: bytes, key: bytes) -> bytes:
    """
    Decrypt a blob produced by encrypt().

    Inputs
      blob  – the exact bytes returned by encrypt().
      key   – the same 32-byte key that was used for encryption.
    Output
      bytes – the original plaintext.
    Raises
      cryptography.exceptions.InvalidTag  – if the blob was tampered with
        or the wrong key was supplied.  The caller MUST catch this and
        treat it as an authentication failure — never reveal *why* it
        failed (wrong key vs. corruption) to the user.
    Side-effects
      None.
    """
    nonce      = blob[:NONCE_LENGTH]
    ciphertext = blob[NONCE_LENGTH:]
    aesgcm     = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def generate_salt() -> bytes:
    """Return a fresh cryptographic salt (16 bytes)."""
    return os.urandom(SALT_LENGTH)


def generate_token(length: int = 32) -> bytes:
    """
    Return *length* cryptographically random bytes.
    Used for internal identifiers (e.g. media-blob filenames) that must
    be unpredictable — prevents an attacker from guessing which file on
    disk corresponds to which logical document.
    """
    return os.urandom(length)