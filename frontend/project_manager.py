# project_manager.py
import tkinter as tk
from tkinter import PhotoImage, ttk, simpledialog, messagebox , filedialog

import cv2
from simple_text_editor import create_text_editor
import sys
import os
import io
import subprocess
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import (
    create_node, get_nodes, get_all_nodes_for_project, get_node,
    rename_node, delete_node,
    save_subpage, load_subpage,
    save_media, get_media_for_node, import_media_file, delete_media,
)
from flowchart import FlowchartEditor
from PIL import Image, ImageTk ,ImageDraw
import fitz

from codeblockhandler_updated import CodeBlockHandler
from text_formatter import TextFormatter


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
            
            # Separator
            tk.Frame(btn_frame, bg='#444444', height=2).pack(fill='x', pady=8)
            
            # Export button with different styling
            export_btn_style = btn_style.copy()
            export_btn_style['bg'] = '#0078d4'
            export_btn_style['fg'] = '#ffffff'
            export_btn_style['activebackground'] = '#005a9e'
            export_btn_style['font'] = ('Segoe UI', 10, 'bold')
            export_btn_style['pady'] = 9
            tk.Button(btn_frame, text="Export Documentation PDF", command=self.export_project,
                      **export_btn_style).pack(fill='x', pady=(2, 5), padx=4)

            # Editor container
            self.editor_container = ttk.Frame(self.root)
            self.editor_container.pack(side='left', fill='both', expand=True)

            self.current_editor = None
            self.current_editor_frame = None
            self.current_node_id = None
            self.text = None
            self.formatter = None
            self._save_timer = None

            # Build tree from database
            self.root_item = self.tree.insert("", "end", text="Project", open=True)
            self.node_id_to_tree_id = {}  # Map database node_id to tree item_id
            self.tree_id_to_node_id = {}  # Reverse mapping
            self.load_tree()

        @staticmethod
        def validate_item_name(name):
            if name is None:
                return False, "Name cannot be empty."
            name = name.strip()
            if not name:
                return False, "Name cannot be empty."
            if len(name) > 80:
                return False, "Name cannot exceed 80 characters."
            return True, name

        def cleanup_orphaned_tags(self, text=None):
            text = text or self.text
            if not text:
                return
            preserve = {'sel', 'sel.last', 'bold', 'italic', 'underline', 'highlight', 'code_block'}
            for tag in text.tag_names():
                if tag in preserve:
                    continue
                if not text.tag_ranges(tag):
                    try:
                        text.tag_delete(tag)
                    except tk.TclError:
                        pass

        def reset_text_widget_state(self, text_widget):
            if not text_widget:
                return
            for tag in text_widget.tag_names():
                if tag not in ('sel', 'sel.last'):
                    try:
                        text_widget.tag_delete(tag)
                    except tk.TclError:
                        pass
            try:
                text_widget.tag_remove('sel', '1.0', tk.END)
            except tk.TclError:
                pass
            try:
                text_widget.mark_set(tk.INSERT, '1.0')
                text_widget.edit_reset()
                text_widget.see('1.0')
                text_widget.delete('1.0', tk.END)
            except tk.TclError:
                pass

        def setup_text_widget_bindings(self, text):
            def on_delete_key(event):
                self.root.after(10, lambda: self.cleanup_orphaned_tags(text))

            text.bind('<KeyRelease-Delete>', on_delete_key, add='+')
            text.bind('<KeyRelease-BackSpace>', on_delete_key, add='+')

            def on_cut(event):
                text.event_generate('<<Cut>>')
                self.root.after(10, lambda: self.cleanup_orphaned_tags(text))
                return 'break'

            text.bind('<Control-x>', on_cut)
            text.bind('<Control-X>', on_cut)

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
            try:
                node = get_node(node_id)
                return node, tree_id
            except Exception as e:
                messagebox.showerror("Error", f"Could not load item:\n{e}", parent=self.root)
                return None, None

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
                        "Subpages and flowcharts cannot have children.",parent=self.root)
                    return
            
            name = simpledialog.askstring("Folder Name", "Enter folder name:", parent=self.root)
            ok, name_or_msg = self.validate_item_name(name)
            if not ok:
                if name is not None:
                    messagebox.showerror("Invalid Name", name_or_msg, parent=self.root)
                return
            name = name_or_msg
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'folder', name)
                # Add to tree
                tree_id = self.tree.insert(parent_tree_id, "end", text=name, open=True)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
            except ValueError as e:
                messagebox.showerror("Error", str(e),parent=self.root)

        def add_subpage(self):
            """Add a subpage node"""
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a folder first",parent=self.root)
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
                        "Subpages and flowcharts cannot have children.",parent=self.root)
                    return
            
            name = simpledialog.askstring("Subpage Name", "Enter subpage name:", parent=self.root)
            ok, name_or_msg = self.validate_item_name(name)
            if not ok:
                if name is not None:
                    messagebox.showerror("Invalid Name", name_or_msg, parent=self.root)
                return
            name = name_or_msg
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'subpage', name)
                # Add to tree
                tree_id = self.tree.insert(parent_tree_id, "end", text=name)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
                # Initialize empty content
                save_subpage(db_node_id, {"content": "", "tags": {}, "formatting": []})
            except ValueError as e:
                messagebox.showerror("Error", str(e),parent=self.root)

        def add_flowchart(self):
            """Add a flowchart node"""
            selected = self.tree.selection()
            if not selected:
                messagebox.showwarning("Warning", "Please select a folder first",parent=self.root)
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
                        "Subpages and flowcharts cannot have children.",parent=self.root)
                    return
            
            name = simpledialog.askstring("Flowchart Name", "Enter flowchart name:", parent=self.root)
            ok, name_or_msg = self.validate_item_name(name)
            if not ok:
                if name is not None:
                    messagebox.showerror("Invalid Name", name_or_msg, parent=self.root)
                return
            name = name_or_msg
            
            try:
                db_node_id = create_node(self.project_id, parent_node_id, 'flowchart', name)
                tree_id = self.tree.insert(parent_tree_id, "end", text=name)
                self.node_id_to_tree_id[db_node_id] = tree_id
                self.tree_id_to_node_id[tree_id] = db_node_id
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=self.root)

        def rename_item(self):
            """Rename selected node"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                messagebox.showwarning("Warning", "Please select an item to rename", parent=self.root)
                return
            
            old_name = node_info['name']
            new_name = simpledialog.askstring("Rename", f"Enter new name for '{old_name}':", parent=self.root)
            ok, name_or_msg = self.validate_item_name(new_name)
            if not ok:
                if new_name is not None:
                    messagebox.showerror("Invalid Name", name_or_msg, parent=self.root)
                return
            new_name = name_or_msg
            if new_name == old_name:
                return
            
            try:
                rename_node(node_info['id'], new_name)
                self.tree.item(tree_id, text=new_name)
            except Exception as e:
                messagebox.showerror("Rename Failed", str(e), parent=self.root)

        def delete_item(self):
            """Delete selected node and all children"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                messagebox.showwarning("Warning", "Please select an item to delete", parent=self.root)
                return
            
            confirm = messagebox.askyesno("Confirm Delete",
                f"Delete '{node_info['name']}' and all its contents?",parent=self.root)
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

        def export_project(self):
            """Export entire project to PDF"""
            # Save current page before exporting
            if self.current_node_id and self.current_editor:
                self.save_current_page()
            
            try:
                from project_export import export_project
                import backend.database as db
                
                success = export_project(
                    self.project_id,
                    self.project_data.get('title', 'Project'),
                    db
                )
                
            except ImportError as e:
                messagebox.showerror(
                    "Export Failed",
                    "Export module not found. Make sure project_export.py is in the same directory.\n\n"
                    f"Error: {str(e)}" ,
                )
            except Exception as e:
                messagebox.showerror(
                    "Export Failed",
                    f"An error occurred during export:\n{str(e)}" ,
                )

        def on_tree_select(self, event):
            """Handle tree item selection"""
            node_info, tree_id = self.get_selected_node_info()
            if not node_info:
                return
            
            # Save current page BEFORE switching — but only if it's a subpage
            if self.current_node_id and self.current_editor:
                if hasattr(self.current_editor, 'text_area'):  # only subpages have text_area
                    if node_info['id'] != self.current_node_id:
                        self.save_current_page()
                elif hasattr(self.current_editor, 'save_flowchart'):  # flowchart
                    if node_info['id'] != self.current_node_id:
                        self.current_editor.save_flowchart(self.current_node_id)
            
            if node_info['node_type'] == 'folder':
                # Folders don't open an editor
                return
            elif node_info['node_type'] == 'flowchart':
                self.open_flowchart_editor(node_info['id'])
            elif node_info['node_type'] == 'subpage':
                self.open_subpage_editor(node_info['id'])

        def open_flowchart_editor(self, node_id: int):
            """Open flowchart editor with safe save on close"""
            if self.current_editor_frame:
                self.current_editor_frame.destroy()
            
            self.current_editor_frame = ttk.Frame(self.editor_container)
            self.current_editor_frame.pack(fill="both", expand=True)
            
            editor = FlowchartEditor(self.current_editor_frame)
            editor.pack(fill="both", expand=True)
            self.current_editor = editor
            self.current_node_id = node_id
            
            # Pass node_id & load immediately
            editor.current_node_id = node_id
            editor.load_flowchart(node_id)

            # Safe save on destroy — check if canvas still exists
            def on_editor_close():
                if hasattr(editor, 'canvas') and editor.canvas.winfo_exists():
                    editor.save_flowchart(node_id)
                self.current_editor_frame.destroy()

            self.current_editor_frame.bind("<Destroy>", lambda e: on_editor_close())

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
            self.text = text
            self.reset_text_widget_state(text)

            formatter = TextFormatter(text)
            self.formatter = formatter
            self.setup_text_widget_bindings(text)

            def _fmt(op):
                def handler(event=None):
                    op()
                    return 'break'
                return handler

            text.bind('<Control-b>', _fmt(formatter.toggle_bold))
            text.bind('<Control-B>', _fmt(formatter.toggle_bold))
            text.bind('<Control-i>', _fmt(formatter.toggle_italic))
            text.bind('<Control-I>', _fmt(formatter.toggle_italic))
            text.bind('<Control-u>', _fmt(formatter.toggle_underline))
            text.bind('<Control-U>', _fmt(formatter.toggle_underline))
            text.bind('<Control-h>', _fmt(formatter.toggle_highlight))
            text.bind('<Control-H>', _fmt(formatter.toggle_highlight))
            text.bind('<Control-Shift-H>', _fmt(formatter.toggle_highlight))

            dump = None
            try:
                dump = load_subpage(node_id)
            except Exception as e:
                messagebox.showerror(
                    "Load Failed",
                    f"Could not load this page.\n{e}",
                    parent=self.root,
                )
                dump = {"content": "", "tags": {}}

            tags_data = {}
            if dump:
                if isinstance(dump, str):
                    content = dump
                    tags_data = {}
                else:
                    content = dump.get('content', '')
                    tags_data = dump.get('tags', {}) or {}
                if content:
                    text.insert("1.0", content)
                formatter.apply_tags_map(tags_data)
            
            def parse_index(idx):
                if not idx:
                    return (0, 0)
                try:
                    line, char = map(int, idx.split('.'))
                    return line, char
                except:
                    return (0, 0)
                
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
                    filetypes=filetypes + [("All files", "*.*"),],
                    parent= self.root
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
                        label.bind('<Double-Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))
                        image_menu = tk.Menu(label, tearoff=0, bg='#222', fg='#ddd')
                        image_menu.add_command(label="Open image", command=lambda fp=file_path: play_video(fp, parent=self.root))
                        image_menu.add_command(label="Download image…", command=lambda fp=file_path: download_file(fp))
                        label.bind('<Button-3>', lambda e, m=image_menu: m.tk_popup(e.x_root, e.y_root))
                    except:
                        label = tk.Label(text, text="[Image Error]", bg='red', fg='white')

                elif media_type == 'video':
                    thumb_frame = tk.Frame(text, bg='#111', width=360, height=200, bd=0, relief='flat')

                    # Background thumbnail (placeholder or real)
                    try:
                        cap = cv2.VideoCapture(file_path)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame)
                                img.thumbnail((360, 200))
                                photo = ImageTk.PhotoImage(img)
                                bg_label = tk.Label(thumb_frame, image=photo, bg='#111')
                                bg_label.image = photo
                                bg_label.place(relx=0.5, rely=0.5, anchor='center')
                    except:
                        bg_label = tk.Label(thumb_frame, text="Video", bg='#222', fg='#888')
                        bg_label.place(relx=0.5, rely=0.5, anchor='center')


                    play_icon = tk.Label(thumb_frame, text="▶", font=('Segoe UI', 30), fg="white", bg='#0d1117', cursor='hand2')
                    play_icon.place(relx=0.5, rely=0.5, anchor='center')
                    video_download = tk.Label(thumb_frame, text="  ↓  Download  ", font=('Segoe UI', 9, 'bold'),
                                              fg='white', bg='#1677d2', cursor='hand2')
                    video_download.place(relx=1.0, rely=1.0, anchor='se', x=-10, y=-10)
                    video_download.bind('<Button-1>', lambda e, fp=file_path: (download_file(fp), 'break'))
                    # Click to play (whole frame)
                    thumb_frame.bind('<Button-1>', lambda e, fp=file_path: play_video(fp))
                    bg_label.bind('<Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))
                    play_icon.bind('<Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))




                    # Right-click download menu
                    menu = tk.Menu(thumb_frame, tearoff=0, bg='#222', fg='#ddd', bd=0)
                    menu.add_command(label="Download video", command=lambda fp=file_path: download_file(fp))
                    thumb_frame.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))

                    label = thumb_frame


                elif media_type in ['pdf', 'doc']:
                    doc_frame = tk.Frame(text, bg='#1a1a2e', width=240, height=160, bd=1, relief='flat')
                    
                    # Try to generate real thumbnail for PDF
                    img_tk = None
                    is_pdf = file_path.lower().endswith('.pdf')
                    if is_pdf:
                        print("[PDF THUMB] File is PDF → attempting generation")
                        try:
                            import fitz
                            print("[PDF THUMB] fitz imported OK")
                            doc = fitz.open(file_path)
                            print(f"[PDF THUMB] Opened document - {len(doc)} pages")
                            if len(doc) > 0:
                                page = doc[0]
                                zoom = 2.0
                                mat = fitz.Matrix(zoom, zoom)
                                pix = page.get_pixmap(matrix=mat, alpha=False)
                                print("[PDF THUMB] Pixmap generated")
                                img_data = pix.tobytes("png")
                                image = Image.open(io.BytesIO(img_data))
                                image.thumbnail((220, 320))
                                img_tk = ImageTk.PhotoImage(image)
                                print("[PDF THUMB] SUCCESS - thumbnail ready")
                            doc.close()
                        except ImportError:
                            print("[PDF THUMB] PyMuPDF missing - install: pip install pymupdf")
                        except Exception as e:
                            print(f"[PDF THUMB] ERROR {file_path}: {type(e).__name__}: {str(e)}")
                    else:
                        print("[DOC THUMB] Non-PDF doc → using fallback")
                    
                    preview_text = original_filename[:24] + "…" if len(original_filename) > 24 else original_filename
                    # Label with thumbnail or fallback
                    if img_tk:
                        doc_label = tk.Label(doc_frame, image=img_tk, bg='#1a1a2e')
                        doc_label.image = img_tk  # MUST keep reference
                        print("[DOC/PDF] Displaying real thumbnail")
                    else:
                        fallback_icon = "📄" if is_pdf else "📝"
                        doc_label = tk.Label(
                            doc_frame,
                            text=f"{fallback_icon}\n{preview_text}",
                            bg='#1a1a2e', fg='#aaccff',
                            font=('Segoe UI', 18),
                            wraplength=220,
                            justify='center'
                        )
                        print("[DOC/PDF] Displaying fallback icon/text")
                    
                    doc_label.pack(pady=10, padx=10, expand=True, fill='both')
                    
                    # Download icon top-right with hover
                    dl_icon = tk.Label(doc_frame, text="  ↓  Download  ", font=('Segoe UI', 9, 'bold'),
                                       fg='white', bg='#1677d2', cursor='hand2', padx=5, pady=3)
                    dl_icon.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)

                    
    
                    dl_icon.bind('<Button-1>', lambda e, fp=file_path: download_file(fp))
                    doc_label.bind('<Double-Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))

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

            # Font family selector
            fonts = ['Segoe UI', 'Arial', 'Helvetica', 'Times New Roman', 'Courier New', 'Georgia', 'Verdana']
            font_var = tk.StringVar(value='Segoe UI')  # default

            font_menu = tk.OptionMenu(toolbar, font_var, *fonts,
                                      command=lambda f: apply_font_family(f))
            
            # Safe style for the OptionMenu button itself
            menu_btn_style = {k: v for k, v in btn_style.items() if k in ['bg', 'fg', 'activebackground', 'activeforeground', 'relief', 'bd', 'font', 'highlightthickness']}
            font_menu.config(width=12, **menu_btn_style)
            
            # Safe style for the dropdown menu items
            menu_items_style = {k: v for k, v in btn_style.items() if k in ['bg', 'fg', 'activebackground', 'activeforeground', 'font']}
            font_menu['menu'].config(**menu_items_style)
            
            font_menu.pack(side='left', padx=4)
            # Font size selector
            sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48 , 52 , 64 , 72 , 80 , 96]
            size_var = tk.StringVar(value='12')

            size_menu = tk.OptionMenu(toolbar, size_var, *sizes,
                                      command=lambda s: apply_font_size(int(s)))
            
            # Safe style for the OptionMenu button itself
            menu_btn_style = {k: v for k, v in btn_style.items() if k in ['bg', 'fg', 'activebackground', 'activeforeground', 'relief', 'bd', 'font', 'highlightthickness']}
            size_menu.config(width=6, **menu_btn_style)
            
            # Safe style for the dropdown menu items
            menu_items_style = {k: v for k, v in btn_style.items() if k in ['bg', 'fg', 'activebackground', 'activeforeground', 'font']}
            size_menu['menu'].config(**menu_items_style)
            
            size_menu.pack(side='left', padx=4)

            def apply_font_family(family):
                """Apply font family using formatter (FIXED)"""
                formatter.apply_font_family(family)

            def apply_font_size(size):
                """Apply font size using formatter (FIXED)"""
                formatter.apply_font_size(size)

            
            # Reload media safely
            media_list = get_media_for_node(node_id)
            print(f"[Reload] {len(media_list)} media items for node {node_id}")

            def parse_index(idx):
                if not idx or '.' not in idx:
                    return (0, 0)
                try:
                    line, char = map(int, idx.split('.'))
                    return line, char
                except:
                    return (0, 0)

            # Sort oldest first (low position to high) — prevents index shift issues
            sorted_media = sorted(media_list, key=lambda m: parse_index(m['position_index']))

            for media in sorted_media:
                pos = media['position_index'] or "1.0"
                file_path = media.get('file_path')
                if not file_path or not os.path.exists(file_path):
                    print(f"[SKIP] Missing file for media ID {media['id']}: {file_path}")
                    continue

                original_filename = media.get('original_filename', 'unnamed')
                media_type = media['media_type']
                media_id = media['id']

                print(f"[Reload] Inserting {media_type} ID {media_id} at {pos}")

                label = None

                if media_type == 'image':
                    try:
                        img = Image.open(file_path)
                        img.thumbnail((300, 300))
                        photo = ImageTk.PhotoImage(img)
                        label = tk.Label(text, image=photo, bg='#333333', cursor='sb_h_double_arrow')
                        label.image = photo
                        label.bind('<Button-1>', lambda e, l=label, i=img: start_resize(e, l, i))
                        label.bind('<B1-Motion>', lambda e, l=label, i=img: do_resize(e, l, i))
                        label.bind('<Double-Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))
                        image_menu = tk.Menu(label, tearoff=0, bg='#222', fg='#ddd')
                        image_menu.add_command(label="Open image", command=lambda fp=file_path: play_video(fp, parent=self.root))
                        image_menu.add_command(label="Download image…", command=lambda fp=file_path: download_file(fp))
                        label.bind('<Button-3>', lambda e, m=image_menu: m.tk_popup(e.x_root, e.y_root))
                    except Exception as e:
                        print(f"[Image fail] {e}")
                        label = tk.Label(text, text="[Broken Image]", bg='red', fg='white')

                elif media_type == 'video':
                    thumb_frame = tk.Frame(text, bg="#b5b6b9", width=360, height=200, bd=0, relief='flat')

                    # Background thumbnail (real or placeholder)
                    bg_photo = None
                    try:
                        cap = cv2.VideoCapture(file_path)
                        if cap.isOpened():
                            ret, frame = cap.read()
                            if ret:
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame)
                                img.thumbnail((360, 200))
                                bg_photo = ImageTk.PhotoImage(img)
                    except:
                        pass

                    bg_label = tk.Label(thumb_frame, image=bg_photo, bg='#0d1117')
                    if bg_photo:
                        bg_label.image = bg_photo
                    bg_label.place(relx=0.5, rely=0.5, anchor='center')


                    play_icon = tk.Label(thumb_frame, text="▶", font=('Segoe UI', 30), fg="white", bg='#0d1117', cursor='hand2')
                    play_icon.place(relx=0.5, rely=0.5, anchor='center')
                    video_download = tk.Label(thumb_frame, text="  ↓  Download  ", font=('Segoe UI', 9, 'bold'),
                                              fg='white', bg='#1677d2', cursor='hand2')
                    video_download.place(relx=1.0, rely=1.0, anchor='se', x=-10, y=-10)
                    video_download.bind('<Button-1>', lambda e, fp=file_path: download_file(fp))
                    # Click to play (whole frame)


                    # Right-click download menu
                    menu = tk.Menu(thumb_frame, tearoff=0, bg='#1e1e2e', fg='#ddd', bd=0)
                    menu.add_command(label="Download video", command=lambda fp=file_path: download_file(fp))
                    thumb_frame.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))

                    def on_thumb_click(event, fp=file_path):
                        print("Clicked!")
                        play_video(fp, parent=self.root)
                    
                    # Bind to frame
                    thumb_frame.bind('<Button-1>', on_thumb_click)
                    # Bind to background image label
                    bg_label.bind('<Button-1>', on_thumb_click)
                    # Bind to play icon label
                    for child in thumb_frame.winfo_children():
                        if child is not video_download:
                            child.bind('<Button-1>', on_thumb_click)



                    label = thumb_frame

                elif media_type in ['pdf', 'doc', 'txt']:
                    print(f"[DOC/PDF DEBUG] Processing {media_type} ID {media_id} - path: {file_path}")
                    
                    doc_frame = tk.Frame(text, bg='#1a1a2e', width=240, height=160, bd=1, relief='flat')
                    
                    img_tk = None
                    preview_text = original_filename[:18] + "..." if len(original_filename) > 18 else original_filename
                    
                    # Try real thumbnail based on actual file extension (not just media_type)
                    is_pdf = file_path.lower().endswith('.pdf')
                    if is_pdf:
                        print("[PDF THUMB] File is PDF → attempting generation")
                        try:
                            import fitz
                            print("[PDF THUMB] fitz imported OK")
                            doc = fitz.open(file_path)
                            print(f"[PDF THUMB] Opened document - {len(doc)} pages")
                            if len(doc) > 0:
                                page = doc[0]
                                zoom = 2.0
                                mat = fitz.Matrix(zoom, zoom)
                                pix = page.get_pixmap(matrix=mat, alpha=False)
                                print("[PDF THUMB] Pixmap generated")
                                img_data = pix.tobytes("png")
                                image = Image.open(io.BytesIO(img_data))
                                image.thumbnail((220, 320))
                                img_tk = ImageTk.PhotoImage(image)
                                print("[PDF THUMB] SUCCESS - thumbnail ready")
                            doc.close()
                        except ImportError:
                            print("[PDF THUMB] PyMuPDF missing - install: pip install pymupdf")
                        except Exception as e:
                            print(f"[PDF THUMB] ERROR {file_path}: {type(e).__name__}: {str(e)}")
                    else:
                        print("[DOC THUMB] Non-PDF doc → using fallback")
                    
                    # Label with thumbnail or fallback
                    if img_tk:
                        doc_label = tk.Label(doc_frame, image=img_tk, bg='#1a1a2e')
                        doc_label.image = img_tk  # MUST keep reference
                        print("[DOC/PDF] Displaying real thumbnail")
                    else:
                        fallback_icon = "📄" if is_pdf else "📝"
                        doc_label = tk.Label(
                            doc_frame,
                            text=f"{fallback_icon}\n{preview_text}",
                            bg='#1a1a2e', fg='#aaccff',
                            font=('Segoe UI', 18),
                            wraplength=220,
                            justify='center'
                        )
                        print("[DOC/PDF] Displaying fallback icon/text")
                    
                    doc_label.pack(pady=10, padx=10, expand=True, fill='both')
                    
                    # Download icon top-right with hover
                    dl_icon = tk.Label(doc_frame, text="  ↓  Download  ", font=('Segoe UI', 9, 'bold'),
                                       fg='white', bg='#1677d2', cursor='hand2', padx=5, pady=3)
                    dl_icon.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)

                    dl_icon.bind('<Button-1>', lambda e, fp=file_path: download_file(fp))
                    doc_label.bind('<Double-Button-1>', lambda e, fp=file_path: play_video(fp, parent=self.root))

                    label = doc_frame
 
                if label:
                    label.media_id = media_id
                    try:
                        text.window_create(pos, window=label)
                        # NO extra insert here — keeps layout stable
                    except tk.TclError as e:
                        print(f"[Window create fail] at {pos}: {e}")
                        text.window_create("end", window=label)
                else:
                    print(f"[SKIP] No label created for media {media_id}")


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

            def play_video(file_path , parent=None):
                """Open any media file with the operating system's default app."""
                
                file_path = os.path.abspath(file_path)
                print(f"[PLAY VIDEO] Attempting to play: {file_path}")
            
                if not os.path.exists(file_path):
                    messagebox.showerror("File Not Found", f"Video file missing:\n{file_path}", parent=parent)
                    return
            
                try:
                    if sys.platform.startswith('win'):
                        os.startfile(os.path.normpath(file_path))
                        print("[PLAY] Windows - os.startfile used")
            
                    elif sys.platform.startswith('linux'):
                        subprocess.Popen(f'xdg-open "{file_path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print("[PLAY] Linux - xdg-open used")
            
                    elif sys.platform == 'darwin':
                        subprocess.Popen(f'open "{file_path}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print("[PLAY] macOS - open used")
            
                    else:
                        raise OSError(f"Unsupported OS: {sys.platform}")
            
                except Exception as e:
                    print(f"[PLAY ERROR] {type(e).__name__}: {str(e)}")
                    messagebox.showerror(
                        "Playback Error",
                        f"Cannot open video.\n\nError: {str(e)}\n\nTry opening manually: {file_path}",
                        parent=parent
                    )
            def download_file(file_path):
                """Let user choose where to save a copy of the media file"""
                from tkinter import filedialog
                import os
                import shutil
    
                if not os.path.exists(file_path):
                    messagebox.showerror("File Not Found", f"This media file is missing:\n{file_path}", parent=self.root)
                    return
    
                default_name = os.path.basename(file_path)
                dest_path = filedialog.asksaveasfilename(
                    defaultextension=os.path.splitext(default_name)[1],
                    initialfile=default_name,
                    title="Save As...",
                    parent=self.root,
                )
    
                if dest_path:
                    try:
                        shutil.copy2(file_path, dest_path)
                        messagebox.showinfo("Download complete", f"Saved to:\n{dest_path}", parent=self.root)
                    except Exception as e:
                        messagebox.showerror("Download failed", str(e), parent=self.root)


            code_handler = CodeBlockHandler(text, theme='github_dark')
            # Available themes: github_dark, monokai, dracula, nord, solarized, 
            #                   one_dark, material, tomorrow, light
            
            def on_key_release(event=None):
                """Handle both code block styling and auto-save"""
                code_handler.apply_code_block_styling(event)
                self.schedule_save()
            
            # Single binding for both code blocks and auto-save
            text.bind('<KeyRelease>', on_key_release)
            
            # Initial check after loading
            text.after(100, code_handler.apply_code_block_styling)
            
            # Separate binding for focus out
            text.bind('<FocusOut>', lambda e: self.save_current_page())

            def detect_media_deletion(round=1):
                """Check for deleted media - retry once after delay"""
                if not self.current_editor or not self.current_node_id:
                    return

                text = self.current_editor.text_area
                
                current_windows = text.window_names()
                existing_widget_ids = set()

                for win_name in current_windows:
                    try:
                        widget = text.nametowidget(win_name)
                        if hasattr(widget, 'media_id'):
                            existing_widget_ids.add(widget.media_id)
                            print(f"[Media Check] Round {round} - Alive widget ID: {widget.media_id}")
                    except tk.TclError:
                        pass

                from backend.database import get_media_for_node
                media_list = get_media_for_node(self.current_node_id)
                db_media_ids = {m['id'] for m in media_list if m.get('id') is not None}

                deleted_ids = db_media_ids - existing_widget_ids

                if deleted_ids:
                    print(f"[Media Delete] DETECTED in round {round}: {deleted_ids}")
                    from backend.database import _db_instance
                    conn = _db_instance._connect()
                    try:
                        for mid in deleted_ids:
                            conn.execute("DELETE FROM media WHERE id=?", (mid,))
                        conn.commit()
                        print(f"[Media Delete] Removed {len(deleted_ids)} entries")
                    finally:
                        conn.close()
                else:
                    print(f"[Media Check] Round {round} - No deletions (alive: {len(current_windows)}, DB: {len(db_media_ids)})")

                # Retry once after 1 second if first round found nothing
                if round == 1:
                    text.after(1000, lambda: detect_media_deletion(round=2))
                else:
                    # Next normal check after 3 seconds
                    text.after(3000, lambda: detect_media_deletion(round=1))

            text.after(1500, lambda: detect_media_deletion(round=1))  # Start first check after 2 seconds

            
        def schedule_save(self):
            """Debounced auto-save"""
            if hasattr(self, '_save_timer'):
                self.root.after_cancel(self._save_timer)
            self._save_timer = self.root.after(1000, self.save_current_page)  # 1 sec delay

        def save_current_page(self):
            """Save current page content — only if it's a subpage (text editor)"""
            if not self.current_editor or not self.current_node_id:
                return
    
            # Only save text content if it's a subpage editor
            if hasattr(self.current_editor, 'text_area'):
                text = self.current_editor.text_area
                content = text.get("1.0", "end-1c")
                
                tags = {}
                for tag_name in ['bold', 'italic', 'underline', 'highlight', 'code_block']:
                    ranges = text.tag_ranges(tag_name)
                    if ranges:
                        tags[tag_name] = [[str(ranges[i]), str(ranges[i+1])] for i in range(0, len(ranges), 2)]

                # Save dynamic font_ and size_ tags
                all_tags = text.tag_names()
                for tag_name in all_tags:
                    if tag_name.startswith('font_') or tag_name.startswith('size_'):
                        ranges = text.tag_ranges(tag_name)
                        if ranges:
                            if tag_name not in tags:
                                tags[tag_name] = []
                            tags[tag_name].extend([[str(ranges[i]), str(ranges[i+1])] for i in range(0, len(ranges), 2)])
                
                dump_data = {'content': content, 'tags': tags}
                save_subpage(self.current_node_id, dump_data)
                
                # Update media positions (only for text editor)
                for window_name in text.window_names():
                    try:
                        widget = text.nametowidget(window_name)
                        if hasattr(widget, 'media_id'):
                            pos = text.index(window_name)
                            from backend.database import update_media_position
                            update_media_position(widget.media_id, pos)
                    except Exception as e:
                        print(f"Failed to update media pos: {e}")
            else:
                # If it's a flowchart → call its save method instead
                if hasattr(self.current_editor, 'save_flowchart'):
                    self.current_editor.save_flowchart(self.current_node_id)
                # Optional: add else for future types

    # Create UI
    # Create UI in a separate window
    window = tk.Toplevel()
    window.title(project_data.get('title', 'Project') if project_data else "Project")
    window.geometry("1000x700")
    window.minsize(800, 500)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "data", "tarizzlogo.png")
    if os.path.exists(logo_path):
        window.logo = PhotoImage(file=logo_path)
        window.iconphoto(False, window.logo)


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
