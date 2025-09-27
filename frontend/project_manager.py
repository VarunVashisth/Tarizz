# project_manager.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from simple_text_editor import create_text_editor

def create_project_manager(parent, project_data=None):
    class ProjectManager:
        def __init__(self, parent, project_data):
            self.root = parent
            self.project_data = project_data if project_data is not None else {}

            # Sidebar
            self.sidebar = ttk.Frame(self.root, width=250)
            self.sidebar.pack(side='left', fill='y')
            self.sidebar.configure(style='Sidebar.TFrame')

            style = ttk.Style()
            style.configure('Sidebar.TFrame', background='#222222')  # matte black
            style.configure('Sidebar.Treeview', background='#222222', fieldbackground='#222222', foreground='#cccccc')
            style.configure('Sidebar.TButton', background='#222222', foreground='#cccccc')

            self.tree = ttk.Treeview(self.sidebar, style='Sidebar.Treeview', show='tree')
            self.tree.pack(fill='both', expand=True)
            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

            btn_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
            btn_frame.pack(fill='x')
            ttk.Button(btn_frame, text="Add Folder", command=self.add_folder, style='Sidebar.TButton').pack(fill='x')
            ttk.Button(btn_frame, text="Add Subpage", command=self.add_subpage, style='Sidebar.TButton').pack(fill='x')
            ttk.Button(btn_frame, text="Delete", command=self.delete, style='Sidebar.TButton').pack(fill='x')

            # Editor container
            self.editor_container = ttk.Frame(self.root)
            self.editor_container.pack(side='left', fill='both', expand=True)

            self.current_editor = None
            self.current_editor_frame = None  # Track the editor frame
            self.current_page = None
            self.root_node = self.tree.insert("", "end", text="Projects", open=True)

        def get_node_data(self, item_id):
            """Return the dict in project_data for the given tree item."""
            # Traverse from root to item, following names
            names = []
            while item_id and item_id != self.root_node:
                names.insert(0, self.tree.item(item_id)['text'])
                item_id = self.tree.parent(item_id)
            data = self.project_data
            for name in names:
                if name in data:
                    data = data[name]
                else:
                    return None
            return data

        def add_folder(self):
            selected = self.tree.selection()
            parent_id = selected[0] if selected else self.root_node
            parent_data = self.get_node_data(parent_id)
            # Only allow adding folder if parent_data is a dict (folder or root)
            if parent_data is None or not isinstance(parent_data, dict):
                messagebox.showerror("Error", "Cannot add a folder under a subpage.")
                return
            name = simpledialog.askstring("Folder Name","Enter folder name:")
            if name and name not in parent_data:
                parent_data[name] = {}  # folder is a dict
                self.tree.insert(parent_id, "end", text=name, open=True)

        def add_subpage(self):
            selected = self.tree.selection()
            if not selected: return
            parent_id = selected[0]
            parent_data = self.get_node_data(parent_id)
            if parent_data is None: return
            name = simpledialog.askstring("Subpage Name","Enter subpage name:")
            if name:
                # Check for duplicate subpage name in the same folder
                if name in parent_data:
                    messagebox.showerror("Error", f"Subpage '{name}' already exists in this folder.")
                    return
                parent_data[name] = None  # subpage is None or file path
                self.tree.insert(parent_id, "end", text=name)

        def delete(self):
            selected = self.tree.selection()
            if not selected: return
            item_id = selected[0]
            item_text = self.tree.item(item_id)['text']
            parent_id = self.tree.parent(item_id)
            parent_data = self.get_node_data(parent_id)
            if parent_data and item_text in parent_data:
                del parent_data[item_text]
            self.tree.delete(item_id)

        def on_tree_select(self, event):
            selected = self.tree.selection()
            if not selected: return
            item_id = selected[0]
            item_text = self.tree.item(item_id)['text']
            parent_id = self.tree.parent(item_id)
            parent_data = self.get_node_data(parent_id)
            if parent_data is None: return  # root or folder clicked
            node_data = parent_data.get(item_text)
            if isinstance(node_data, dict):
                # Folder selected, do not open editor
                return
            # Subpage selected, open editor
            self.open_editor(parent_data, item_text)

        def open_editor(self, folder_data, page):
            # Ensure 'Projects' key exists in folder_data
            if 'Projects' not in folder_data:
                folder_data['Projects'] = {}

            if page in folder_data:
                file_path = folder_data[page]
                if self.current_editor_frame:
                    self.current_editor_frame.destroy()
                    self.current_editor_frame = None
                self.current_editor = None

                frame = tk.Frame(self.editor_container, bg='#222222')
                frame.pack(fill='both', expand=True)
                self.current_editor_frame = frame

                editor = create_text_editor(parent=frame)
                self.current_editor = editor

                toolbar = tk.Frame(frame, bg='#222222')
                toolbar.pack(fill='x', padx=8, pady=8, side='top')

                btn_style = {
                    'bg': '#222222',
                    'fg': '#cccccc',
                    'activebackground': '#333333',
                    'activeforeground': '#ffffff',
                    'relief': 'flat',
                    'bd': 0,
                    'font': ('Segoe UI', 10),
                    'highlightthickness': 0,
                    'padx': 12,
                    'pady': 6,
                    'cursor': 'hand2'
                }

                heading_btn = tk.Button(toolbar, text="Heading", command=editor.make_heading, **btn_style)
                heading_btn.pack(side='left', padx=(0, 4))
                subheading_btn = tk.Button(toolbar, text="Subheading", command=editor.make_subheading, **btn_style)
                subheading_btn.pack(side='left', padx=4)
                normal_btn = tk.Button(toolbar, text="Normal", command=editor.make_normal, **btn_style)
                normal_btn.pack(side='left', padx=4)

                font_families = ['Consolas', 'Segoe UI', 'Arial', 'Courier', 'Times']
                font_family_var = tk.StringVar(value='Consolas')
                def on_font_family_change(value):
                    editor.change_font(font_family=value, font_size=font_size_var.get())
                font_family_menu = tk.OptionMenu(toolbar, font_family_var, *font_families, command=on_font_family_change)
                font_family_menu.config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10), relief='flat', bd=0, highlightthickness=0, activebackground='#333333', activeforeground='#ffffff')
                font_family_menu['menu'].config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10))
                font_family_menu.pack(side='left', padx=4)

                font_size_var = tk.IntVar(value=12)
                def on_font_size_change(value):
                    editor.change_font(font_family=font_family_var.get(), font_size=int(value))
                font_size_menu = tk.OptionMenu(toolbar, font_size_var, *[10, 12, 14, 16, 18, 20, 24], command=on_font_size_change)
                font_size_menu.config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10), relief='flat', bd=0, highlightthickness=0, activebackground='#333333', activeforeground='#ffffff')
                font_size_menu['menu'].config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10))
                font_size_menu.pack(side='left', padx=4)

                insert_img_btn = tk.Button(toolbar, text="Insert Image", command=editor.upload_image, **btn_style)
                insert_img_btn.pack(side='left', padx=4)
                # --- End styled toolbar ---

                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        editor.text_area.insert('1.0', content)
                    except:
                        pass
                self.current_page = (folder_data, page)
                editor.text_area.bind('<FocusOut>', lambda e: self.save_current_page())
            elif page in folder_data.get('Projects', {}):
                file_path = folder_data['Projects'][page]
                if self.current_editor_frame:
                    self.current_editor_frame.destroy()
                    self.current_editor_frame = None
                self.current_editor = None

                frame = tk.Frame(self.editor_container, bg='#222222')
                frame.pack(fill='both', expand=True)
                self.current_editor_frame = frame

                editor = create_text_editor(parent=frame)
                self.current_editor = editor

                toolbar = tk.Frame(frame, bg='#222222')
                toolbar.pack(fill='x', padx=8, pady=8, side='top')

                btn_style = {
                    'bg': '#222222',
                    'fg': '#cccccc',
                    'activebackground': '#333333',
                    'activeforeground': '#ffffff',
                    'relief': 'flat',
                    'bd': 0,
                    'font': ('Segoe UI', 10),
                    'highlightthickness': 0,
                    'padx': 12,
                    'pady': 6,
                    'cursor': 'hand2'
                }

                heading_btn = tk.Button(toolbar, text="Heading", command=editor.make_heading, **btn_style)
                heading_btn.pack(side='left', padx=(0, 4))
                subheading_btn = tk.Button(toolbar, text="Subheading", command=editor.make_subheading, **btn_style)
                subheading_btn.pack(side='left', padx=4)
                normal_btn = tk.Button(toolbar, text="Normal", command=editor.make_normal, **btn_style)
                normal_btn.pack(side='left', padx=4)

                font_families = ['Consolas', 'Segoe UI', 'Arial', 'Courier', 'Times']
                font_family_var = tk.StringVar(value='Consolas')
                def on_font_family_change(value):
                    editor.change_font(font_family=value, font_size=font_size_var.get())
                font_family_menu = tk.OptionMenu(toolbar, font_family_var, *font_families, command=on_font_family_change)
                font_family_menu.config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10), relief='flat', bd=0, highlightthickness=0, activebackground='#333333', activeforeground='#ffffff')
                font_family_menu['menu'].config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10))
                font_family_menu.pack(side='left', padx=4)

                font_size_var = tk.IntVar(value=12)
                def on_font_size_change(value):
                    editor.change_font(font_family=font_family_var.get(), font_size=int(value))
                font_size_menu = tk.OptionMenu(toolbar, font_size_var, *[10, 12, 14, 16, 18, 20, 24], command=on_font_size_change)
                font_size_menu.config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10), relief='flat', bd=0, highlightthickness=0, activebackground='#333333', activeforeground='#ffffff')
                font_size_menu['menu'].config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10))
                font_size_menu.pack(side='left', padx=4)

                insert_img_btn = tk.Button(toolbar, text="Insert Image", command=editor.upload_image, **btn_style)
                insert_img_btn.pack(side='left', padx=4)
                # --- End styled toolbar ---

                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        editor.text_area.insert('1.0', content)
                    except:
                        pass
                self.current_page = (folder_data, page)
                editor.text_area.bind('<FocusOut>', lambda e: self.save_current_page())
            else:
                messagebox.showerror("Error", f"Page '{page}' not found in folder data.")
                return

        def save_current_page(self):
            if not self.current_editor or not self.current_page: return
            folder_data,page = self.current_page
            content = self.current_editor.text_area.get('1.0','end-1c')
            file_path = f"{page}.txt"
            with open(file_path,'w',encoding='utf-8') as f:
                f.write(content)
            folder_data[page] = file_path

    # Create a frame for the project manager UI
    frame = ttk.Frame(parent)
    frame.pack(fill='both', expand=True)
    ProjectManager(frame, project_data)
    return frame

# Usage example (remove or comment out for integration):
# if __name__ == "__main__":
#     root = tk.Tk()
#     root.geometry("1200x700")
#     create_project_manager(root)
#     root.mainloop()
#     root.geometry("1200x700")
#     create_project_manager(root)
#     root.mainloop()
#     root.geometry("1200x700")
#     create_project_manager(root)
#     root.mainloop()
#     root.geometry("1200x700")
#     create_project_manager(root)
#     root.mainloop()
