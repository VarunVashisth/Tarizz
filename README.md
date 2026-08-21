# Tarizz - Advanced Project Management & Documentation Tool

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

> A powerful desktop application for managing projects with rich text editing, flowcharts, media embedding, and intelligent code block formatting.



# Tarizz

Tarizz is a desktop application for organizing projects into a folder tree, writing formatted documentation, embedding media, and designing flowcharts, all stored locally in an encrypted, password-protected database. It is built with Python and Tkinter and has no server or internet dependency.
![alt text](frontend/data/tarizzlogo.ico)
**Table of Contents**
- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [File-by-File Explanation](#file-by-file-explanation)
- [Requirements](#requirements)
- [Running from Source](#running-from-source)
- [Installing the Prebuilt Linux Build (Arch Linux)](#installing-the-prebuilt-linux-build-arch-linux)
- [Building Your Own Package (Other Operating Systems)](#building-your-own-package-other-operating-systems)
- [Data Storage and Security](#data-storage-and-security)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [License](#license)

---

## Overview

Tarizz gives each project a hierarchical structure of folders, subpages, and flowcharts. Subpages are rich-text documents with font, size, and style control; flowcharts are node-and-connector diagrams; and both live inside a project you can export to PDF. All content is encrypted at rest behind a single-user login, and everything runs locally with SQLite as the storage engine, so no account, server, or network access is required to use the application.

---

## Features

- **Project dashboard** — create, rename, delete, and reorder projects as draggable cards.
- **Hierarchical structure** — organize each project into folders, subpages, and flowcharts, nested arbitrarily.
- **Rich text editing** — bold, italic, underline, and highlight, plus independent font family and font size control.
  - Formatting can be applied to a selection, or set with nothing selected so that subsequently typed text uses it.
  - The font family list is generated from the fonts actually installed on the machine running Tarizz, so every option in the dropdown is guaranteed to render.
- **Code blocks** — text wrapped in triple single quotes (`'''like this'''`) is automatically styled as a code block, with a choice of nine color themes (GitHub Dark, Monokai, Dracula, Nord, Solarized, One Dark, Material, Tomorrow, Light).
- **Media embedding** — insert images, videos, and documents (PDF/DOC/DOCX/TXT) directly into a subpage. Images and PDFs get generated thumbnails, videos get a play button that opens the system's default player, and all media can be downloaded back out.
- **Flowchart editor** — a dedicated canvas for building diagrams with rectangles, ovals, diamonds, lines, and arrows, with pan, zoom, and PNG export.
- **PDF export** — export an entire project (its tree structure, subpage content, and flowcharts rendered as images) to a single PDF document.
- **Autosave** — subpages and flowcharts save automatically after a short pause in typing/editing, and also on losing focus.
- **Encrypted local storage** — a single-user login protects an AES-256-GCM encrypted SQLite database with a scrypt-derived key; there is no cloud sync and no external account.

---

## Project Structure

```
Tarizz/
├── LICENSE
├── README.md
├── get-pip.py
└── frontend/
    ├── main.py                       Application entry point
    ├── project_manager.py            Project tree, subpage editor UI, toolbar
    ├── text_formatter.py             Font/size/bold/italic/underline/highlight logic
    ├── codeblockhandler_updated.py   Code block detection and theming
    ├── simple_text_editor.py         Standalone text editor widget
    ├── flowchart.py                  Flowchart canvas editor
    ├── project_export.py             Project-to-PDF export
    ├── backend/
    │   ├── __init__.py
    │   ├── database.py               SQLite schema and data access layer
    │   ├── auth_manager.py           Compatibility wrapper around auth_manager_simple
    │   ├── auth_manager_simple.py    Login/registration/password-reset logic
    │   ├── auth_ui.py                Login/registration Tkinter screens
    │   └── crypto_engine.py          AES-256-GCM encryption, scrypt key derivation
    └── data/
        └── tarizzlogo.ico            Application icon
```

At runtime, Tarizz also creates a per-user data directory outside the repository (see [Data Storage and Security](#data-storage-and-security)) — this is where the actual database, media files, and login credentials are kept, not inside the project folder.

---

## File-by-File Explanation

### `frontend/main.py`
Application entry point. Sets up the per-user data directory, runs the login/registration gate through `AuthManager`, unlocks the encrypted database on success, and then launches `ProjectDashboard` — the card-based grid of projects shown after login.

### `frontend/project_manager.py`
The largest module. Renders the project's folder/subpage/flowchart tree, opens the subpage text editor with its formatting toolbar (font family, font size, bold/italic/underline/highlight buttons), handles inserting and rendering media, and drives autosave for whichever editor is currently open.

### `frontend/text_formatter.py`
Implements text formatting as a set of composable Tkinter text tags, so bold, italic, underline, highlight, font family, and font size can all be layered on the same text without one resetting another. Also implements the "sticky" typing format: choosing a font/size/style with no text selected applies it to whatever is typed next, until the cursor moves elsewhere.

### `frontend/codeblockhandler_updated.py`
Scans subpage text for content wrapped in triple single quotes and applies one of nine color themes to it, styling it like a code block (monospace font, background color, margins).

### `frontend/simple_text_editor.py`
A simpler, self-contained Tkinter text editor widget with its own hotkeys and code-block detection, used as the underlying text widget for a subpage editor instance.

### `frontend/flowchart.py`
A canvas-based diagram editor: rectangles, ovals, diamonds, lines, and arrows can be drawn, moved, labeled, and deleted, with pan and zoom controls and PNG export. Flowcharts autosave the same way subpages do.

### `frontend/project_export.py`
Walks a project's full tree — folders, subpages, and flowcharts — and renders it into a single PDF document using ReportLab, including subpage text formatting and flowcharts converted to images.

### `frontend/backend/database.py`
The SQLite data access layer. Defines the schema (`projects`, `nodes`, `content`, `media` tables) and every read/write function the rest of the application calls — creating and deleting nodes, saving and loading subpage content, and tracking embedded media.

### `frontend/backend/auth_manager.py`
A thin compatibility wrapper that exposes `auth_manager_simple.SimpleAuthManager` as `AuthManager`.

### `frontend/backend/auth_manager_simple.py`
Single-user authentication. On account creation, a random 256-bit data key is generated and encrypted twice — once under a key derived from the user's password, once under a key derived from their security-question answer — so a password reset does not lock the user out of their existing data. Also handles login attempt limiting with a temporary lockout.

### `frontend/backend/auth_ui.py`
The Tkinter screens for logging in, registering, and resetting a password, shown before the main dashboard appears.

### `frontend/backend/crypto_engine.py`
Low-level cryptography: AES-256-GCM authenticated encryption/decryption, and scrypt-based key derivation from a password or security answer.

### `frontend/data/tarizzlogo.ico`
The application window/taskbar icon.

### `get-pip.py`
The standard `pip` bootstrap script, provided for environments that don't already have `pip` available.

---

## Requirements

- Python 3.9 or newer, with Tkinter available (bundled with most Python installers; on Linux it is usually a separate package — see [Running from Source](#running-from-source) below).
- The following third-party Python packages:
  - `pillow`
  - `opencv-python`
  - `pymupdf`
  - `reportlab`
  - `cryptography`

There is no `requirements.txt` in this repository at the moment; install the packages above directly, or generate your own `requirements.txt` from them.

---

## Running from Source

```bash
git clone https://github.com/VarunVashisth/Tarizz.git
cd Tarizz/frontend

pip install pillow opencv-python pymupdf reportlab cryptography

python main.py
```

On first launch you will be asked to create an account (username, password, and a security question used for password recovery). This creates the encrypted local database described below — there is no external server involved.

If `tkinter` is missing:

```bash
# Debian / Ubuntu
sudo apt-get install python3-tk

# Arch Linux
sudo pacman -S tk

# Fedora
sudo dnf install python3-tkinter

# macOS (Homebrew Python)
brew install python-tk
```

---
##Windows
just download the installer and run it or package it yourself and run it

## Installing the Prebuilt Linux Build (Arch Linux)

If you have a PyInstaller-built binary of Tarizz (a single executable file, typically named `Tarizz` or `Tarizz.bin`), it does not run by default because Linux does not mark downloaded files as executable. You need to grant execute permission and, optionally, register it with your application menu.

### Step 1 — Make the binary executable

Place the binary somewhere permanent, for example `/opt/tarizz/Tarizz` or `~/.local/bin/Tarizz`, then:

```bash
chmod +x /path/to/Tarizz
```

You can now run it directly:

```bash
/path/to/Tarizz
```

### Step 2 — Add it to your application menu with a `.desktop` file

Linux desktop environments (GNOME, KDE, XFCE, and others) discover applications through `.desktop` files, which follow the freedesktop.org Desktop Entry specification. Create one for Tarizz:

```bash
mkdir -p ~/.local/share/applications
nano ~/.local/share/applications/tarizz.desktop
```

Paste in the following, adjusting the paths to match where you placed the binary and the icon:

```ini
[Desktop Entry]
Name=Tarizz
Comment=Project management and documentation tool
Exec=/path/to/Tarizz
Icon=/path/to/Tarizz/data/tarizzlogo.ico
Terminal=false
Type=Application
Categories=Office;Development;
```

Save the file, then make it executable and refresh the desktop database:

```bash
chmod +x ~/.local/share/applications/tarizz.desktop
update-desktop-database ~/.local/share/applications
```

Tarizz should now appear in your application launcher/menu like any other installed application. This `.desktop` approach works the same way on essentially every Linux distribution, not just Arch — the difference on other distributions is only in how you'd install dependencies via their own package manager if building from source instead of using the binary.

---

## Building Your Own Package (Other Operating Systems)

The PyInstaller build referenced above is Linux-specific. If you are on Windows, macOS, or a different Linux architecture, clone the repository and package it yourself:

```bash
git clone https://github.com/VarunVashisth/Tarizz.git
cd Tarizz/frontend

pip install pillow opencv-python pymupdf reportlab cryptography pyinstaller

pyinstaller --noconfirm --windowed --onefile --name Tarizz --icon data/tarizzlogo.ico main.py
```

The resulting executable will be created under `dist/`. From there:

- **Windows** — run `dist\Tarizz.exe` directly, or create a shortcut to it.
- **macOS** — run `dist/Tarizz`, or target a `.app` bundle if you want a native macOS application; you may need to allow the app in System Settings → Privacy & Security the first time, since it is unsigned.
- **Linux (any distribution/architecture)** — follow the same `chmod +x` and `.desktop` steps described above, adjusted to your distribution's package manager for any missing system libraries.

---

## Data Storage and Security

Tarizz does not store your data inside the cloned repository. On first run it creates a per-user data directory:

- **Windows** — `%APPDATA%\Tarizz`
- **Linux/macOS** — `~/.tarizz`

Inside that directory:

- `auth.json` — your username, password hash, security question, and the doubly-wrapped data encryption key. Your plaintext password is never stored.
- `tarizz.db` — the SQLite database holding your projects, folder/subpage/flowchart structure, and text content, with sensitive fields encrypted using AES-256-GCM under a key derived from your password via scrypt.
- `media/` — embedded images, videos, and documents.

Because everything is local, backing up Tarizz means backing up this one directory. There is no built-in cloud sync.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+B` | Toggle bold |
| `Ctrl+I` | Toggle italic |
| `Ctrl+U` | Toggle underline |
| `Ctrl+H` / `Ctrl+Shift+H` | Toggle highlight |

Font family, font size, and the bold/italic/underline/highlight actions are also available as toolbar buttons in the subpage editor, and work the same way whether triggered from the keyboard or the toolbar.

---

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.
