"""
tarizz_bootstrap.py  —  The Bridge Between Frontend and Backend
================================================================
Responsibility : Be the ONLY place that imports backend modules AND
                 frontend modules in the same process.  Monkey-patch
                 the frontend classes at specific, well-defined hooks
                 so that all persistence is encrypted — without
                 changing a single line in the frontend source files.

Why monkey-patching and not inheritance / subclassing?
-------------------------------------------------------
  • The frontend classes are already instantiated by their own code
    (ProjectDashboard creates ProjectCards; ProjectCard opens
    ProjectManager).  To subclass we would have to change those
    instantiation lines — which we are not allowed to do.
  • Monkey-patching replaces or wraps *specific methods* after the
    class is defined but before instances are created.  The frontend
    code never knows anything changed.
  • Each patch is guarded by a clear comment explaining WHAT it
    replaces and WHY.

Integration points (the six hooks)
------------------------------------
  1. ProjectDashboard.__init__     – after the UI is built, load
                                     persisted cards from the vault.
  2. ProjectDashboard.add_card     – when a new card is created,
                                     assign it a db_id = None so the
                                     session knows it's new.
  3. ProjectDashboard.delete_selected_project
                                   – before the card widget is
                                     destroyed, tell the session to
                                     delete its encrypted data.
  4. ProjectDashboard.run          – wrap mainloop's exit to call
                                     session.shutdown().
  5. ProjectCard.__init__          – attach db_id attribute.
  6. ProjectManager.save_current_page
                                   – intercept the plain-text write
                                     and route through encrypted
                                     save instead.

What this file does NOT do
--------------------------
  • It does NOT create any Tkinter widgets.
  • It does NOT contain UI logic.
  • It does NOT touch auth.dat or any encrypted file directly —
    all that goes through SessionManager.
"""

import os
import json
import hashlib  # ← NEW: for blob_id derivation

# ---------------------------------------------------------------------------
# Backend imports  (the only place these are imported)
# ---------------------------------------------------------------------------
from backend.session_manager import SessionManager
from backend.auth_ui         import run_auth_gate


# ---------------------------------------------------------------------------
# Module-level session singleton.  Set by bootstrap(); read by patched methods.
# ---------------------------------------------------------------------------
_session: SessionManager = None


def bootstrap():
    """
    Entry point.  Called from the modified __main__ block in main.py.

    Flow:
      1. Create SessionManager  (data dir + sub-dirs appear on disk).
      2. Show auth gate         (blocks until user authenticates or quits).
      3. If auth failed         →  exit.
      4. Initialize database    →  set up new DB with session key
      5. Patch frontend classes →  attach encrypted persistence hooks.
      6. Return                 →  main.py creates ProjectDashboard as usual.

    Inputs  : None
    Output  : None  (raises SystemExit if auth fails).
    Side-effects
      • Creates ~/.tarizz (or equivalent) if missing.
      • May write auth.dat / keycheck.dat on first run.
      • Initializes database.db with session key
      • Patches ProjectDashboard and ProjectManager classes in memory.
    """
    global _session

    # --- 1. session manager (data directory is created here) ---
    _session = SessionManager()

    # --- 2. auth gate (blocks) ---
    authenticated = run_auth_gate(_session)
    if not authenticated:
        raise SystemExit(0)       # user closed the window

    # --- 3. initialize database ---
    from backend.database import init_database
    db_path = os.path.join(_session.storage.data_dir, "database.db")
    init_database(db_path, _session.session_key)

    # --- 4. patch the frontend ---
    _apply_patches()


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
def _apply_patches():
    """
    Import the frontend classes and wrap/replace the six integration
    methods.  Each patch is a closure that captures _session.
    """
    # We import here (not at module top) so that this module can be
    # imported even if tkinter is not available yet (e.g. during testing).
    import main as frontend_main
    import project_manager as frontend_pm

    # ── Patch 1: ProjectDashboard.__init__  ─────────────────────────
    #   After the original __init__ runs (UI is built, sample cards
    #   created), we REPLACE the sample cards with persisted ones.
    _orig_dashboard_init = frontend_main.ProjectDashboard.__init__

    def _patched_dashboard_init(self):
        _orig_dashboard_init(self)              # builds UI + sample cards
        _load_persisted_cards(self)             # replaces samples with vault

        # Register a WM_DELETE_WINDOW handler so we can flush on close
        self.root.protocol("WM_DELETE_WINDOW", lambda: _on_dashboard_close(self))

    frontend_main.ProjectDashboard.__init__ = _patched_dashboard_init

    # ── Patch 2: ProjectDashboard.add_card  ──────────────────────────
    #   Wrap so that every new card gets db_id = None (tells the
    #   session it hasn't been persisted yet).
    _orig_add_card = frontend_main.ProjectDashboard.add_card

    def _patched_add_card(self, title="New Project", description="Click to edit"):
        _orig_add_card(self, title, description)
        # The card that was just appended is the last one in self.cards
        new_card = self.cards[-1]
        new_card.db_id = None       # marks it as "not yet saved"

    frontend_main.ProjectDashboard.add_card = _patched_add_card

    # ── Patch 3: ProjectDashboard.delete_selected_project  ──────────
    #   Before the card is destroyed, tell the database to clean up.
    _orig_delete = frontend_main.ProjectDashboard.delete_selected_project

    def _patched_delete(self):
        if self.selected_card and hasattr(self.selected_card, "db_id"):
            db_id = self.selected_card.db_id
            if db_id is not None:
                from backend.database import _db_instance
                _db_instance.delete_project(db_id)
        _orig_delete(self)          # destroys the widget

    frontend_main.ProjectDashboard.delete_selected_project = _patched_delete

    # ── Patch 4: ProjectManager (inner class) save_current_page  ─────
    #   The inner class is created inside create_project_manager().
    #   We can't patch it directly.  Instead we wrap create_project_manager
    #   to post-patch the instance after it's created.
    _orig_create_pm = frontend_pm.create_project_manager

    def _patched_create_pm(parent, project_data=None):
        frame = _orig_create_pm(parent, project_data)
        # The ProjectManager instance is not returned, but we can
        # find it by walking the frame's children.  Instead, we patch
        # the *class* before it's instantiated — but it's defined inside
        # a function, so we use a different approach: we wrap the
        # open() built-in that save_current_page uses.  See patch 6.
        return frame

    frontend_pm.create_project_manager = _patched_create_pm

    # ── Patch 5: builtins.open  (scoped intercept for page saves)  ──
    #   save_current_page() does:
    #       file_path = f"{page}.txt"
    #       with open(file_path, 'w', encoding='utf-8') as f:
    #           f.write(content)
    #   We intercept writes to files that match "*page*.txt" in CWD and
    #   route them through encrypted save.  This is the narrowest possible
    #   intercept — it only fires for 'w' mode files ending in .txt that
    #   are in the current working directory.
    import builtins
    _real_open = builtins.open

    class _EncryptedFileProxy:
        """
        A file-like object that buffers writes and, on close/exit,
        encrypts the content and stores it in the vault.
        """
        def __init__(self, path, encoding="utf-8"):
            self._path     = path
            self._encoding = encoding
            self._buffer   = []
            self._closed   = False

        def write(self, data):
            self._buffer.append(data)
            return len(data)

        def close(self):
            if self._closed:
                return
            self._closed = True
            content = "".join(self._buffer)
            # Derive a stable blob_id from the filename so repeated
            # saves of the same page update the same blob.
            import hashlib
            page_name = os.path.splitext(os.path.basename(self._path))[0]
            blob_id   = hashlib.sha256(page_name.encode()).hexdigest()[:48]
            _session.storage.write_blob(
                blob_id, content.encode(self._encoding), _session.session_key
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        # Satisfy any code that checks .name
        @property
        def name(self):
            return self._path

    def _intercepting_open(file, mode="r", *args, **kwargs):
        """
        Drop-in replacement for builtins.open.
        - Intercepts WRITES to *.txt in CWD → encrypts to vault
        - Intercepts READS from *.txt in CWD → decrypts from vault
        Everything else passes through.
        """
        fpath = str(file)

        # Check if this is a CWD .txt operation
        is_cwd_txt = (
            fpath.endswith(".txt")
            and os.sep not in fpath
            and "/" not in fpath
            and _session is not None
            and _session.session_key is not None
        )

        # WRITE intercept
        if is_cwd_txt and "w" in mode:
            encoding = kwargs.get("encoding", "utf-8")
            return _EncryptedFileProxy(fpath, encoding)

        # READ intercept
        if is_cwd_txt and "r" in mode:
            encoding = kwargs.get("encoding", "utf-8")
            # Derive blob_id same way as write
            page_name = os.path.splitext(os.path.basename(fpath))[0]
            blob_id   = hashlib.sha256(page_name.encode()).hexdigest()[:48]
            
            # Try to read from vault
            if _session.storage.blob_exists(blob_id):
                try:
                    raw = _session.storage.read_blob(blob_id, _session.session_key)
                    content = raw.decode(encoding)
                    # Return a StringIO object so it acts like a file
                    import io
                    return io.StringIO(content)
                except Exception as e:
                    print(f"Failed to read encrypted page {fpath}: {e}")
            
            # If blob doesn't exist or failed, return empty file
            import io
            return io.StringIO("")

        # Default: real open
        return _real_open(file, mode, *args, **kwargs)

    builtins.open = _intercepting_open


# ---------------------------------------------------------------------------
# Helper: load persisted cards into the dashboard
# ---------------------------------------------------------------------------
def _load_persisted_cards(dashboard):
    """
    Replace the sample cards that __init__ created with cards restored
    from the database.

    Inputs
      dashboard – the ProjectDashboard instance (after __init__).
    Side-effects
      • Destroys existing sample cards.
      • Creates new ProjectCard instances populated from the database.
      • Sets db_id on each restored card.
    """
    import main as frontend_main
    from backend.database import _db_instance

    projects = _db_instance.get_all_projects()
    if not projects:
        # First run — keep the sample cards but give them db_id = None
        # and create them in the database
        for i, card in enumerate(dashboard.cards):
            db_id = _db_instance.create_project(
                card.get_title(),
                card.get_description(),
                i
            )
            card.db_id = db_id
            card.project_data = {'id': db_id}  # Store DB ID in project_data
        return

    # Destroy sample cards
    for card in dashboard.cards:
        card.destroy()
    dashboard.cards.clear()
    dashboard.selected_card = None

    # Recreate from database
    projects.sort(key=lambda p: p["card_order"])
    for proj in projects:
        card = frontend_main.ProjectCard(
            dashboard,
            title=proj["title"],
            description=proj["description"]
        )
        card.db_id = proj["id"]
        card.project_data = {'id': proj["id"]}  # Pass DB ID to project manager
        dashboard.cards.append(card)

    dashboard.arrange_cards()


# ---------------------------------------------------------------------------
# Helper: graceful shutdown
# ---------------------------------------------------------------------------
def _on_dashboard_close(dashboard):
    """
    Called when the user closes the main window.

    Inputs
      dashboard – the ProjectDashboard instance.
    Side-effects
      • Saves all cards to database
      • Destroys the Tk root (ends mainloop).
    """
    from backend.database import _db_instance
    
    # Save all cards
    for i, card in enumerate(dashboard.cards):
        if card.db_id:
            _db_instance.update_project(
                card.db_id,
                card.get_title(),
                card.get_description(),
                i
            )
        else:
            # New card that was added during this session
            db_id = _db_instance.create_project(
                card.get_title(),
                card.get_description(),
                i
            )
            card.db_id = db_id
    
    # Wipe temp directory
    _session._wipe_tmp()
    dashboard.root.destroy()
