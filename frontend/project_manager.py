# project_manager.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
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

            # Load content from database
            content = load_subpage(node_id)
            if content:
                editor.text_area.delete("1.0", "end")
                editor.text_area.insert("1.0", content or "")

            # Bind auto-save
            editor.text_area.bind('<KeyRelease>', lambda e: self.schedule_save())
            editor.text_area.bind('<FocusOut>', lambda e: self.save_current_page())

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
            
            # Get text widget content
#            content = self.current_editor.text_area.content('1.0', 'end', 
#                                                      text=True, tag=True, mark=True, window=True)
#            
#            # Save to database (encrypted automatically)
#            save_subpage(self.current_node_id, content)

            content = self.current_editor.text_area.get("1.0", "end-1c")
            save_subpage(self.current_node_id, content)

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