"""
storage_manager.py  —  Tarizz Storage Layer
============================================
Responsibility : Own every file-system interaction.  Create the encrypted
                 data directory on first run; provide read/write helpers
                 that transparently encrypt on the way out and decrypt on
                 the way in.

Why a storage manager?
----------------------
The frontend writes files directly to CWD (e.g. save_current_page writes
"{page}.txt").  We cannot change that code.  Instead, we:
  1. Intercept at the *backend* integration points.
  2. Route all writes through this layer, which encrypts before touching
     disk.
  3. Store encrypted blobs under opaque, randomly-generated filenames so
     that even the *names* leak nothing about the content.

Directory layout
----------------
  ~/.tarizz/                   ← data_dir  (or %APPDATA%\\Tarizz on Win)
    auth.dat                   ← created by AuthManager
    keycheck.dat               ← created by AuthManager
    vault/                     ← all encrypted content blobs
      <hex token>.enc          ← each blob: nonce + ciphertext + GCM-tag
    media/                     ← binary media (images, video, PDFs)
      <hex token>.enc          ← encrypted copy of the original file
    index.db                   ← SQLite database (see content_index.py)

Why ~/.tarizz (or %APPDATA%)?
  • It is a *user-writable* directory — no admin rights needed.
  • On Windows it survives MSIX sandboxing (the app gets a virtual
    %APPDATA%).
  • On macOS / Linux the equivalent is ~/Library/Application Support or
    ~/.config, but ~/.tarizz keeps things simple cross-platform for now.

Microsoft-Store compatibility
  • No writes outside the data directory.
  • No COM or shell integration.
  • SQLite is fine — it is a flat file, no server process.
"""

import os
import sys
import platform

from . import crypto_engine as crypto


# ---------------------------------------------------------------------------
# Data-directory resolution
# ---------------------------------------------------------------------------
def _resolve_data_dir() -> str:
    """
    Return the absolute path to Tarizz's persistent data directory.
    Creates it if it does not exist.

    Platform logic:
      Windows  →  %APPDATA%\\Tarizz        (e.g. C:\\Users\\You\\AppData\\Roaming\\Tarizz)
      macOS    →  ~/Library/Application Support/Tarizz
      Linux    →  ~/.tarizz
    """
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "Tarizz")
    elif platform.system() == "Darwin":
        path = os.path.join(
            os.path.expanduser("~"), "Library", "Application Support", "Tarizz"
        )
    else:
        path = os.path.join(os.path.expanduser("~"), ".tarizz")

    os.makedirs(path, exist_ok=True)
    return path


class StorageManager:
    """
    Central I/O hub.  Instantiated once by the bootstrap layer and passed
    (or made available via a module-level singleton) to every other backend
    component.

    Attributes
      data_dir  – absolute path to the Tarizz data directory.
      vault_dir – sub-directory for text/JSON blobs.
      media_dir – sub-directory for binary media blobs.
    """

    def __init__(self):
        """
        Inputs  : None  (directory is resolved automatically).
        Side-effects
          • Creates ~/.tarizz (or equivalent) if missing.
          • Creates vault/ and media/ sub-directories if missing.
        """
        self.data_dir  = _resolve_data_dir()
        self.vault_dir = os.path.join(self.data_dir, "vault")
        self.media_dir = os.path.join(self.data_dir, "media")
        os.makedirs(self.vault_dir, exist_ok=True)
        os.makedirs(self.media_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Encrypted blob I/O  (vault)
    # ------------------------------------------------------------------
    def write_blob(self, blob_id: str, plaintext: bytes, key: bytes) -> str:
        """
        Encrypt *plaintext* and store it as vault/<blob_id>.enc.

        Inputs
          blob_id   – a unique identifier (hex string).  The caller is
                      responsible for generating this (use
                      crypto_engine.generate_token().hex()).
          plaintext – raw bytes to protect.
          key       – 32-byte session key.
        Output
          str       – the full path to the .enc file on disk.
        Side-effects
          • Writes one file to vault/.
        """
        encrypted = crypto.encrypt(plaintext, key)
        path = os.path.join(self.vault_dir, f"{blob_id}.enc")
        with open(path, "wb") as fh:
            fh.write(encrypted)
        return path

    def read_blob(self, blob_id: str, key: bytes) -> bytes:
        """
        Read and decrypt vault/<blob_id>.enc.

        Inputs
          blob_id – same id used in write_blob.
          key     – 32-byte session key.
        Output
          bytes   – the original plaintext.
        Raises
          FileNotFoundError  – blob_id does not exist on disk.
          InvalidTag         – tampered / wrong key.
        Side-effects
          None.
        """
        path = os.path.join(self.vault_dir, f"{blob_id}.enc")
        with open(path, "rb") as fh:
            blob = fh.read()
        return crypto.decrypt(blob, key)

    def delete_blob(self, blob_id: str) -> None:
        """Remove a vault blob from disk.  No-op if it doesn't exist."""
        path = os.path.join(self.vault_dir, f"{blob_id}.enc")
        if os.path.isfile(path):
            os.remove(path)

    # ------------------------------------------------------------------
    # Media vault  (images / video / PDFs)
    # ------------------------------------------------------------------
    def store_media(self, source_path: str, key: bytes) -> str:
        """
        Copy a file from *source_path* into the encrypted media vault.

        Why copy?
          The frontend embeds media by its *original* file path.  If the
          user moves or deletes that file, the embed breaks.  By copying
          into our vault we own the file and it survives independently.
          The original is never touched or deleted.

        Inputs
          source_path – absolute path to the file the user selected via
                        the file dialog.
          key         – 32-byte session key.
        Output
          str         – the media_id (hex token) that can be stored in
                        the content index.  The encrypted file on disk is
                        media/<media_id>.enc.
        Side-effects
          • Reads source_path.
          • Writes one encrypted file to media/.
        """
        media_id = crypto.generate_token(24).hex()   # 48-char hex name
        with open(source_path, "rb") as fh:
            raw = fh.read()
        encrypted = crypto.encrypt(raw, key)
        dest = os.path.join(self.media_dir, f"{media_id}.enc")
        with open(dest, "wb") as fh:
            fh.write(encrypted)
        return media_id

    def retrieve_media(self, media_id: str, key: bytes, dest_path: str) -> str:
        """
        Decrypt a media blob and write it to *dest_path* so the frontend
        can reference it by a real file path.

        Inputs
          media_id  – the id returned by store_media.
          key       – 32-byte session key.
          dest_path – where to write the decrypted copy (typically a
                      temp directory — see session_tmp in bootstrap).
        Output
          str       – dest_path (convenience).
        Raises
          FileNotFoundError / InvalidTag  – propagated.
        Side-effects
          • Writes one file to dest_path.
        """
        src = os.path.join(self.media_dir, f"{media_id}.enc")
        with open(src, "rb") as fh:
            blob = fh.read()
        plaintext = crypto.decrypt(blob, key)
        with open(dest_path, "wb") as fh:
            fh.write(plaintext)
        return dest_path

    def delete_media(self, media_id: str) -> None:
        """Remove a media blob.  No-op if missing."""
        path = os.path.join(self.media_dir, f"{media_id}.enc")
        if os.path.isfile(path):
            os.remove(path)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def blob_exists(self, blob_id: str) -> bool:
        """Check whether a vault blob exists on disk."""
        return os.path.isfile(os.path.join(self.vault_dir, f"{blob_id}.enc"))

    def media_exists(self, media_id: str) -> bool:
        """Check whether a media blob exists on disk."""
        return os.path.isfile(os.path.join(self.media_dir, f"{media_id}.enc"))
