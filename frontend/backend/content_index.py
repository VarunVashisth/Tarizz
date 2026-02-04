"""
content_index.py  —  Tarizz Content Index (SQLite catalogue)
=============================================================
Responsibility : Maintain a fast, queryable catalogue of every project,
                 sub-page, flowchart, and media blob that exists in the
                 encrypted vault.

Why SQLite and not a flat JSON file?
-------------------------------------
  • The project_data dict is a *tree* (nested dicts).  Serialising a
    tree to JSON and re-reading it is O(n) on every launch; with SQLite
    we can load *only* the cards the dashboard needs right now and lazy-
    load sub-trees when a project card is opened.
  • SQLite handles concurrent reads safely — future multi-window support
    won't require locking code.
  • SQLite is a single flat file; perfectly fine for MSIX packaging.

Security posture of the index
------------------------------
  The .db file on disk is NOT encrypted at the SQLite level — that would
  require a custom VFS (complex, not MSIX-friendly).  Instead:
    • Every *value* column (content, metadata) stores only the blob_id
      that points into the encrypted vault.
    • Names (project titles, page names) ARE stored in plaintext in the
      index for search speed, but they are considered low-sensitivity
      metadata (the user chose them; they are visible on screen).
    • If you later need name-level encryption too, replace the name
      columns with encrypted blobs — the rest of the schema stays the
      same.

Schema
------
  projects
    id          INTEGER PK AUTOINCREMENT
    title       TEXT        – human-readable title (low-sensitivity)
    description TEXT        – card description
    card_order  INTEGER     – position on the dashboard (0-based)
    blob_id     TEXT        – encrypted vault blob containing the full
                              project_data dict (JSON-serialised)
    created_at  REAL        – epoch timestamp
    updated_at  REAL        – epoch timestamp

  pages
    id            INTEGER PK AUTOINCREMENT
    project_id    INTEGER FK → projects.id
    page_name     TEXT        – name shown in the tree
    parent_path   TEXT        – "/" separated path of ancestor names
                                (e.g. "/Folder A/Sub Folder")
                                used to reconstruct the tree
    page_type     TEXT        – "subpage" | "flowchart"
    blob_id       TEXT        – encrypted blob with the page content
    created_at    REAL
    updated_at    REAL

  media
    id            INTEGER PK AUTOINCREMENT
    project_id    INTEGER FK → projects.id
    page_name     TEXT        – which page embeds this media
    media_id      TEXT        – token in the media/ vault directory
    original_name TEXT        – original filename (for re-download)
    media_type    TEXT        – "image" | "video" | "pdf" | "doc"
    created_at    REAL

All tables get a simple index on (project_id) for fast per-project loads.
"""

import os
import sqlite3
import time
import json
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# SQL statements  (kept as module-level constants for clarity + easy grep)
# ---------------------------------------------------------------------------
_CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL DEFAULT 'New Project',
    description TEXT    NOT NULL DEFAULT '',
    card_order  INTEGER NOT NULL DEFAULT 0,
    blob_id     TEXT,
    created_at  REAL    NOT NULL,
    updated_at  REAL    NOT NULL
);
"""

_CREATE_PAGES = """
CREATE TABLE IF NOT EXISTS pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL,
    page_name   TEXT    NOT NULL,
    parent_path TEXT    NOT NULL DEFAULT '/',
    page_type   TEXT    NOT NULL DEFAULT 'subpage',
    blob_id     TEXT,
    created_at  REAL    NOT NULL,
    updated_at  REAL    NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

_CREATE_MEDIA = """
CREATE TABLE IF NOT EXISTS media (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL,
    page_name     TEXT    NOT NULL,
    media_id      TEXT    NOT NULL,
    original_name TEXT    NOT NULL,
    media_type    TEXT    NOT NULL DEFAULT 'image',
    created_at    REAL    NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pages_project    ON pages (project_id);",
    "CREATE INDEX IF NOT EXISTS idx_media_project    ON media (project_id);",
    "CREATE INDEX IF NOT EXISTS idx_media_page       ON media (project_id, page_name);",
    "CREATE INDEX IF NOT EXISTS idx_projects_order   ON projects (card_order);",
]


class ContentIndex:
    """
    Thin ORM-free wrapper around the SQLite catalogue.

    Instantiation
      ContentIndex(db_path)  – db_path is inside the Tarizz data directory.
                               The file is created if it doesn't exist.
    """

    def __init__(self, db_path: str):
        """
        Inputs
          db_path – absolute path to index.db (inside data_dir).
        Side-effects
          • Creates the .db file and all tables if they don't exist.
          • Enables WAL mode for better concurrent-read behaviour.
          • Enables foreign-key enforcement.
        """
        self.db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # Internal — connection + schema
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        """
        Return a new connection with row_factory set so rows come back
        as dicts.  Connections are short-lived (one per logical operation)
        to avoid locking issues.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist yet."""
        conn = self._connect()
        try:
            conn.execute(_CREATE_PROJECTS)
            conn.execute(_CREATE_PAGES)
            conn.execute(_CREATE_MEDIA)
            for idx_sql in _CREATE_INDEXES:
                conn.execute(idx_sql)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Projects  (dashboard cards)
    # ------------------------------------------------------------------
    def upsert_project(self, project_id: Optional[int], title: str,
                       description: str, card_order: int,
                       blob_id: str) -> int:
        """
        Insert or update a project row.

        Inputs
          project_id   – None for insert; existing id for update.
          title        – card title text.
          description  – card description text.
          card_order   – 0-based position in the dashboard grid.
          blob_id      – vault blob containing the serialised project_data.
        Output
          int          – the row id (new or existing).
        Side-effects
          • One INSERT or UPDATE in SQLite.
        """
        now = time.time()
        conn = self._connect()
        try:
            if project_id is None:
                cur = conn.execute(
                    "INSERT INTO projects (title, description, card_order, blob_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?);",
                    (title, description, card_order, blob_id, now, now)
                )
                conn.commit()
                return cur.lastrowid
            else:
                conn.execute(
                    "UPDATE projects SET title=?, description=?, card_order=?, blob_id=?, updated_at=? "
                    "WHERE id=?;",
                    (title, description, card_order, blob_id, now, project_id)
                )
                conn.commit()
                return project_id
        finally:
            conn.close()

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Load every project row, ordered by card_order.

        Output
          List of dicts with keys: id, title, description, card_order,
          blob_id, created_at, updated_at.
        Side-effects
          None.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY card_order ASC;"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_project(self, project_id: int) -> None:
        """
        Delete a project and all its pages / media (CASCADE).

        Inputs
          project_id – the row id to remove.
        Side-effects
          • Deletes rows from projects, pages, media.
          • Caller is responsible for also deleting the actual encrypted
            blobs from the vault (see StorageManager).
        """
        conn = self._connect()
        try:
            conn.execute("DELETE FROM projects WHERE id=?;", (project_id,))
            conn.commit()
        finally:
            conn.close()

    def get_project_blob_id(self, project_id: int) -> Optional[str]:
        """Return the blob_id for one project, or None."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT blob_id FROM projects WHERE id=?;", (project_id,)
            ).fetchone()
            return row["blob_id"] if row else None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Pages  (sub-pages & flowcharts inside a project)
    # ------------------------------------------------------------------
    def upsert_page(self, page_id: Optional[int], project_id: int,
                    page_name: str, parent_path: str,
                    page_type: str, blob_id: str) -> int:
        """
        Insert or update a page row.

        Inputs
          page_id     – None for insert; existing row id for update.
          project_id  – FK to projects.
          page_name   – the name shown in the Treeview.
          parent_path – "/" delimited ancestor path (for tree rebuild).
          page_type   – "subpage" or "flowchart".
          blob_id     – vault blob with page content.
        Output
          int         – row id.
        """
        now = time.time()
        conn = self._connect()
        try:
            if page_id is None:
                cur = conn.execute(
                    "INSERT INTO pages (project_id, page_name, parent_path, page_type, blob_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (project_id, page_name, parent_path, page_type, blob_id, now, now)
                )
                conn.commit()
                return cur.lastrowid
            else:
                conn.execute(
                    "UPDATE pages SET page_name=?, parent_path=?, page_type=?, blob_id=?, updated_at=? "
                    "WHERE id=?;",
                    (page_name, parent_path, page_type, blob_id, now, page_id)
                )
                conn.commit()
                return page_id
        finally:
            conn.close()

    def get_pages_for_project(self, project_id: int) -> List[Dict[str, Any]]:
        """Load all pages for one project."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM pages WHERE project_id=? ORDER BY parent_path, page_name;",
                (project_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_page(self, page_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM pages WHERE id=?;", (page_id,))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------
    def register_media(self, project_id: int, page_name: str,
                       media_id: str, original_name: str,
                       media_type: str) -> int:
        """
        Record that a media file has been stored in the vault.

        Inputs
          project_id    – which project owns this media.
          page_name     – which page embeds it.
          media_id      – the token used in media/<media_id>.enc.
          original_name – filename the user picked (for re-download label).
          media_type    – "image" | "video" | "pdf" | "doc".
        Output
          int           – row id.
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO media (project_id, page_name, media_id, original_name, media_type, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (project_id, page_name, media_id, original_name, media_type, time.time())
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

    def get_media_for_project(self, project_id: int) -> List[Dict[str, Any]]:
        """Load all media records for one project."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM media WHERE project_id=?;", (project_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_media_for_page(self, project_id: int, page_name: str) -> List[Dict[str, Any]]:
        """Load media records for a specific page."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM media WHERE project_id=? AND page_name=?;",
                (project_id, page_name)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_media(self, media_row_id: int) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM media WHERE id=?;", (media_row_id,))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Bulk / index rebuild
    # ------------------------------------------------------------------
    def get_all_blob_ids(self) -> List[str]:
        """
        Return every blob_id referenced anywhere in the index.
        Used during cleanup to find orphaned blobs on disk.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT blob_id FROM projects WHERE blob_id IS NOT NULL "
                "UNION "
                "SELECT blob_id FROM pages WHERE blob_id IS NOT NULL;"
            ).fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()

    def get_all_media_ids(self) -> List[str]:
        """Return every media_id in the media table."""
        conn = self._connect()
        try:
            rows = conn.execute("SELECT media_id FROM media;").fetchall()
            return [r[0] for r in rows]
        finally:
            conn.close()
