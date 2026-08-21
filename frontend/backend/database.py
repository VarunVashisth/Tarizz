
import sqlite3
import json
import os
import shutil
import uuid
from typing import Optional, Dict, List, Any

try:
    from backend.crypto_engine import encrypt, decrypt
except ImportError:
    encrypt = lambda data, key: data
    decrypt = lambda data, key: data

_db_instance = None
_db_path = None
_media_dir = None


def set_db_path(path: str):
    """Set the active vault database and its matching media directory."""
    global _db_path, _db_instance, _media_dir
    _db_path = os.path.abspath(path)
    _media_dir = os.path.join(os.path.dirname(_db_path), "media")
    os.makedirs(_media_dir, exist_ok=True)
    _db_instance = None
    Database._instance = None


def set_media_dir(path: str):
    global _media_dir
    _media_dir = path
    os.makedirs(path, exist_ok=True)


def get_media_dir() -> str:
    global _media_dir
    if not _media_dir:
        # Backward-compatible recovery for sessions initialized by older code.
        if _db_path:
            _media_dir = os.path.join(os.path.dirname(os.path.abspath(_db_path)), "media")
            os.makedirs(_media_dir, exist_ok=True)
        else:
            raise RuntimeError("Media directory not set. Please authenticate first.")
    return _media_dir


def get_db_path() -> str:
    global _db_path
    if not _db_path:
        raise RuntimeError("Database path not set. Please authenticate first.")
    return _db_path


def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(get_db_path())
    return _db_instance


class Database:
    """Singleton database manager"""
    _instance = None
    _session_key = None

    def __new__(cls, db_path: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._init_db()
        elif getattr(cls._instance, "db_path", None) != db_path:
            cls._instance.db_path = db_path
            cls._instance._init_db()
        return cls._instance

    @classmethod
    def set_session_key(cls, key: bytes):
        cls._session_key = key

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    card_order INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    parent_id INTEGER,
                    node_type TEXT NOT NULL CHECK(node_type IN ('folder', 'subpage', 'flowchart')),
                    name TEXT NOT NULL,
                    formatting TEXT DEFAULT '[]',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL UNIQUE,
                    encrypted_dump BLOB NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL,
                    media_type TEXT NOT NULL CHECK(media_type IN ('image', 'video', 'pdf', 'doc')),
                    encrypted_path BLOB NOT NULL,
                    original_filename TEXT,
                    position_index TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)

            self._ensure_column(conn, "nodes", "formatting", "TEXT DEFAULT '[]'")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_node ON content(node_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_node ON media(node_id);")

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _ensure_column(conn, table, column, decl):
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl};")

    def create_project(self, title: str, description: str, card_order: int) -> int:
        import time
        now = time.time()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO projects (title, description, card_order, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?);",
                (title, description, card_order, now, now)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_project(self, project_id: int, title: str, description: str, card_order: int):
        import time
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE projects SET title=?, description=?, card_order=?, updated_at=? WHERE id=?;",
                (title, description, card_order, time.time(), project_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_projects(self) -> List[Dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY card_order ASC;"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_project(self, project_id: int):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM projects WHERE id=?;", (project_id,))
            conn.commit()
        finally:
            conn.close()

    def create_node(self, project_id: int, parent_id: Optional[int],
                    node_type: str, name: str) -> int:
        import time

        if parent_id:
            conn = self._connect()
            try:
                parent = conn.execute(
                    "SELECT node_type FROM nodes WHERE id=?;", (parent_id,)
                ).fetchone()
                if parent and parent['node_type'] in ('subpage', 'flowchart'):
                    raise ValueError(f"Cannot add child to {parent['node_type']}")
            finally:
                conn.close()

        now = time.time()
        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO nodes (project_id, parent_id, node_type, name, formatting, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, '[]', ?, ?);",
                (project_id, parent_id, node_type, name, now, now)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_node(self, node_id: int) -> Optional[Dict]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM nodes WHERE id=?;", (node_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_nodes(self, project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
        conn = self._connect()
        try:
            if parent_id is None:
                rows = conn.execute(
                    "SELECT * FROM nodes WHERE project_id=? AND parent_id IS NULL ORDER BY created_at;",
                    (project_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM nodes WHERE project_id=? AND parent_id=? ORDER BY created_at;",
                    (project_id, parent_id)
                ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_all_nodes_for_project(self, project_id: int) -> List[Dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE project_id=? ORDER BY created_at;",
                (project_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def rename_node(self, node_id: int, new_name: str):
        import time
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE nodes SET name=?, updated_at=? WHERE id=?;",
                (new_name, time.time(), node_id)
            )
            conn.commit()
        finally:
            conn.close()

    def delete_node(self, node_id: int):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM nodes WHERE id=?;", (node_id,))
            conn.commit()
        finally:
            conn.close()

    def _normalize_dump(self, data_dump) -> Dict:
        if data_dump is None:
            return {"content": "", "tags": {}, "formatting": []}
        if isinstance(data_dump, str):
            return {"content": data_dump, "tags": {}, "formatting": []}
        if isinstance(data_dump, dict):
            dump = dict(data_dump)
            dump.setdefault("content", "")
            dump.setdefault("tags", {})
            dump.setdefault("formatting", [])
            return dump
        return {"content": "", "tags": {}, "formatting": []}

    def save_subpage(self, node_id: int, data_dump):
        import time

        dump = self._normalize_dump(data_dump)
        json_str = json.dumps(dump)

        if self._session_key:
            encrypted = encrypt(json_str.encode("utf-8"), self._session_key)
        else:
            encrypted = json_str.encode("utf-8")

        formatting_json = json.dumps(dump.get("formatting") or dump.get("tags") or [])

        conn = self._connect()
        try:
            exists = conn.execute(
                "SELECT id FROM content WHERE node_id=?;", (node_id,)
            ).fetchone()

            if exists:
                conn.execute(
                    "UPDATE content SET encrypted_dump=?, updated_at=? WHERE node_id=?;",
                    (encrypted, time.time(), node_id)
                )
            else:
                conn.execute(
                    "INSERT INTO content (node_id, encrypted_dump, updated_at) VALUES (?, ?, ?);",
                    (node_id, encrypted, time.time())
                )
            conn.execute(
                "UPDATE nodes SET formatting=?, updated_at=? WHERE id=?;",
                (formatting_json, time.time(), node_id)
            )
            conn.commit()
        finally:
            conn.close()

    def load_subpage(self, node_id: int) -> Optional[Dict]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT encrypted_dump FROM content WHERE node_id=?;", (node_id,)
            ).fetchone()

            if not row:
                return {"content": "", "tags": {}, "formatting": []}

            blob = row["encrypted_dump"]
            if self._session_key:
                decrypted = decrypt(blob, self._session_key)
            else:
                decrypted = blob

            parsed = json.loads(decrypted.decode("utf-8"))
            return self._normalize_dump(parsed)
        finally:
            conn.close()

    def import_media_file(self, src_path: str) -> str:
        """Copy a user file into the app media library and return the new path."""
        if not src_path or not os.path.exists(src_path):
            raise FileNotFoundError("Media file does not exist")
        media_dir = get_media_dir()
        ext = os.path.splitext(src_path)[1]
        dest_name = uuid.uuid4().hex + ext
        dest = os.path.join(media_dir, dest_name)
        shutil.copy2(src_path, dest)
        return dest

    def save_media(self, node_id: int, media_type: str, file_path: str,
                   original_filename: str, position_index: str) -> int:
        import time

        if self._session_key:
            encrypted_path = encrypt(file_path.encode("utf-8"), self._session_key)
        else:
            encrypted_path = file_path.encode("utf-8")

        conn = self._connect()
        try:
            cursor = conn.execute(
                "INSERT INTO media (node_id, media_type, encrypted_path, original_filename, position_index, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (node_id, media_type, encrypted_path, original_filename, position_index, time.time())
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_media(self, media_id: int, position: str):
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE media SET position_index=? WHERE id=?;",
                (position, media_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_media_for_node(self, node_id: int) -> List[Dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM media WHERE node_id=? ORDER BY created_at;", (node_id,)
            ).fetchall()

            result = []
            for row in rows:
                item = dict(row)
                if self._session_key:
                    decrypted_path = decrypt(row["encrypted_path"], self._session_key)
                else:
                    decrypted_path = row["encrypted_path"]
                item["file_path"] = decrypted_path.decode("utf-8")
                del item["encrypted_path"]
                result.append(item)
            return result
        finally:
            conn.close()

    def delete_media(self, media_id: int):
        conn = self._connect()
        try:
            conn.execute("DELETE FROM media WHERE id=?;", (media_id,))
            conn.commit()
        finally:
            conn.close()

    def reset_database(self):
        global _db_instance
        _db_instance = None
        Database._instance = None


def reset_database():
    global _db_instance
    _db_instance = None
    Database._instance = None


def create_node(project_id: int, parent_id: Optional[int],
                node_type: str, name: str) -> int:
    return get_db().create_node(project_id, parent_id, node_type, name)


def get_nodes(project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
    return get_db().get_nodes(project_id, parent_id)


def get_all_nodes_for_project(project_id: int) -> List[Dict]:
    return get_db().get_all_nodes_for_project(project_id)


def get_node(node_id: int) -> Optional[Dict]:
    return get_db().get_node(node_id)


def rename_node(node_id: int, new_name: str):
    return get_db().rename_node(node_id, new_name)


def delete_node(node_id: int):
    get_db().delete_node(node_id)


def save_subpage(node_id: int, data_dump):
    return get_db().save_subpage(node_id, data_dump)


def load_subpage(node_id: int) -> Optional[Dict]:
    return get_db().load_subpage(node_id)


def save_media(node_id: int, media_type: str, file_path: str,
               original_filename: str, position_index: str) -> int:
    return get_db().save_media(node_id, media_type, file_path,
                               original_filename, position_index)


def import_media_file(src_path: str) -> str:
    return get_db().import_media_file(src_path)


def get_media_for_node(node_id: int) -> List[Dict]:
    return get_db().get_media_for_node(node_id)


def get_all_projects() -> List[Dict]:
    return get_db().get_all_projects()


def create_project(title: str, description: str, card_order: int) -> int:
    return get_db().create_project(title, description, card_order)


def update_project(project_id: int, title: str, description: str, card_order: int):
    return get_db().update_project(project_id, title, description, card_order)


def delete_project(project_id: int):
    return get_db().delete_project(project_id)


def update_media_position(media_id: int, position: str):
    get_db().update_media(media_id, position)


def delete_media(media_id: int):
    get_db().delete_media(media_id)
