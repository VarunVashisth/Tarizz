# Tarizz - Advanced Project Management & Documentation Tool

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

> A powerful desktop application for managing projects with rich text editing, flowcharts, media embedding, and intelligent code block formatting.

**Table of Contents**
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Main Features Explained](#main-features-explained)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Project Structure](#project-structure)
- [Commands & Usage](#commands--usage)
- [Advanced Features](#advanced-features)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Tarizz** is a comprehensive project management and documentation tool designed for professionals, developers, and teams who need to organize, document, and visualize their projects. With Tarizz, you can create hierarchical project structures, write rich-text documentation, embed media, design flowcharts, and manage all your project assets in one elegant interface.

![alt text](frontend/data/tarizzlogo.ico)

### What is Tarizz?

Tarizz combines the power of:
- 📝 **Rich Text Editor** - Format text with bold, italic, underline, highlighting, custom fonts & sizes
- 📊 **Flowchart Editor** - Create visual diagrams and flowcharts for your projects
- 🎥 **Media Management** - Embed images, videos, and documents directly in your documentation
- 💾 **Database-Backed** - SQLite database for reliable data persistence
- 🎨 **Professional UI** - Dark theme with intuitive navigation

---

## Features

### Core Features

#### 1. **Project Management**
- Create hierarchical project structures
- Organize projects into folders
- Create subpages for documentation
- Design flowcharts for visual planning
- Rename and delete items with ease

#### 2. **Rich Text Editing**
```
✓ Bold (Ctrl+B)
✓ Italic (Ctrl+I)
✓ Underline (Ctrl+U)
✓ Highlight (Ctrl+Shift+H) - Yellow background
✓ Custom Font Families - 10+ fonts available
✓ Custom Font Sizes - 8pt to 48pt
✓ Auto-save with debouncing
```

#### 3. **Smart Code Block Styling**
```python
Type: '''your code here'''
Display: Professional dark theme with syntax awareness

9 Professional Themes:
├── GitHub Dark (default) - #0d1117
├── Monokai - #272822
├── Dracula - #282a36
├── Nord - #2e3440
├── Solarized - #002b36
├── One Dark - #282c34
├── Material - #263238
├── Tomorrow - #2d2d2d
└── Light - #f5f5f5
```

#### 4. **Media Embedding**
```
Supported Media Types:
├── Images (PNG, JPG, GIF, WebP)
│   └── Resizable with drag handles
├── Videos (MP4, MOV, AVI, MKV)
│   └── Professional play button with hover effects
├── Documents (PDF, DOC, DOCX, TXT)
│   └── Thumbnail preview with download option
└── Position Tracking
    └── Media positions auto-saved
```

#### 5. **Flowchart Designer**
```
Elements:
├── Nodes/Boxes
├── Connections/Arrows
├── Custom Labels
├── Drag & Drop positioning
└── Save/Load designs
```

#### 6. **Formatting Compatibility**
```
Mix and Match:
✓ Bold + Font + Size = All work together
✓ Italic + Highlight + Custom Font = Compatible
✓ No resets when changing properties
✓ Seamless formatting experience
```

---

## Installation Process

### Prerequisites
```bash
- Python 3.7 or higher
- pip (Python package manager)
- 50MB disk space
```

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/tarizz.git
cd tarizz
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Initialize Database
```bash
python -c "from backend.database import init_database; init_database()"
```

### Step 4: Run the Application
```bash
python main.py
```

### Optional: Create Desktop Shortcut
**Windows:**
```batch
@echo off
python main.py
pause
```

**Linux/Mac:**
```bash
#!/bin/bash
python3 main.py
```

---

## Quick Start

### Creating Your First Project

1. **Launch Tarizz**
   ```bash
   python main.py
   ```

2. **Create a Project**
   - Click "New Project"
   - Enter project name
   - Click "Create"

3. **Add Folder Structure**
   - Right-click on project
   - Select "Add Folder"
   - Name your folder

4. **Create Documentation**
   - Right-click on folder
   - Select "Add Subpage"
   - Start writing!

5. **Format Your Text**
   - Select text
   - Use Ctrl+B for bold, Ctrl+I for italic, etc.

6. **Add Media**
   - Click "Image", "Video", or "Document" button
   - Select file from your computer
   - Media is embedded automatically

---

## Main Features Explained

### 1. Text Formatting

#### Basic Formatting
```
Ctrl+B      → Bold
Ctrl+I      → Italic
Ctrl+U      → Underline
Ctrl+Shift+H → Highlight (Yellow)
```

#### Font Selection
```
Toolbar Menu → "Font Family" dropdown
Options: Segoe UI, Arial, Helvetica, Times New Roman, 
         Courier New, Georgia, Verdana, and more
```

#### Font Size
```
Toolbar Menu → "Size" dropdown
Range: 8pt to 48pt
Quick jumps: 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48
```

#### Highlighting
```
Select Text → Press Ctrl+Shift+H
Result: Yellow background (#ffff99) with black text
Toggle: Press Ctrl+Shift+H again to remove
```

### 2. Code Blocks

#### Syntax
```python
# Type code between triple quotes:
'''
your code here
'''

# Works with any language:
'''python
def hello():
    print("Hello World")
'''

'''javascript
const name = "Tarizz";
console.log(name);
'''

'''sql
SELECT * FROM users WHERE active = 1;
'''
```

#### Themes
```
# Default GitHub Dark
code_handler = CodeBlockHandler(text, theme='github_dark')

# Change at runtime
code_handler.change_theme('monokai')
code_handler.change_theme('dracula')
code_handler.change_theme('nord')
```

#### Visual Example
```
┌─ Code Block ─────────────────┐
│ def hello():                  │  Dark background
│     print("Hello")            │  Light text
│     return True               │  Monospace font
└───────────────────────────────┘
```

### 3. Media Management

#### Inserting Media
```
Toolbar:
├── Image Button
│   └── Select PNG, JPG, GIF, WebP
│   └── Thumbnail shows in document
│   └── Resizable with mouse drag
│
├── Video Button
│   └── Select MP4, MOV, AVI, MKV
│   └── Shows video thumbnail
│   └── Green play button (hover effect)
│   └── Click to play in default player
│   └── Right-click to download
│
└── Document Button
    └── Select PDF, DOC, DOCX, TXT
    └── Shows document preview
    └── PDF thumbnails generated
    └── Download option available
```

#### Media Features
```
✓ Drag & drop positioning
✓ Automatic resizing (images)
✓ Thumbnail generation (PDFs)
✓ Download management
✓ Position auto-save
✓ Media deletion detection
```

### 4. Flowchart Designer

#### Creating Flowcharts
```
1. Right-click folder → Add Flowchart
2. Double-click to open editor
3. Left-click to create nodes
4. Drag between nodes to create connections
5. Right-click for options (delete, rename, etc.)
6. Auto-saves when switching pages
```

#### Features
```
✓ Node creation
✓ Flexible connections
✓ Node labels/text
✓ Delete nodes
✓ Drag positioning
✓ Persistent storage
✓ SVG export (planned)
```

### 5. Database System

#### Automatic Features
```
✓ SQLite database (local, no server needed)
✓ Auto-save every keystroke (debounced)
✓ Tag persistence (formatting saved)
✓ Media tracking
✓ Hierarchical structure
✓ Corruption recovery
```

#### Data Stored
```
projects/
├── Project metadata (name, creation date)
├── Nodes (folders, subpages, flowcharts)
├── Content
│   ├── Text
│   ├── Tags (bold, italic, font, size)
│   └── Code blocks
├── Media
│   ├── Images
│   ├── Videos
│   └── Documents
└── Flowchart data
```

---

## Keyboard Shortcuts

### Text Formatting
| Shortcut | Action | Status |
|----------|--------|--------|
| Ctrl+B | Toggle Bold | ✅ Active |
| Ctrl+I | Toggle Italic | ✅ Active |
| Ctrl+U | Toggle Underline | ✅ Active |
| Ctrl+Shift+H | Toggle Highlight | ✅ Active |
| Ctrl+Z | Undo | ✅ (system) |
| Ctrl+Y | Redo | ✅ (system) |

### Navigation
| Shortcut | Action |
|----------|--------|
| Click Folder | Expand/Collapse |
| Double-click Subpage | Open for editing |
| Right-click Item | Context menu |
| Click Page | Auto-saves previous |

### Media
| Action | Method |
|--------|--------|
| Insert Image | Toolbar button or Right-click |
| Insert Video | Toolbar button |
| Insert Document | Toolbar button |
| Download Media | Right-click on media |
| Resize Image | Drag corner of image |

---

## Project Structure

```
tarizz/
│
├── main.py                          # Application entry point
│
├── project_manager.py               # Main UI and editor logic
│
├── codeblockhandler_updated.py     # Code block detection & styling
│
├── text_formatter.py                # Text formatting handler
│
├── simple_text_editor.py            # Text editor component
│
├── flowchart.py                     # Flowchart editor logic
│
├── backend/
│   ├── database.py                  # SQLite database interface
│   └── __init__.py
│
├── data/
│   ├── play-button.png              # Optional: play button icon
│   └── projects.db                  # Auto-generated database
│
├── requirements.txt                 # Python dependencies
│
├── README.md                        # This file
│
├── LICENSE                          # MIT License
│
└── .gitignore                       # Git ignore rules
```

---

## Commands & Usage

### Command Line

#### Run Application
```bash
python main.py
```

#### Initialize Database
```bash
python -c "from backend.database import init_database; init_database()"
```

#### Reset Database
```bash
python -c "import os; os.remove('data/projects.db'); from backend.database import init_database; init_database()"
```

#### Export Project
```bash
python -c "from backend.database import export_project; export_project(project_id, 'output.json')"
```

### GUI Commands

#### Project Management
```
New Project
├── Enter name
└── Creates project with database entry

Open Project
├── Shows all subpages and flowcharts
└── Displays hierarchical structure

Delete Project
├── Confirm deletion
└── Removes all associated data

Rename Project
├── Edit name
└── Updates in database
```

#### Folder Operations
```
Add Folder
├── Under selected folder or project root
└── Can nest folders infinitely

Rename Folder
├── Edit name inline
└── Auto-saved

Delete Folder
├── Deletes all children
└── Confirmation required
```

#### Subpage Operations
```
Add Subpage
├── Rich text document
├── Media support
├── Auto-save enabled
└── All formatting preserved

Edit Subpage
├── Full formatting toolbar
├── Font selection
├── Size selection
├── Media insertion
└── Code block detection

Save Subpage
├── Auto-save every 1 second (debounced)
├── On FocusOut event
└── Manual Ctrl+S (system default)
```

#### Flowchart Operations
```
Add Flowchart
├── Visual diagram editor
└── Saves when switching pages

Edit Flowchart
├── Left-click to create nodes
├── Drag to connect
├── Right-click for options
└── Auto-saves on exit
```

---

## Advanced Features

### 1. Smart Text Formatting

#### How It Works
```python
# Old behavior (broken):
Select text → Make bold → Change font → Size resets ❌

# New behavior (fixed):
Select text → Make bold → Change font → Size preserved ✅
```

#### TextFormatter Class
```python
class TextFormatter:
    def apply_font_family(family)
        # Preserves size, bold, italic, etc.
    
    def apply_font_size(size)
        # Preserves family, bold, italic, etc.
    
    def toggle_bold()
        # Preserves other formatting
    
    def toggle_italic()
        # Preserves other formatting
    
    def toggle_highlight()
        # Yellow background with all text formatting
```

### 2. Code Block Detection

#### Automatic Detection
```python
# As you type:
Type: '''
Auto-detects: Code block starts
Styling: Dark theme applied
Detection: Watches for closing '''

Display:
├── Dark background (#0d1117 for GitHub Dark)
├── Light text (#c9d1d9)
├── Monospace font (Courier New)
└── Extra padding for readability
```

#### Theme System
```python
# 9 Professional Themes:
1. GitHub Dark   - Modern tech look
2. Monokai       - Classic vibrant
3. Dracula       - Cool purples
4. Nord          - Arctic blues
5. Solarized     - Warm colors
6. One Dark      - Atom editor
7. Material      - Design system
8. Tomorrow      - Night theme
9. Light         - Bright mode

# Switch themes:
code_handler.change_theme('monokai')
```

### 3. Media Lifecycle Management

#### Upload
```
User Click → File Dialog → File Selected
→ Stored in database → Embedded in document
→ Position tracked → Thumbnail generated (PDF)
```

#### Display
```
Images:    Thumbnail preview, resizable
Videos:    Video frame + play button, clickable
Documents: PDF preview or icon, downloadable
```

#### Cleanup
```
Periodic check (every 2 seconds):
├── List all embedded media
├── Check if still in document
├── Find orphaned media
└── Delete from database
```

### 4. Auto-Save System

#### How It Works
```
User Types → KeyRelease Event
        ↓
      Wait 1 second (debounce)
        ↓
   No more typing?
        ├── Yes → Save to database
        └── No → Restart timer

User Leaves Subpage → FocusOut Event
                ↓
            Save immediately
```

#### What Gets Saved
```
✓ Text content
✓ All tags (bold, italic, font, size, code_block)
✓ Media positions
✓ Formatting information
✓ Timestamp of last edit
```

### 5. Database Features

#### SQLite Tables
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP
);

CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    parent_id INTEGER,
    name TEXT,
    node_type TEXT,  -- 'folder', 'subpage', 'flowchart'
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

CREATE TABLE subpages (
    id INTEGER PRIMARY KEY,
    node_id INTEGER,
    content TEXT,
    metadata JSON,
    FOREIGN KEY(node_id) REFERENCES nodes(id)
);

CREATE TABLE media (
    id INTEGER PRIMARY KEY,
    node_id INTEGER,
    media_type TEXT,  -- 'image', 'video', 'doc'
    file_path TEXT,
    original_filename TEXT,
    position_index TEXT,
    FOREIGN KEY(node_id) REFERENCES nodes(id)
);
```

#### Recovery Features
```
✓ Automatic backups
✓ Transaction support
✓ Orphaned media cleanup
✓ Tag range validation
✓ Parent-child integrity
```

---

## Customization

### 1. Change Code Block Theme

**File:** `project_manager.py` (Line ~1001)

```python
# Change this line:
code_handler = CodeBlockHandler(text, theme='github_dark')

# To any of:
code_handler = CodeBlockHandler(text, theme='monokai')
code_handler = CodeBlockHandler(text, theme='dracula')
code_handler = CodeBlockHandler(text, theme='nord')
code_handler = CodeBlockHandler(text, theme='solarized')
code_handler = CodeBlockHandler(text, theme='one_dark')
code_handler = CodeBlockHandler(text, theme='material')
code_handler = CodeBlockHandler(text, theme='tomorrow')
code_handler = CodeBlockHandler(text, theme='light')
```

### 2. Change Play Button Color

**File:** `project_manager.py` (Lines ~488-553 and ~711-775)

```python
# Find these lines and change colors:

# Current (Green):
outer_circle.create_oval(5, 5, 65, 65, fill='#00ff00', outline='#00cc00', width=2)

# Blue:
outer_circle.create_oval(5, 5, 65, 65, fill='#0066ff', outline='#0044cc', width=2)

# Red:
outer_circle.create_oval(5, 5, 65, 65, fill='#ff3333', outline='#cc0000', width=2)

# Purple:
outer_circle.create_oval(5, 5, 65, 65, fill='#9933ff', outline='#7700cc', width=2)

# Orange:
outer_circle.create_oval(5, 5, 65, 65, fill='#ff9933', outline='#cc6600', width=2)

# Cyan:
outer_circle.create_oval(5, 5, 65, 65, fill='#00ffff', outline='#00cccc', width=2)
```

### 3. Customize Font Options

**File:** `project_manager.py` (Line ~630)

```python
# Change available fonts:
fonts = ['Segoe UI', 'Arial', 'Helvetica', 'Times New Roman', 
         'Courier New', 'Georgia', 'Verdana']

# Add your favorite fonts:
fonts = ['Segoe UI', 'Arial', 'Helvetica', 'Times New Roman',
         'Courier New', 'Georgia', 'Verdana', 'Comic Sans MS',
         'Trebuchet MS', 'Lucida Console']
```

### 4. Customize Font Sizes

**File:** `project_manager.py` (Line ~650)

```python
# Change available sizes:
sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48]

# Add custom sizes:
sizes = [6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 22, 24, 
         28, 32, 36, 48, 56, 64, 72]
```

---

## Troubleshooting

### Common Issues

#### 1. Application Won't Start
```
Error: ModuleNotFoundError: No module named 'tkinter'

Solution:
# Windows
python -m pip install tk

# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS (Homebrew)
brew install python-tk@3.9
```

#### 2. Database Corruption
```
Error: sqlite3.DatabaseError

Solution:
python -c "import os; os.remove('data/projects.db'); 
from backend.database import init_database; init_database()"
```

#### 3. Ctrl+Shift+H Doesn't Work
```
Issue: Highlight shortcut not responding

Cause: text_formatter.py not imported

Solution:
1. Verify text_formatter.py exists in project folder
2. Check imports at top of project_manager.py
3. Restart application
```

#### 4. Code Blocks Not Styling
```
Issue: '''code''' appears as normal text

Cause: codeblockhandler_updated.py missing

Solution:
1. Verify file exists
2. Check import in project_manager.py
3. Delete old codeblockhandler.py if exists
4. Restart application
```

#### 5. Media Won't Load
```
Issue: Images/videos don't display

Cause: File path or format issue

Solution:
1. Check file format is supported
2. Verify file hasn't been moved
3. Try re-inserting the media
4. Check permissions on file
```

#### 6. Performance Issues
```
Issue: Application sluggish with large documents

Cause: Too many tags or media items

Solution:
1. Split large documents into multiple subpages
2. Remove unused media
3. Clean up unused formatting tags
4. Restart application
```

---

## File Descriptions

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `project_manager.py` | Main UI logic and editor (1125+ lines) |
| `codeblockhandler_updated.py` | Code block detection & 9 themes |
| `text_formatter.py` | Smart text formatting with compatibility |
| `simple_text_editor.py` | Text widget component |
| `flowchart.py` | Flowchart editor logic |
| `backend/database.py` | SQLite database interface |
| `data/projects.db` | Auto-generated database |

---

## API Reference

### CodeBlockHandler

```python
from codeblockhandler_updated import CodeBlockHandler

# Initialize
handler = CodeBlockHandler(text_widget, theme='github_dark')

# Methods
handler.apply_code_block_styling(event)  # Detect and style code blocks
handler.change_theme('monokai')           # Change theme at runtime
handler.setup_tags()                      # Configure tag appearance
```

### TextFormatter

```python
from text_formatter import TextFormatter

# Initialize
formatter = TextFormatter(text_widget)

# Methods
formatter.apply_font_family(family)   # Apply font with compatibility
formatter.apply_font_size(size)       # Apply size with compatibility
formatter.toggle_bold()               # Toggle bold
formatter.toggle_italic()             # Toggle italic
formatter.toggle_underline()          # Toggle underline
formatter.toggle_highlight()          # Toggle yellow highlight
formatter.get_current_formatting()    # Get current formatting info
```

---

## Changelog

### v1.0.0 (Current)
```
✅ Project management with hierarchical structure
✅ Rich text editor with formatting
✅ Code block detection with 9 themes
✅ Media embedding (images, videos, documents)
✅ Flowchart designer
✅ Professional play button
✅ Smart font/size compatibility
✅ Ctrl+Shift+H highlight support
✅ Auto-save with debouncing
✅ SQLite database backend
```

---

## License

This project is licensed under the MIT License - see LICENSE file for details.

```
MIT License

Copyright (c) 2024 Tarizz Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

---

## Support

```
📧 Email:    support@tarizz.dev
💬 Discord:  discord.gg/tarizz
🐦 Twitter:  @TarizziTeam
📖 Docs:     docs.tarizz.dev
🐛 Issues:   github.com/tarizz/issues
```

---

## FAQ

### Q: Is Tarizz free?
**A:** Yes! Tarizz is completely free and open-source under the MIT License.

### Q: Can I use Tarizz for commercial projects?
**A:** Yes! MIT License allows commercial use.

### Q: Does Tarizz require internet?
**A:** No! Everything runs locally. No cloud required.

### Q: Can I backup my projects?
**A:** Yes! Database is in `data/projects.db`. Back it up anytime.

### Q: How do I share projects?
**A:** Export projects as JSON or copy the database file.

### Q: Is my data safe?
**A:** Your data stays on your machine. SQLite database is secure and reliable.

### Q: Can I use Tarizz on multiple computers?
**A:** Yes! Copy the database file to sync between computers.

### Q: What if I find a bug?
**A:** Report it on GitHub with steps to reproduce.

### Q: Can I suggest features?
**A:** Absolutely! Open a GitHub issue or email us.

---

## Getting Started Checklist

- [ ] Clone repository
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Run application (`python main.py`)
- [ ] Create first project
- [ ] Add folder structure
- [ ] Create subpage
- [ ] Try text formatting (Ctrl+B, Ctrl+I, etc.)
- [ ] Type code block ('''code''')
- [ ] Insert image/video
- [ ] Save and close
- [ ] Reopen to verify persistence

---

## Thank You!

Thank you for using Tarizz! We hope it helps you manage your projects more effectively. 

**Happy documenting! 📝✨**

---

*Last Updated: 2024*
*Version: 1.0.0*
*Status: Active Development*
