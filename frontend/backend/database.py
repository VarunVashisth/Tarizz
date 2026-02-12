"""
database.py — Simplified Tarizz Database Layer
===============================================
A clean SQLite schema with parent-child relationships for the tree structure
and encrypted content storage for all text/media.

Schema Design:
--------------
1. projects table — dashboard cards
2. nodes table — tree hierarchy (folders, subpages, flowcharts)
3. content table — encrypted text content with formatting dump
4. media table — tracks media files with their encrypted paths

Every piece of data is encrypted before storage.
"""

import sqlite3
import json
import os
from typing import Optional, Dict, List, Any
import hashlib

# Import crypto from the backend
try:
    from backend.crypto_engine import encrypt, decrypt
except ImportError:
    # Fallback for testing
    encrypt = lambda data, key: data
    decrypt = lambda data, key: data

_db_instance = None  # Singleton instance of Database
_db_path = None

def set_db_path(path: str):
    """Set the database path for the current vault"""
    global _db_path
    _db_path = path

def get_db_path() -> str:
    """Get the current database path"""
    global _db_path
    if not _db_path:
        raise RuntimeError("Database path not set. Please authenticate first.")
    return _db_path
    
    
    # Default fallback
    import os
    if os.name == 'nt':
        default_dir = os.path.join(os.environ.get('APPDATA', '.'), 'Tarizz')
    else:
        default_dir = os.path.join(os.path.expanduser('~'), '.tarizz')
    
    os.makedirs(default_dir, exist_ok=True)
    return os.path.join(default_dir, 'tarizz.db')

def get_db():
    global _db_instance
    if _db_instance is None:
        db_path = get_db_path()
        _db_instance = Database(db_path)
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
        return cls._instance
    
    @classmethod
    def set_session_key(cls, key: bytes):
        """Set the encryption key for this session"""
        cls._session_key = key
    
    def _connect(self) -> sqlite3.Connection:
        """Create a new connection with dict row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    
    def _init_db(self):
        """Create all tables if they don't exist"""


        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._connect()
        try:
            # Projects table - dashboard cards
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
            
            # Nodes table - tree structure (folders, subpages, flowcharts)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    parent_id INTEGER,
                    node_type TEXT NOT NULL CHECK(node_type IN ('folder', 'subpage', 'flowchart')),
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)
            
            # Content table - encrypted text content with text widget dump
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    node_id INTEGER NOT NULL UNIQUE,
                    encrypted_dump BLOB NOT NULL,
                    updated_at REAL NOT NULL,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                );
            """)
            
            # Media table - tracks embedded media with encrypted file paths
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
            
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_content_node ON content(node_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_media_node ON media(node_id);")
            
            conn.commit()
        finally:
            conn.close()
    
    # ========================================================================
    # PROJECTS (Dashboard Cards)
    # ========================================================================
    
    def create_project(self, title: str, description: str, card_order: int) -> int:
        """Create a new project card"""
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
        """Update project card"""
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
        """Load all project cards ordered by card_order"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY card_order ASC;"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def delete_project(self, project_id: int):
        """Delete project and all its nodes (CASCADE handles children)"""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM projects WHERE id=?;", (project_id,))
            conn.commit()
        finally:
            conn.close()
    
    # ========================================================================
    # NODES (Tree Structure)
    # ========================================================================
    
    def create_node(self, project_id: int, parent_id: Optional[int], 
                   node_type: str, name: str) -> int:
        """
        Create a node in the tree.
        
        Rules enforced:
        - Folders can contain folders or subpages or flowcharts
        - Subpages CANNOT contain anything (leaf nodes)
        - Flowcharts CANNOT contain anything (leaf nodes)
        """
        import time
        
        # Validate parent isn't a subpage or flowchart
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
                "INSERT INTO nodes (project_id, parent_id, node_type, name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?);",
                (project_id, parent_id, node_type, name, now, now)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_nodes(self, project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
        """Get all child nodes of a parent (or root nodes if parent_id is None)"""
        conn = self._connect()
        try:
            if parent_id is None:
                # Get root nodes (those with no parent)
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
        """Get ALL nodes in a project (for tree rebuilding)"""
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
        """Rename a node"""
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
        """Delete node and all its children (CASCADE)"""
        conn = self._connect()
        try:
            conn.execute("DELETE FROM nodes WHERE id=?;", (node_id,))
            conn.commit()
        finally:
            conn.close()
    
    # ========================================================================
    # CONTENT (Encrypted Text Widget Dumps)
    # ========================================================================
    
    def save_subpage(self, node_id: int, data_dump: Dict):
        """
        Save dict with 'content' (str) and 'tags' (dict of lists)
        """
        import time
        
        json_str = json.dumps(data_dump)
        
        if self._session_key:
            encrypted = encrypt(json_str.encode('utf-8'), self._session_key)
        else:
            encrypted = json_str.encode('utf-8')
        
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
            conn.commit()
        finally:
            conn.close()
    
    def load_subpage(self, node_id: int) -> Optional[Dict]:
        """Load and decrypt dict dump"""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT encrypted_dump FROM content WHERE node_id=?;", (node_id,)
            ).fetchone()
            
            if not row:
                return None
            
            if self._session_key:
                decrypted = decrypt(row['encrypted_dump'], self._session_key)
            else:
                decrypted = row['encrypted_dump']
            
            json_str = decrypted.decode('utf-8')
            return json.loads(json_str)
        finally:
            conn.close()
    
    # ========================================================================
    # MEDIA (Embedded Files)
    # ========================================================================
    
    def save_media(self, node_id: int, media_type: str, file_path: str, 
                   original_filename: str, position_index: str) -> int:
        """
        Save media reference with encrypted file path.
        
        file_path: the actual path on disk
        position_index: text widget index where it's inserted (e.g., "1.5")
        """
        import time
        
        # Encrypt the file path
        if self._session_key:
            encrypted_path = encrypt(file_path.encode('utf-8'), self._session_key)
        else:
            encrypted_path = file_path.encode('utf-8')
        
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

    def update_media(self, media_id: int , position: str ):
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
        """Get all media for a node with decrypted paths"""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM media WHERE node_id=? ORDER BY created_at;", (node_id,)
            ).fetchall()
            
            result = []
            for row in rows:
                item = dict(row)
                # Decrypt path
                if self._session_key:
                    decrypted_path = decrypt(row['encrypted_path'], self._session_key)
                else:
                    decrypted_path = row['encrypted_path']
                item['file_path'] = decrypted_path.decode('utf-8')
                del item['encrypted_path']  # Remove encrypted version
                result.append(item)
            
            return result
        finally:
            conn.close()
    
    def delete_media(self, media_id: int):
        """Delete a media reference"""
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


# ============================================================================
# PUBLIC API (for project_manager.py to import)
# ============================================================================


def reset_database():
    """Reset the entire database (for testing)"""
    return get_db().reset_database()

def create_node(project_id: int, parent_id: Optional[int], 
                node_type: str, name: str) -> int:
    """Create a tree node"""
    return get_db().create_node(project_id, parent_id, node_type, name)

def get_nodes(project_id: int, parent_id: Optional[int] = None) -> List[Dict]:
    """Get child nodes"""
    return get_db().get_nodes(project_id, parent_id)
def get_all_nodes_for_project(project_id: int) -> List[Dict]:
    """Get all nodes for a project"""
    return get_db().get_all_nodes_for_project(project_id)

def rename_node(node_id: int, new_name: str):
    """Rename a node"""
    return get_db().rename_node(node_id, new_name)

def delete_node(node_id: int):
    """Delete a node"""
    get_db().delete_node(node_id)

def save_subpage(node_id: int, data_dump: Dict):
    """Save dict dump encrypted"""
    return get_db().save_subpage(node_id, data_dump)

def load_subpage(node_id: int) -> Optional[Dict]:
    """Load dict dump decrypted"""
    return get_db().load_subpage(node_id)
def save_media(node_id: int, media_type: str, file_path: str,
               original_filename: str, position_index: str) -> int:
    """Save media reference"""
    return get_db().save_media(node_id, media_type, file_path, 
                                   original_filename, position_index)

def get_media_for_node(node_id: int) -> List[Dict]:
    """Get all media for a node"""
    return get_db().get_media_for_node(node_id)

def get_all_projects() -> List[Dict]:
    """Get all project cards"""
    return get_db().get_all_projects()
def create_project(title: str, description: str, card_order: int) -> int:
    """Create a new project card"""
    return get_db().create_project(title, description, card_order)

def update_project(project_id: int, title: str, description: str, card_order: int):
    """Update a project card"""
    return get_db().update_project(project_id, title, description, card_order) 

def delete_project(project_id: int):
    """Delete a project card and all its nodes"""
    return get_db().delete_project(project_id)

def update_media_position(media_id: int, position: str):
    get_db().update_media(media_id, position)
