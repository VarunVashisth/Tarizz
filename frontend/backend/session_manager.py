"""
session_manager.py  —  Tarizz Session Façade
=============================================
Responsibility : Be the single public interface between the bootstrap
                 integration layer and the rest of the backend.  No
                 frontend file imports anything from backend/ directly;
                 everything goes through this class.

Why a façade?
-------------
  • The bootstrap layer (tarizz_bootstrap.py) is the ONLY file that
    imports backend modules.  session_manager is what it imports.
  • Keeps the integration code short and readable.
  • Makes future changes (e.g., switching from SQLite to another store)
    invisible to the integration layer.

Lifecycle
---------
  1. StorageManager created  →  data dir exists.
  2. AuthManager created     →  knows where auth.dat lives.
  3. User authenticates      →  session_key is set.
  4. ContentIndex created    →  SQLite tables exist.
  5. Session is "active"     →  load/save calls work.
  6. App closes              →  flush() is called to persist any
                                in-memory dirty state.
"""

import os
import json
import tempfile
import shutil
import time
from typing import List, Dict, Any, Optional

from . import crypto_engine as crypto
from .auth_manager     import AuthManager
from .storage_manager  import StorageManager
from .content_index    import ContentIndex


class SessionManager:
    """
    The one object the integration layer needs.

    Usage (pseudocode)
      session = SessionManager()
      if session.is_first_run():
          session.create_password(pwd)
      else:
          session.login(pwd)          # sets session_key internally
      projects = session.load_all_projects()   # list of dicts
      ...
      session.flush()                 # on app close
    """

    def __init__(self):
        """
        Inputs  : None
        Side-effects
          • StorageManager is instantiated (creates data dir + sub-dirs).
          • AuthManager is instantiated (does NOT touch disk yet).
          • ContentIndex is NOT yet created — it requires the session key,
            so it is created in _activate_session().
        """
        self.storage  = StorageManager()
        self.auth     = AuthManager(self.storage.data_dir)
        self.index    = None              # set after login
        self.session_key = None           # set after login

        # Temporary directory for decrypted media the frontend needs to
        # read by file path.  Wiped when the app closes.
        self._tmp_dir = None

    # ------------------------------------------------------------------
    # Auth delegation  (thin wrappers so the integration layer doesn't
    #                    need to know about AuthManager directly)
    # ------------------------------------------------------------------
    def is_first_run(self) -> bool:
        return self.auth.is_first_run()

    def create_password(self, password: str) -> None:
        """
        First-run: create the master password and activate the session.

        Inputs
          password – validated password string.
        Side-effects
          • Writes auth.dat and keycheck.dat (via AuthManager).
          • Activates the session (index, tmp dir, etc.).
        """
        self.auth.create_password(password)
        self._activate_session(self.auth.session_key)

    def login(self, password: str) -> bool:
        """
        Subsequent-run: verify password and activate the session.

        Inputs
          password – the password the user typed.
        Output
          True  – success; session is active.
          False – failure (wrong password or locked out).
        Side-effects
          • On success: activates session.
          • On failure: may trigger lockout (see AuthManager).
        """
        if not self.auth.login(password):
            return False
        self._activate_session(self.auth.session_key)
        return True

    def is_locked(self) -> bool:
        return self.auth.is_locked()

    def lockout_remaining(self) -> float:
        return self.auth.lockout_remaining_seconds()

    # ------------------------------------------------------------------
    # Project CRUD  (called by the integration layer)
    # ------------------------------------------------------------------
    def load_all_projects(self) -> List[Dict[str, Any]]:
        """
        Load every project from the index, decrypt each project_data blob,
        and return a list ready to populate the dashboard.

        Output
          List of dicts, each with:
            "db_id"       – the SQLite row id (needed for later updates)
            "title"       – card title
            "description" – card description
            "card_order"  – grid position
            "project_data"– the decrypted, deserialised nested dict that
                            the frontend passes to ProjectManager
        Side-effects
          None (read-only).
        """
        rows = self.index.get_all_projects()
        result = []
        for row in rows:
            project_data = {}
            if row["blob_id"]:
                try:
                    raw = self.storage.read_blob(row["blob_id"], self.session_key)
                    project_data = json.loads(raw.decode("utf-8"))
                except Exception:
                    # Blob missing or corrupted — start with empty dict.
                    # A production app would log a warning here.
                    project_data = {}
            result.append({
                "db_id":        row["id"],
                "title":        row["title"],
                "description":  row["description"],
                "card_order":   row["card_order"],
                "project_data": project_data,
            })
        return result

    def save_project(self, db_id: Optional[int], title: str,
                     description: str, card_order: int,
                     project_data: dict) -> int:
        """
        Persist (or update) one project card.

        Inputs
          db_id        – None for a brand-new card; existing id for update.
          title        – current card title.
          description  – current card description.
          card_order   – current grid position.
          project_data – the nested dict from ProjectCard.project_data.
        Output
          int          – the db_id (new or existing) — the caller should
                         cache this on the card for future updates.
        Side-effects
          • Encrypts project_data JSON → vault blob.
          • Inserts or updates the projects table row.
        """
        # Serialise + encrypt the project tree
        json_bytes = json.dumps(project_data).encode("utf-8")
        blob_id = crypto.generate_token(24).hex()
        self.storage.write_blob(blob_id, json_bytes, self.session_key)

        # Persist in the index
        new_id = self.index.upsert_project(
            db_id, title, description, card_order, blob_id
        )

        # If we updated an existing row, the old blob is now orphaned.
        # We don't delete it here to keep this call fast; flush() or a
        # periodic cleanup pass handles orphan removal.
        return new_id

    def delete_project(self, db_id: int) -> None:
        """
        Remove a project and all its pages / media from index AND vault.

        Inputs
          db_id – the project row id.
        Side-effects
          • Deletes encrypted blobs (project + all its pages).
          • Deletes encrypted media blobs.
          • Deletes index rows (CASCADE handles pages + media rows).
        """
        # Gather blob_ids and media_ids before deleting index rows
        project_blob = self.index.get_project_blob_id(db_id)
        pages  = self.index.get_pages_for_project(db_id)
        medias = self.index.get_media_for_project(db_id)

        # Delete from index (CASCADE removes pages + media rows)
        self.index.delete_project(db_id)

        # Delete actual encrypted files
        if project_blob:
            self.storage.delete_blob(project_blob)
        for p in pages:
            if p["blob_id"]:
                self.storage.delete_blob(p["blob_id"])
        for m in medias:
            self.storage.delete_media(m["media_id"])

    # ------------------------------------------------------------------
    # Page persistence  (sub-pages + flowcharts)
    # ------------------------------------------------------------------
    def save_page(self, project_id: int, page_name: str,
                  parent_path: str, page_type: str,
                  content: str, existing_page_id: Optional[int] = None) -> int:
        """
        Encrypt and persist one page's content.

        Inputs
          project_id      – owning project's db id.
          page_name       – name shown in the Treeview.
          parent_path     – "/" delimited ancestor path.
          page_type       – "subpage" or "flowchart".
          content         – the text or JSON content of the page.
          existing_page_id– row id if updating; None if new.
        Output
          int             – the page row id.
        Side-effects
          • Writes an encrypted blob.
          • Inserts/updates a pages row.
        """
        blob_id = crypto.generate_token(24).hex()
        self.storage.write_blob(
            blob_id, content.encode("utf-8"), self.session_key
        )
        return self.index.upsert_page(
            existing_page_id, project_id, page_name,
            parent_path, page_type, blob_id
        )

    def load_page(self, blob_id: str) -> str:
        """
        Decrypt and return a page's text content.

        Inputs
          blob_id – from the pages table.
        Output
          str     – the page content.
        """
        raw = self.storage.read_blob(blob_id, self.session_key)
        return raw.decode("utf-8")

    # ------------------------------------------------------------------
    # Media management
    # ------------------------------------------------------------------
    def import_media(self, project_id: int, page_name: str,
                     source_path: str, media_type: str) -> Dict[str, str]:
        """
        Copy a file into the encrypted media vault and record it.

        Inputs
          project_id  – owning project.
          page_name   – which page embeds this.
          source_path – original file path the user picked.
          media_type  – "image" | "video" | "pdf" | "doc".
        Output
          dict with:
            "media_id"      – opaque token (for internal tracking).
            "original_name" – the basename of source_path.
        Side-effects
          • Copies + encrypts the file into media/.
          • Inserts a row in the media table.
        """
        media_id = self.storage.store_media(source_path, self.session_key)
        original_name = os.path.basename(source_path)
        self.index.register_media(
            project_id, page_name, media_id, original_name, media_type
        )
        return {"media_id": media_id, "original_name": original_name}

    def export_media(self, media_id: str, original_name: str) -> str:
        """
        Decrypt a media blob into the session's temp directory so the
        frontend can reference it by an actual file path.

        Inputs
          media_id      – the token from import_media.
          original_name – used as the filename in the tmp dir.
        Output
          str           – absolute path to the decrypted temp file.
        Side-effects
          • Writes one file to the session tmp directory.
        """
        dest = os.path.join(self._tmp_dir, original_name)
        # Avoid collisions if two pages embed files with the same name
        base, ext = os.path.splitext(dest)
        counter = 1
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1
        return self.storage.retrieve_media(media_id, self.session_key, dest)

    # ------------------------------------------------------------------
    # Bulk flush  (call on app close)
    # ------------------------------------------------------------------
    def flush(self, cards: list) -> None:
        """
        Persist the current in-memory state of ALL dashboard cards.
        Called once when the application is about to exit.

        Inputs
          cards – the list of ProjectCard objects from ProjectDashboard.
                  Each card must have: .db_id, .get_title(),
                  .get_description(), .project_data, and its index
                  in the list is its card_order.
        Side-effects
          • Writes/updates encrypted blobs for every card.
          • Updates the projects table.
        """
        for order, card in enumerate(cards):
            self.save_project(
                db_id=getattr(card, "db_id", None),
                title=card.get_title(),
                description=card.get_description(),
                card_order=order,
                project_data=card.project_data,
            )

    # ------------------------------------------------------------------
    # Cleanup  (orphan removal)
    # ------------------------------------------------------------------
    def cleanup_orphans(self) -> None:
        """
        Walk the vault/ and media/ directories; delete any .enc file
        whose id is NOT referenced by the content index.

        TEMPORARILY DISABLED: Page content blobs written by the open()
        intercept are not in the index yet, so they get deleted. We need
        a smarter approach that excludes SHA256-derived page blob_ids.
        
        TODO: Either:
        1. Register page blobs in the index when written, OR
        2. Exclude blob_ids matching SHA256(page_name) pattern
        """
        # Disabled for now
        return
        
        # Original code kept for reference:
        # known_blobs  = set(self.index.get_all_blob_ids())
        # known_medias = set(self.index.get_all_media_ids())
        # 
        # for fname in os.listdir(self.storage.vault_dir):
        #     if fname.endswith(".enc"):
        #         blob_id = fname[:-4]
        #         if blob_id not in known_blobs:
        #             os.remove(os.path.join(self.storage.vault_dir, fname))
        #
        # for fname in os.listdir(self.storage.media_dir):
        #     if fname.endswith(".enc"):
        #         media_id = fname[:-4]
        #         if media_id not in known_medias:
        #             os.remove(os.path.join(self.storage.media_dir, fname))

    # ------------------------------------------------------------------
    # Session teardown
    # ------------------------------------------------------------------
    def shutdown(self, cards: list) -> None:
        """
        Full graceful shutdown sequence.

        Inputs
          cards – same as flush().
        Side-effects
          • Flushes all cards.
          • Cleans up orphaned blobs.
          • Wipes the session tmp directory (decrypted media).
          • Clears session_key from memory.
        """
        self.flush(cards)
        self.cleanup_orphans()
        self._wipe_tmp()
        self.session_key = None      # scrub the key from memory

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------
    def _activate_session(self, key: bytes) -> None:
        """
        Called after successful auth.  Sets up the index and tmp dir.

        Inputs
          key – the 32-byte session key from AuthManager.
        Side-effects
          • self.session_key is set.
          • ContentIndex is instantiated (creates tables if needed).
          • A temp directory is created for decrypted media.
        """
        self.session_key = key
        base_dir = os.path.expanduser("~/.tarizz")
        os.makedirs(base_dir, exist_ok=True)
     
        db_path = os.path.join(base_dir, "index.db")
        self.index = ContentIndex(db_path)
        # Temp dir for media the frontend needs to open by path.
        # tempfile.mkdtemp() returns a unique dir; we wipe it on shutdown.
        self._tmp_dir = tempfile.mkdtemp(prefix="tarizz_session_")

    def _wipe_tmp(self) -> None:
        """Remove the session temp directory and all its contents."""
        if self._tmp_dir and os.path.isdir(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None
