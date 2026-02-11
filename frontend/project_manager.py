# project_manager.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox , filedialog
from simple_text_editor import create_text_editor
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import (
    create_node, get_nodes, get_all_nodes_for_project,
    rename_node, delete_node,
    save_subpage, load_subpage,
    save_media, get_media_for_node
)
from flowchart import FlowchartEditor
from PIL import Image, ImageTk

def create_project_manager(parent, project_data=None, parent_card=None):
    """
    Create the project manager UI.
    
    project_data: dict with 'id' key containing the project_id from database
    parent_card: reference to the ProjectCard instance (for saving)
    """
    class ProjectManager:
        def __init__(self, parent, project_data, parent_card):
            self.root = parent
            self.project_data = project_data if project_data is not None else {}
            self.project_id = self.project_data.get('id')  # Database project ID
            self.parent_card = parent_card
            
            if not self.project_id:
                messagebox.showerror("Error", "Invalid project - no database ID")
                return

            # Sidebar
            self.sidebar = ttk.Frame(self.root, width=250)
            self.sidebar.pack(side='left', fill='y')
            self.sidebar.configure(style='Sidebar.TFrame')

            style = ttk.Style()
            style.theme_use('default')
            style.configure('Sidebar.TFrame', background='#222222')
            style.configure('Sidebar.Treeview', background='#222222', fieldbackground='#222222', 
                          borderwidth=0, foreground='#cccccc', relief='flat')
            style.map('Sidebar.Treeview',
                     background=[('selected', '#333333')],
                     foreground=[('selected', '#ffffff')])

            self.tree = ttk.Treeview(self.sidebar, style='Sidebar.Treeview', show='tree')
            self.tree.pack(fill='both', expand=True)
            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

            # Buttons
            btn_style = {
                'bg': '#222222', 'fg': '#cccccc',
                'activebackground': '#333333', 'activeforeground': '#ffffff',
                'relief': 'flat', 'bd': 0,
                'font': ('Segoe UI', 10),
                'highlightthickness': 0,
                'padx': 12, 'pady': 6,
                'cursor': 'hand2'
            }
            
            btn_frame = tk.Frame(self.sidebar, bg='#222222')
            btn_frame.pack(fill='x', pady=4)
            
            tk.Button(btn_frame, text="Add Folder", command=self.add_folder, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Add Subpage", command=self.add_subpage, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Add Flowchart", command=self.add_flowchart, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Rename", command=self.rename_item, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Delete", command=self.delete_item, **btn_style).pack(fill='x', pady=2)

            # Editor container
            self.editor_container = ttk.Frame(self.root)
            self.editor_container.pack(side='left', fill='both', expand=True)

            self.current_editor = None
            self.current_editor_frame = None
            self.current_node_id = None  # Track which node is open
            
            # Build tree from database
            self.root_item = self.tree.insert("", "end", text="Project", open=True)
            self.node_id_to_tree_id = {}  # Map database node_id to tree item_id
            self.tree_id_to_node_id = {}  # Reverse mapping
            self.load_tree()

        def load_tree(self):
            """Load the entire tree structure from database"""
            # Clear existing tree items except root
            for child in self.tree.get_children(self.root_item):
                self.tree.delete(child)
            self.node_id_to_tree_id.clear()
            self.tree_id_to_node_id.clear()
            
            # Get all nodes
            all_nodes = get_all_nodes_for_project(self.project_id) if self.project_id else []
            
            # Build a parent->children map
            children_map = {}
            for node in all_nodes:
                parent_id = node['parent_id']
                if parent_id not in children_map:
                    children_map[parent_id] = []
                children_map[parent_id].append(node)
            
            # Recursive tree builder
            def add_children(parent_tree_id, parent_node_id):
                if parent_node_id not in children_map:
                    return
                for node in children_map[parent_node_id]:
                    tree_id = self.tree.insert(parent_tree_id, "end", text=node['name'], open=True)
                    self.node_id_to_tree_id[node['id']] = tree_id
                    self.tree_id_to_node_id[tree_id] = node['id']
                    # Recursively add children
                    add_children(tree_id, node['id'])
            
            # Start from root nodes (those with parent_id = None)
            add_children(self.root_item, None)

        def get_selected_node_info(self):
            """Get database node info for selected tree item"""
            selected = self.tree.selection()
            if not selected or selected[0] == self.root_item:
                return None, None
            
            tree_id = selected[0]
            node_id = self.tree_id_to_node_id.get(tree_id)
            if not node_id:
                return None, None
            
            # Fetch node from database
            from backend.database import _db_instance
            conn = _db_instance._connect()
            try:
                node = conn.execute("SELECT * FROM nodes WHERE id=?;", (node_id,)).fetchone()
                return dict(node) if node else None, tree_id
            finally:
                conn.close()

        def add_folder(self):
            """Add a folder node"""
            selected = self.tree.selection()
            parent_tree_id = selected[0] if selected else self.root_item
            parent_node_id = self.tree_id_to_node_id.get(parent_tree_id)  # None if root
            
            # Check if parent allows children
            if parent_node_id:
                node_info, _ = self.get_selected_node_info()
                if node_info and node_info['node_type'] in ('subpage', 'flowchart'):
                    messagebox.showerror("Error", 
                        f"Cannot add folder under a {node_info['node_type']}.\n"
                        "Subpages and flowcharts cannot have children.")
                    return
            
            name = simpledialog.askstring("Folder Name", "Enter folder name:")
            if not name:
                return
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'folder', name)
                # Add to tree
                tree_id = self.tree.insert(parent_tree_id, "end", text=name, open=True)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        def add_subpage(self):
            """Add a subpage node"""
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a folder first")
                return
            
            parent_tree_id = selected[0]
            if parent_tree_id == self.root_item:
                parent_node_id = None
            else:
                parent_node_id = self.tree_id_to_node_id.get(parent_tree_id)
            
            # Check if parent allows children
            if parent_node_id:
                node_info, _ = self.get_selected_node_info()
                if node_info and node_info['node_type'] in ('subpage', 'flowchart'):
                    messagebox.showerror("Error",
                        f"Cannot add subpage under a {node_info['node_type']}.\n"
                        "Subpages and flowcharts cannot have children.")
                    return
            
            name = simpledialog.askstring("Subpage Name", "Enter subpage name:")
            if not name:
                return
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'subpage', name)
                # Add to tree
                tree_id = self.tree.insert(parent_tree_id, "end", text=name)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
                # Initialize empty content
                save_subpage(db_node_id, "")
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        def add_flowchart(self):
            """Add a flowchart node"""
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a folder first")
                return
            
            parent_tree_id = selected[0]
            if parent_tree_id == self.root_item:
                parent_node_id = None
            else:
                parent_node_id = self.tree_id_to_node_id.get(parent_tree_id)
            
            # Check if parent allows children
            if parent_node_id:
                node_info, _ = self.get_selected_node_info()
                if node_info and node_info['node_type'] in ('subpage', 'flowchart'):
                    messagebox.showerror("Error",
                        f"Cannot add flowchart under a {node_info['node_type']}.\n"
                        "Subpages and flowcharts cannot have children.")
                    return
            
            name = simpledialog.askstring("Flowchart Name", "Enter flowchart name:")
            if not name:
                return
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'flowchart', name)
                tree_id = self.tree.insert(parent_tree_id, "end", text=name)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        def rename_item(self):
            """Rename selected node"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                messagebox.showwarning("Warning", "Please select an item to rename")
                return
            
            old_name = node_info['name']
            new_name = simpledialog.askstring("Rename", f"Enter new name for '{old_name}':")
            if not new_name or new_name == old_name:
                return
            
            rename_node(node_info['id'], new_name)
            self.tree.item(tree_id, text=new_name)

        def delete_item(self):
            """Delete selected node and all children"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                messagebox.showwarning("Warning", "Please select an item to delete")
                return
            
            confirm = messagebox.askyesno("Confirm Delete",
                f"Delete '{node_info['name']}' and all its contents?")
            if not confirm:
                return
            
            delete_node(node_info['id'])
            self.tree.delete(tree_id)
            del self.tree_id_to_node_id[tree_id]
            del self.node_id_to_tree_id[node_info['id']]
            
            # Clear editor if this was open
            if self.current_node_id == node_info['id']:
                if self.current_editor_frame:
                    self.current_editor_frame.destroy()
                self.current_editor = None
                self.current_node_id = None

        def on_tree_select(self, event):
            """Handle tree item selection"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                return
            
            # Save current page before switching
            if self.current_node_id and self.current_editor:
                if node_info['id'] != self.current_node_id:
                   self.save_current_page()
            
            if node_info['node_type'] == 'folder':
                # Folders don't open an editor
                return
            elif node_info['node_type'] == 'flowchart':
                self.open_flowchart_editor(node_info['id'])
            elif node_info['node_type'] == 'subpage':
                self.open_subpage_editor(node_info['id'])

        def open_flowchart_editor(self, node_id: int):
            """Open flowchart editor (not yet implemented with persistence)"""
            if self.current_editor_frame:
                self.current_editor_frame.destroy()
            
            self.current_editor_frame = ttk.Frame(self.editor_container)
            self.current_editor_frame.pack(fill="both", expand=True)
            self.current_editor = FlowchartEditor(self.current_editor_frame)
            self.current_editor.pack(fill="both", expand=True)
            self.current_node_id = node_id

        def open_subpage_editor(self, node_id: int):
            """Open text editor for a subpage"""
            if self.current_editor_frame:
                self.current_editor_frame.destroy()
            
            frame = tk.Frame(self.editor_container, bg='#222222')
            frame.pack(fill='both', expand=True)
            self.current_editor_frame = frame
        
            editor = create_text_editor(parent=frame)
            self.current_editor = editor
            self.current_node_id = node_id
        
            text = editor.text_area
            text.tag_configure('bold', font=(text.cget('font').split()[0], -12, 'bold'))
            text.tag_configure('italic', font=(text.cget('font').split()[0], -12, 'italic'))
            text.tag_configure('underline', underline=True)
            text.tag_configure('highlight', background='#ffff00', foreground='#000000')
            text.tag_configure('code', font='Courier -12', background='#003300', foreground='#00ff00',
                               lmargin1=10, lmargin2=10, rmargin=10)
        
            def toggle_tag(event=None, tag=None):
                try:
                    sel_start = text.index(tk.SEL_FIRST)
                    sel_end = text.index(tk.SEL_LAST)
                    if sel_start and sel_end:
                        current_tags = text.tag_names(sel_start)
                        if tag in current_tags:
                            text.tag_remove(tag, sel_start, sel_end)
                        else:
                            text.tag_add(tag, sel_start, sel_end)
                    return 'break'
                except tk.TclError:
                    return 'break'
        
            text.bind('<Control-b>', lambda e: toggle_tag(e, 'bold'))
            text.bind('<Control-i>', lambda e: toggle_tag(e, 'italic'))
            text.bind('<Control-u>', lambda e: toggle_tag(e, 'underline'))
            text.bind('<Control-Shift-h>', lambda e: toggle_tag(e, 'highlight'))
            text.bind('<Control-Shift-c>', lambda e: toggle_tag(e, 'code'))
        
            # Toolbar code here (your existing toolbar)
        
            # Load content
            dump = load_subpage(node_id)
            if dump:
                text.delete("1.0", "end")
                
                # Handle both old string format and new dict format
                if isinstance(dump, str):
                    content = dump
                    tags_data = {}
                    print("[DEBUG] Loaded legacy string content")
                else:
                    content = dump.get('content', '')
                    tags_data = dump.get('tags', {})
                    print(f"[DEBUG] Loaded dict - content len: {len(content)}")
                
                text.insert("1.0", content)
    
                # Apply tags if present
                for tag_name, ranges_list in tags_data.items():
                    for start, end in ranges_list:
                        try:
                            text.tag_add(tag_name, start, end)
                        except tk.TclError:
                            pass  # ignore invalid indices
                        # Load media
            media_list = get_media_for_node(node_id)
            
            def parse_index(idx):
                if not idx:
                    return (0, 0)
                try:
                    line, char = map(int, idx.split('.'))
                    return line, char
                except:
                    return (0, 0)
                
                        # ───────────────────────────────────────────────
            #   Toolbar — only for inserting NEW media
            # ───────────────────────────────────────────────
            toolbar = tk.Frame(frame, bg='#181818', height=38)
            toolbar.pack(side='top', fill='x', pady=(0, 6))
            toolbar.pack_propagate(False)

            btn_style = {
                'bg': '#252525', 'fg': '#d0d0d0',
                'activebackground': '#353535', 'activeforeground': 'white',
                'relief': 'flat', 'bd': 0,
                'font': ('Segoe UI', 10), 'padx': 14, 'pady': 6,
                'cursor': 'hand2', 'highlightthickness': 0
            }

            def insert_new_media(media_type):
                # File dialog for new insertion
                filetypes = []
                if media_type == 'image':
                    filetypes = [("Images", "*.png *.jpg *.jpeg *.gif *.webp")]
                elif media_type == 'video':
                    filetypes = [("Videos", "*.mp4 *.mov *.avi *.mkv")]
                elif media_type == 'doc':
                    filetypes = [("Documents", "*.pdf *.doc *.docx *.txt")]

                file_path = filedialog.askopenfilename(
                    title=f"Insert {media_type.capitalize()}",
                    filetypes=filetypes + [("All files", "*.*")]
                )

                if not file_path or not os.path.exists(file_path):
                    return

                original_filename = os.path.basename(file_path)
                insert_pos = text.index("insert")

                # Save to DB first
                media_id = save_media(
                    self.current_node_id,
                    media_type,
                    file_path,
                    original_filename,
                    insert_pos
                )

                # Now embed it (copy-paste your widget creation code here)
                label = None

                if media_type == 'image':
                    try:
                        img = Image.open(file_path)
                        img.thumbnail((400, 400))
                        photo = ImageTk.PhotoImage(img)
                        label = tk.Label(text, image=photo, bg='#333333', cursor='sb_h_double_arrow')
                        label.image = photo
                        label.bind('<Button-1>', lambda e, l=label, i=img: start_resize(e, l, i))
                        label.bind('<B1-Motion>', lambda e, l=label, i=img: do_resize(e, l, i))
                    except:
                        label = tk.Label(text, text="[Image Error]", bg='red', fg='white')

                elif media_type == 'video':
                    # Paste your video thumb_frame code here (from reload block)
                    thumb_frame = tk.Frame(text, bg='#1e3a1e', width=320, height=180)
                    tk.Label(thumb_frame, text='▶ ' + original_filename[:25], 
                             bg='#1e3a1e', fg='#88ff88').pack(expand=True)
                    thumb_frame.bind('<Button-1>', lambda e, fp=file_path: play_video(fp))
                    # ... add menu etc. ...
                    label = thumb_frame

                elif media_type == 'doc':
                    # Paste your doc_frame code here
                    doc_frame = tk.Frame(text, bg='#2a2a3a', width=220, height=120)
                    tk.Label(doc_frame, text='📄 ' + original_filename[:20], 
                             bg='#2a2a3a', fg='#aaffaa').pack(pady=10)
                    tk.Button(doc_frame, text="↓ Save", command=lambda fp=file_path: download_file(fp),
                              bg='#3a5a3a', fg='white', relief='flat').pack(side='bottom')
                    label = doc_frame

                if label:
                    label.media_id = media_id
                    try:
                        text.window_create(insert_pos, window=label)
                    except tk.TclError:
                        text.window_create("end", window=label)

            # Add the 3 buttons
            tk.Button(toolbar, text="Image", command=lambda: insert_new_media('image'), **btn_style).pack(side='left', padx=5)
            tk.Button(toolbar, text="Video", command=lambda: insert_new_media('video'), **btn_style).pack(side='left', padx=5)
            tk.Button(toolbar, text="Document", command=lambda: insert_new_media('doc'), **btn_style).pack(side='left', padx=5)
            
            sorted_media = sorted(media_list, key=lambda m: parse_index(m['position_index']), reverse=True)
            
            for media in sorted_media:
                pos = media['position_index'] or "end"
                file_path = media['file_path']
                original_filename = media['original_filename']
                media_type = media['media_type']
                media_id = media['id']
                
                if media_type == 'image':
                    from PIL import Image, ImageTk
                    try:
                        img = Image.open(file_path)
                        img.thumbnail((200, 200))
                        photo = ImageTk.PhotoImage(img)
                        label = tk.Label(text, image=photo, bg='#333333', cursor='sb_h_double_arrow')
                        label.image = photo
                        label.bind('<Button-1>', lambda e, l=label, i=img: start_resize(e, l, i))
                        label.bind('<B1-Motion>', lambda e, l=label, i=img: do_resize(e, l, i))
                    except:
                        label = tk.Label(text, text="[Broken Image]", bg='red', fg='white')
                    label.media_id = media_id
                
                elif media_type == 'video':
                    thumb_frame = tk.Frame(text, bg='#333333', width=200, height=150)
                    # Placeholder thumbnail (no real extract without extra libs)
                    tk.Label(thumb_frame, text='▶ Video: ' + original_filename[:20], bg='#333333', fg='#cccccc', wraplength=180).pack(pady=10)
                    thumb_frame.bind('<Button-1>', lambda e, fp=file_path: play_video(fp))
                    menu = tk.Menu(thumb_frame, tearoff=0)
                    menu.add_command(label='Download', command=lambda fp=file_path: download_file(fp))
                    thumb_frame.bind('<Button-3>', lambda e: menu.post(e.x_root, e.y_root))
                    label = thumb_frame
                    label.media_id = media_id
                
                elif media_type in ['pdf', 'doc']:
                    doc_frame = tk.Frame(text, bg='#2a2a3a', width=220, height=100)
                    # Placeholder thumbnail
                    tk.Label(doc_frame, text='📄 Doc: ' + original_filename[:20], bg='#2a2a3a', fg='#aaffaa', wraplength=200).pack(pady=4)
                    tk.Button(doc_frame, text="↓ Save", command=lambda fp=file_path: download_file(fp), bg='#3a5a3a', fg='white', relief='flat', padx=8).pack(side='bottom', pady=4)
                    label = doc_frame
                    label.media_id = media_id
                
                try:
                    insert_pos = pos if pos else "end"
                    text.window_create(insert_pos, window=label)
                except tk.TclError as e:
                    print(f"window create failed at {pos}: {e}")   # debug
                    text.window_create("end", window=label)  # fallback to end



                    # ───────────────────────────────────────────────
        #   Image resize helpers
        # ───────────────────────────────────────────────
            def start_resize(event, label, original_image):
                """Begin resizing image when mouse pressed on it"""
                label._resize_start_x = event.x
                label._resize_start_width = label.winfo_width()
                label._resize_start_height = label.winfo_height()
                label._original_image = original_image  # keep reference
    
            def do_resize(event, label, original_image):
                """Resize image while dragging mouse (preserve aspect ratio)"""
                if not hasattr(label, '_resize_start_x'):
                    return
    
                dx = event.x - label._resize_start_x
                new_width = max(60, label._resize_start_width + dx)  # min 60px
    
                # Preserve aspect ratio
                aspect = label._resize_start_height / label._resize_start_width
                new_height = int(new_width * aspect)
    
                try:
                    from PIL import Image, ImageTk
                    resized_img = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    new_photo = ImageTk.PhotoImage(resized_img)
                    label.configure(image=new_photo)
                    label.image = new_photo  # keep reference alive
                    label.configure(width=new_width, height=new_height)
                except Exception as e:
                    print(f"Resize failed: {e}")
    
            # ───────────────────────────────────────────────
            #   Media action helpers
            # ───────────────────────────────────────────────
            def play_video(file_path):
                """Open video file with default system player"""
                import subprocess
                import sys
                import os
    
                if not os.path.exists(file_path):
                    print(f"Video file not found: {file_path}")
                    return
    
                try:
                    if sys.platform == "darwin":       # macOS
                        subprocess.call(['open', file_path])
                    elif sys.platform == "win32":      # Windows
                        os.startfile(file_path)
                    else:                              # Linux
                        subprocess.call(['xdg-open', file_path])
                except Exception as e:
                    print(f"Could not open video: {e}")
                    # Optional: show messagebox
                    # messagebox.showerror("Error", f"Cannot play video:\n{e}")
    
            def download_file(file_path):
                """Let user choose where to save a copy of the media file"""
                from tkinter import filedialog
                import os
                import shutil
    
                if not os.path.exists(file_path):
                    print(f"File not found for download: {file_path}")
                    return
    
                default_name = os.path.basename(file_path)
                dest_path = filedialog.asksaveasfilename(
                    defaultextension=os.path.splitext(default_name)[1],
                    initialfile=default_name,
                    title="Save As..."
                )
    
                if dest_path:
                    try:
                        shutil.copy2(file_path, dest_path)
                        print(f"File saved to: {dest_path}")
                    except Exception as e:
                        print(f"Download failed: {e}")
        
            # Bind auto-save
            text.bind('<KeyRelease>', lambda e: self.schedule_save())
            text.bind('<FocusOut>', lambda e: self.save_current_page())


 #       def restore_text_content(self, text_widget, content):
 #           """Restore text widget from content"""
 #           text_widget.delete('1.0', 'end')
 #           
 #           for item in content:
 #               if not isinstance(item, (list, tuple)) or len(item) < 2:
 #                   continue
 #               
 #               cmd = item[0]
 #               
 #               if cmd == 'text' and len(item) >= 3:
 #                   text_widget.insert(item[1], item[2])
 #               elif cmd == 'tagon' and len(item) >= 3:
 #                   text_widget.tag_add(item[2], item[1])
 #               elif cmd == 'tagoff' and len(item) >= 3:
 #                   text_widget.tag_remove(item[2], item[1])
 #               elif cmd == 'mark' and len(item) >= 3:
 #                   text_widget.mark_set(item[2], item[1])
                # window/image restoration can be added here

        def schedule_save(self):
            """Debounced auto-save"""
            if hasattr(self, '_save_timer'):
                self.root.after_cancel(self._save_timer)
            self._save_timer = self.root.after(1000, self.save_current_page)  # 1 sec delay

        def save_current_page(self):
            """Save current page content to database"""
            if not self.current_editor or not self.current_node_id:
                return
            
            text = self.current_editor.text_area
            content = text.get("1.0", "end-1c")
            
            tags = {}
            for tag_name in ['bold', 'italic', 'underline', 'highlight', 'code']:
                ranges = text.tag_ranges(tag_name)
                if ranges:
                    tags[tag_name] = [[str(ranges[i]), str(ranges[i+1])] for i in range(0, len(ranges), 2)]
            
            dump_data = {'content': content, 'tags': tags}
            save_subpage(self.current_node_id, dump_data)
            
            # Update media positions
            for window_name in text.window_names():
                try:
                    widget = text.nametowidget(window_name)
                    if hasattr(widget, 'media_id'):
                        pos = text.index(window_name)
                        from backend.database import update_media_position
                        update_media_position(widget.media_id, pos)
                except Exception as e:
                    print(f"Failed to update media position for widget {widget}: {e}")
    # Create UI
    # Create UI in a separate window
    window = tk.Toplevel()
    window.title(project_data.get('title', 'Project') if project_data else "Project")
    window.geometry("1000x700")
    window.minsize(800, 500)

    # Center window
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (1000 // 2)
    y = (window.winfo_screenheight() // 2) - (700 // 2)
    window.geometry(f"1000x700+{x}+{y}")

    # Main container inside new window
    main_frame = ttk.Frame(window)
    main_frame.pack(fill='both', expand=True)

    # Pass main_frame to ProjectManager class (not the window directly)
    ProjectManager(main_frame, project_data, parent_card)

    # Clean close
    window.protocol("WM_DELETE_WINDOW", window.destroy)

    return window