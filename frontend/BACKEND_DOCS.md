# Tarizz Backend — Complete Technical Documentation

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py  (entry point)                   │
│   Only change: 2 lines added to __main__ block.                 │
│   All frontend classes (ProjectDashboard, ProjectCard, etc.)    │
│   are byte-for-byte identical in logic and UI.                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │  calls bootstrap()
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              backend/tarizz_bootstrap.py                         │
│   THE ONLY FILE THAT IMPORTS BOTH FRONTEND AND BACKEND.         │
│   • Runs the auth gate (blocks until login succeeds).           │
│   • Monkey-patches 5 frontend methods to route I/O through      │
│     the encrypted session.                                      │
│   • Intercepts builtins.open() for *.txt writes in CWD.        │
└───────────────────────────┬─────────────────────────────────────┘
                            │  imports + orchestrates
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌──────────────┐  ┌─────────────────┐  ┌───────────────┐
│  auth_ui.py  │  │ session_manager │  │  auth_manager │
│  (Tkinter    │  │   .py  (façade) │  │   .py         │
│   login UI)  │  │                 │  │  password     │
└──────────────┘  └────┬──────┬─────┘  │  hash, login, │
                       │      │        │  lockout      │
                       ▼      ▼        └───────────────┘
          ┌────────────────┐  ┌────────────────┐
          │ storage_manager│  │ content_index  │
          │   .py          │  │   .py (SQLite) │
          │  vault/ blobs  │  │  projects,     │
          │  media/ blobs  │  │  pages, media  │
          └───────┬────────┘  └────────────────┘
                  │  uses
                  ▼
          ┌────────────────┐
          │  crypto_engine │
          │   .py          │
          │  scrypt, AES-  │
          │  256-GCM       │
          └────────────────┘
```

**Data flow for a typical "save page" operation:**

```
Frontend: save_current_page()
    → writes to open("PageName.txt", "w")
        → intercepted by _intercepting_open()
            → _EncryptedFileProxy buffers the text
            → on close(): derives blob_id from page name hash
            → calls storage.write_blob(blob_id, encrypted_bytes, key)
                → crypto_engine.encrypt(plaintext, key)
                    → os.urandom(12)  → nonce
                    → AESGCM(key).encrypt(nonce, plaintext, None)
                → writes nonce + ciphertext + GCM_tag to vault/<blob_id>.enc
```

---

## 2. Folder Structure

```
your_project/
├── main.py                        ← your entry point (2 lines added)
├── project_manager.py             ← UNTOUCHED
├── simple_text_editor.py          ← UNTOUCHED
├── flowchart.py                   ← UNTOUCHED
├── requirements.txt               ← updated with `cryptography>=41.0`
└── backend/
    ├── __init__.py                ← package marker (4 lines)
    ├── crypto_engine.py           ← Layer 1: all cryptographic primitives
    ├── auth_manager.py            ← Layer 2: password create/verify/lockout
    ├── storage_manager.py         ← Layer 3: encrypted file I/O
    ├── content_index.py           ← Layer 4: SQLite catalogue
    ├── session_manager.py         ← Layer 5: façade / coordinator
    ├── auth_ui.py                 ← Layer 6: Tkinter login window
    └── tarizz_bootstrap.py        ← Layer 7: the bridge (patches frontend)
```

---

## 3. Per-File Deep Dive

### 3.1 `crypto_engine.py` — The Cryptographic Foundation

**What it does:** Every encrypt, decrypt, and key-derive call in the entire
application lives here. No other module touches raw cryptographic primitives.

**Why it exists:** Centralisation. If a vulnerability is found in AES-GCM
tomorrow, you change one file. If you scattered `AESGCM(...)` calls across
five modules, you'd miss one during a patch.

**Key functions:**

| Function | Inputs | Outputs | Side-effects |
|---|---|---|---|
| `derive_key(password, salt)` | password string, 16-byte salt | 32-byte AES key | ~100ms CPU (scrypt) |
| `encrypt(plaintext, key)` | arbitrary bytes, 32-byte key | nonce + ciphertext + GCM tag | reads OS CSPRNG |
| `decrypt(blob, key)` | output of encrypt(), same key | original plaintext | raises `InvalidTag` if tampered |
| `generate_salt()` | — | 16 random bytes | reads OS CSPRNG |
| `generate_token(length)` | int | `length` random bytes | reads OS CSPRNG |

**Security decisions explained:**

- **scrypt over Argon2:** Argon2 has no stdlib support on Windows. scrypt is
  in `hashlib` since Python 3.6. Both are memory-hard; scrypt with n=2^17
  uses ~128 MB RAM, making GPU-only attacks expensive.
- **AES-256-GCM over AES-CBC:** GCM is *authenticated* encryption. A single
  bit flip anywhere in the ciphertext causes the tag check to fail before any
  plaintext is produced. CBC requires a separate HMAC step and is easy to
  implement incorrectly (padding oracle attacks).
- **Fresh nonce per call:** GCM security collapses entirely if a (key, nonce)
  pair repeats. We use `os.urandom(12)` each time. With 96-bit nonces and one
  user, the birthday bound is ~2^48 encryptions — effectively infinite.

---

### 3.2 `auth_manager.py` — Password & Session Authentication

**What it does:** Manages master-password creation on first run, verification
on subsequent runs, and in-memory brute-force lockout.

**Why it exists:** Authentication is a *policy* layer (how many attempts?
what rules?). Encryption is a *mechanism* layer (which algorithm?). Mixing
them makes auditing dangerous.

**Disk artefacts it creates:**

| File | Contents | What it protects |
|---|---|---|
| `auth.dat` | salt (16 B) + SHA-256(derived_key) (32 B) | Lets us verify the password quickly without storing the key itself |
| `keycheck.dat` | AES-GCM encrypted sentinel ("TARIZZ_KEY_OK") | Authenticated proof that the derived key is correct — the GCM tag is the real check |

**Two-step verification explained:**
1. Derive the key from the entered password + stored salt (slow, ~100ms).
2. SHA-256(derived_key) compared to stored hash — fast early-exit if wrong.
3. Decrypt keycheck.dat with the derived key — if GCM tag validates AND the
   plaintext matches the sentinel, the password is definitely correct.

**Lockout policy:**
- 5 consecutive failures → 60-second lockout.
- Counter is in-memory only. A process restart resets it. This is intentional:
  a desktop app shouldn't lock the user out of their own machine after a
  restart. The lockout stops shoulder-surfers, not remote attackers.

---

### 3.3 `storage_manager.py` — Encrypted File I/O

**What it does:** Owns every file-system interaction. Provides `write_blob` /
`read_blob` for text/JSON data and `store_media` / `retrieve_media` for binary
files (images, video, PDFs).

**Why it exists:** The frontend writes files directly to CWD. We can't change
that. Instead, every write that matters is routed through this layer, which
encrypts before touching disk and stores under randomly-generated filenames
so even the names leak nothing.

**Directory layout it manages:**

```
~/.tarizz/                       (or %APPDATA%\Tarizz on Windows)
  vault/
    <48-char hex>.enc            encrypted text/JSON blobs
  media/
    <48-char hex>.enc            encrypted copies of user's media files
```

**Why copy media instead of referencing the original?**
The frontend embeds media by file path. If the user moves or deletes their
original file, the embed breaks. By copying into our vault we own the file
independently. The original is never touched or deleted.

---

### 3.4 `content_index.py` — SQLite Catalogue

**What it does:** A fast, queryable catalogue of every project, page, and
media blob. Three tables: `projects`, `pages`, `media`.

**Why SQLite and not JSON?**
- The project tree is nested. Loading a full JSON tree on every launch is
  O(n); with SQLite we load only what's needed right now.
- SQLite handles concurrent reads safely (future multi-window support).
- It's a single flat file — perfect for MSIX packaging.

**Security posture of the index:**
- The `.db` file is NOT encrypted at the file level. Encrypting SQLite itself
  requires a custom VFS (complex, not MSIX-friendly).
- Instead, every *value* column stores only the opaque `blob_id` that points
  into the encrypted vault. The actual content never touches the database.
- Project titles and page names are stored in plaintext for search speed.
  These are considered low-sensitivity (they're visible on screen anyway).
  If you later need name-level encryption, replace those columns with
  encrypted blobs — the rest of the schema stays the same.

---

### 3.5 `session_manager.py` — The Runtime Façade

**What it does:** The single object the bootstrap layer talks to. Holds
references to auth, storage, and index. Exposes high-level operations:
`save_project`, `load_all_projects`, `save_page`, `load_page`,
`import_media`, `export_media`, `flush`, `shutdown`.

**Why a façade?** Keeps the integration code (bootstrap) short and readable.
Makes future changes (e.g., swapping SQLite for another store) invisible to
the integration layer.

**Lifecycle:**
```
StorageManager()     → data dir exists
AuthManager()        → knows where auth.dat lives
User authenticates   → session_key is set
ContentIndex()       → SQLite tables exist
Session is "active"  → load/save calls work
App closes           → flush() persists everything, shutdown() wipes tmp
```

**The temp directory:**
When the frontend needs to open a media file by path (e.g., to play a video),
we decrypt it into a per-session temp directory. This directory is wiped on
`shutdown()`. Decrypted media never persists across restarts.

---

### 3.6 `auth_ui.py` — The Login Window

**What it does:** A standalone Tkinter window that runs BEFORE the dashboard.
Shows "Create Password" on first run, "Unlock" on subsequent runs.

**Why a separate file?** The auth window has a completely different layout
from the dashboard. It must be destroyed before the dashboard root is created
(Tkinter single-root rule). Isolation makes it swappable.

**Design decisions:**
- Live strength feedback updates as the user types (keystroke binding).
- Lockout countdown refreshes every second via `.after(1000, ...)`.
- Both "wrong password" and "locked out" show the same generic message to
  avoid revealing which state the system is in.

---

### 3.7 `tarizz_bootstrap.py` — The Bridge

**What it does:** The ONLY file that imports both frontend and backend modules.
Runs the auth gate, then monkey-patches five frontend methods.

**Why monkey-patching?** The frontend classes are instantiated by their own
code. To subclass we'd have to change those instantiation lines — forbidden.
Monkey-patching replaces specific methods after the class is defined but before
instances are created. The frontend never knows anything changed.

**The six integration hooks:**

| # | What's patched | Why |
|---|---|---|
| 1 | `ProjectDashboard.__init__` | After UI is built, replace sample cards with persisted ones from the vault |
| 2 | `ProjectDashboard.add_card` | New cards get `db_id = None` so the session knows they're unsaved |
| 3 | `ProjectDashboard.delete_selected_project` | Before widget destruction, delete encrypted data from vault |
| 4 | `WM_DELETE_WINDOW` protocol | On window close, call `session.shutdown()` to flush all cards |
| 5 | `builtins.open` | Intercept `*.txt` writes in CWD (what `save_current_page` does) and route through encrypted write |
| 6 | `create_project_manager` | Wrapping point for future per-page hooks |

**The `builtins.open` intercept in detail:**

`save_current_page()` in `project_manager.py` does:
```python
file_path = f"{page}.txt"
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

Our replacement `open()` checks: is this a `'w'` mode call to a `*.txt` file
with no directory separator (i.e., CWD)? If yes, return an
`_EncryptedFileProxy` instead of a real file handle. The proxy buffers
`write()` calls and, on `close()` (triggered by the `with` block exit),
encrypts the buffered content and stores it in the vault. The blob_id is
derived deterministically from the page name (SHA-256 hash) so repeated saves
of the same page always update the same blob.

---

## 4. How Frontend Talks to Backend

The frontend **never imports backend modules**. All communication happens
through the patches applied by `tarizz_bootstrap.py`:

```
Frontend action                    Backend hook that fires
─────────────────────────────────  ──────────────────────────────────
App starts                         bootstrap() → auth gate
User logs in                       session.login() or session.create_password()
Dashboard appears                  _load_persisted_cards() populates cards
User edits card title/desc         (in-memory only; flushed on close)
User double-clicks card            ProjectManager opens with card.project_data
User types in a subpage            (in-memory text widget)
User clicks away / focuses out     save_current_page() → open() intercepted
                                   → _EncryptedFileProxy → vault write
User inserts image/video/PDF       (frontend stores original path;
                                    bootstrap can hook insert_media in future)
User closes the app                WM_DELETE_WINDOW → session.shutdown()
                                   → flush() encrypts all cards
                                   → cleanup_orphans() removes stale blobs
                                   → tmp dir wiped
                                   → session_key zeroed in memory
```

---

## 5. Security Model

### Threat: Casual file inspection
**Mitigated by:** AES-256-GCM encryption on every blob. Even the filenames
are random hex tokens — an inspector sees nothing but opaque `.enc` files.

### Threat: Tampered data (bit-flip, malicious edit)
**Mitigated by:** GCM's authentication tag. If even one bit changes,
`decrypt()` raises `InvalidTag` before any plaintext is produced.

### Threat: Brute-force password attack (offline)
**Mitigated by:** scrypt with n=2^17 (128 MB RAM, ~100ms per attempt).
At 10,000 attempts/second (optimistic for a memory-hard function), cracking
an 8-character password with mixed case + digit takes years.

### Threat: Password stored in plaintext
**Mitigated by:** The password is never stored. Only `SHA-256(scrypt(password,
salt))` is on disk. The actual derived key is in memory only for the session.

### Threat: Key persisted across restarts
**Mitigated by:** The session key is computed fresh from the password each time.
On `shutdown()`, `self.session_key = None` scrubs it from the Python object.
(Note: Python's garbage collector may not immediately zero the memory. For
truly paranoid scrubbing, use `ctypes` to overwrite the bytes object — a
future hardening step.)

### Threat: Decrypted media left on disk after close
**Mitigated by:** All decrypted media goes into a temp directory that is
`shutil.rmtree()`'d on shutdown. Nothing survives a clean close.

### Threat: SQLite index leaks content
**Mitigated by:** The index stores only blob_ids (opaque tokens) and
low-sensitivity metadata (titles, page names). Actual content bytes never
touch the database.

---

## 6. Microsoft Store Compatibility Notes

| Requirement | Status |
|---|---|
| No writes outside app directory | ✓ All I/O is in `%APPDATA%\Tarizz` |
| No kernel drivers | ✓ Pure Python + `cryptography` (C extension, no drivers) |
| No COM / shell integration | ✓ (except `os.startfile` in the frontend — pre-existing) |
| No forbidden APIs | ✓ `hashlib`, `sqlite3`, `tempfile`, `os` are all allowed |
| Single flat-file database | ✓ SQLite |
| Packagable with MSIX | ✓ All dependencies are pip-installable, no system packages needed |

---

## 7. Future Scalability Notes

### 7.1 Per-file encryption of the SQLite database
If project titles / page names become sensitive, switch to
[SQLCipher](https://www.grinways.com/sqlcipher/) or encrypt individual
columns. The blob_id indirection pattern already isolates content; only the
metadata columns need attention.

### 7.2 Key rotation
Add a `rotate_master_password()` method to `AuthManager`:
derive the new key, re-encrypt every blob_id mapping in the index,
re-write `auth.dat` and `keycheck.dat`. The vault blobs themselves don't
need re-encryption (they're encrypted with the *session* key, not the
master password directly — but in our current design they are the same).
If you want key rotation without re-encrypting the vault, introduce a
two-level key hierarchy: master key encrypts a *vault key*; the vault key
encrypts content. Rotating the master key then only requires re-encrypting
the vault key blob.

### 7.3 Multi-user support
Replace the single `auth.dat` with a `users/` directory. Each user has their
own salt + key-hash. The vault and media directories gain a `user_id/` prefix.
The content index gains a `user_id` column.

### 7.4 Sync (future cloud option)
The blob-based architecture is sync-friendly. Each blob is immutable and
content-addressed (or at least uniquely keyed). A sync layer can upload
`*.enc` files to a remote store without ever seeing plaintext. Conflict
resolution happens at the index level (last-write-wins or merge).

### 7.5 Flowchart persistence
`FlowchartEditor` currently has no save mechanism. To persist flowcharts:
1. Serialize the canvas state (shapes list, lines list, text_items dict)
   to JSON in `FlowchartEditor`.
2. On tree-select of a flowchart node, call `session.save_page(...,
   page_type="flowchart", content=json_state)`.
3. On load, call `session.load_page(blob_id)` and reconstruct the canvas.
   No frontend changes needed — just add a `serialize()` / `deserialize()`
   method to `FlowchartEditor` and wire them in the bootstrap patches.

### 7.6 Auto-save
Currently cards are flushed on app close. For crash-resilience, add a
periodic timer (e.g., every 30 seconds) that calls `session.flush(cards)`.
Tkinter's `.after()` makes this trivial to wire in the bootstrap.

---

*Documentation generated alongside the Tarizz backend — February 2025.*
