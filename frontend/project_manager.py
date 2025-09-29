# project_manager.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from simple_text_editor import create_text_editor
import fitz
import webbrowser
import subprocess
import os
import platform
import cv2
from PIL import Image, ImageTk
import shutil
import io
from flowchart import FlowchartEditor

def open_file_with_default_app(filepath):
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        os.system(f'open "{filepath}"')
    else:
        os.system(f'xdg-open "{filepath}"')

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
            style.theme_use('default')
            style.configure('Sidebar.TFrame', background='#222222')  # matte black
            style.configure('Sidebar.Treeview', background='#222222', fieldbackground='#222222', borderwidth=0 ,foreground='#cccccc', relief='flat')
            style.configure('Sidebar.TButton', background='#222222', foreground='#cccccc')
            style.map(
                    'Sidebar.Treeview',
                    background=[('selected', '#333333')],
                    foreground=[('selected', '#ffffff')]
                )

            self.tree = ttk.Treeview(self.sidebar, style='Sidebar.Treeview', show='tree')
            self.tree.pack(fill='both', expand=True)
            self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

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
            
            btn_frame = tk.Frame(self.sidebar, bg='#222222')
            btn_frame.pack(fill='x', pady=4)
            
            tk.Button(btn_frame, text="Add Folder", command=self.add_folder, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Add Subpage", command=self.add_subpage, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Add Flowchart", command=self.add_flowchart, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Rename", command=self.rename_item, **btn_style).pack(fill='x', pady=2)
            tk.Button(btn_frame, text="Delete", command=self.delete, **btn_style).pack(fill='x', pady=2)

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

        def add_flowchart(self):
            selected = self.tree.selection()
            if not selected: return
            parent_id = selected[0]
            parent_data = self.get_node_data(parent_id)
            if parent_data is None: return
            name = simpledialog.askstring("Flowchart Name","Enter Flowchart name:")
            if name:
                # Check for duplicate Flowchart name in the same folder
                if name in parent_data:
                    messagebox.showerror("Error", f"Flowchart '{name}' already exists in this folder.")
                    return
                parent_data[name] = "flowchart"  # Flowchart is None or file path
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

        # Inside your ProjectManager class, add this method:

        def rename_item(self):
            selected = self.tree.selection()
            if not selected:
                return
            item_id = selected[0]
            old_name = self.tree.item(item_id)['text']
            parent_id = self.tree.parent(item_id)
            parent_data = self.get_node_data(parent_id)
            if parent_data is None:
                return
            
            new_name = simpledialog.askstring("Rename", f"Enter new name for '{old_name}':")
            if not new_name:
                return
            if new_name in parent_data:
                messagebox.showerror("Error", f"An item named '{new_name}' already exists here.")
                return
            
            # Preserve existing value (subpage None, flowchart None, folder dict)
            parent_data[new_name] = parent_data.pop(old_name)
            
            # Update tree text
            self.tree.item(item_id, text=new_name)


        def on_tree_select(self, event):
            selected = self.tree.selection()
            if not selected: return
            item_id = selected[0]
            item_text = self.tree.item(item_id)['text']
            parent_id = self.tree.parent(item_id)
            parent_data = self.get_node_data(parent_id)
            if parent_data is None: return  # folder or root clicked
        
            node_data = parent_data.get(item_text)
            if isinstance(node_data, dict):
                return  # folder
            elif node_data == "flowchart":
                self.open_flowchart_editor(item_text)  # pass the name
            else:
                self.open_editor(parent_data, item_text)         

                
        def open_flowchart_editor(self, flowchart_data):
            if self.current_editor_frame:
                self.current_editor_frame.destroy()
            self.current_editor_frame = ttk.Frame(self.editor_container)
            self.current_editor_frame.pack(fill="both", expand=True)
            self.current_editor = FlowchartEditor(self.current_editor_frame)
            self.current_editor.pack(fill="both", expand=True)

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

                toolbar = tk.Frame(frame, bg='#222222')
                toolbar.pack(fill='x', padx=8, pady=8, side='top')

                editor = create_text_editor(parent=frame)
                self.current_editor = editor



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
                font_size_menu = tk.OptionMenu(toolbar, font_size_var, *[10, 12, 14, 16, 18, 20, 24, 32 , 38, 42 , 47, 50], command=on_font_size_change)
                font_size_menu.config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10), relief='flat', bd=0, highlightthickness=0, activebackground='#333333', activeforeground='#ffffff')
                font_size_menu['menu'].config(bg='#222222', fg='#cccccc', font=('Segoe UI', 10))
                font_size_menu.pack(side='left', padx=4)

                insert_img_btn = tk.Button(toolbar, text="Insert Image", command=editor.upload_image, **btn_style)
                insert_img_btn.pack(side='left', padx=4)

                def insert_video_embed():
                    file_path = tk.filedialog.askopenfilename(
                        filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")]
                    )
                    if file_path:
                        # Try to get a thumbnail from the video
                        try:
                            cap = cv2.VideoCapture(file_path)
                            ret, frame = cap.read()
                            cap.release()
                            if ret:
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                img = Image.fromarray(frame)
                                img.thumbnail((360, 240))
                                img_tk = ImageTk.PhotoImage(img)
                            else:
                                img_tk = None
                        except Exception:
                            img_tk = None

                        # Create a frame for the embedded video widget
                        video_frame = tk.Frame(editor.text_area, bg='#222222', bd=0)
                        # Thumbnail or fallback
                        if img_tk:
                            thumb_label = tk.Label(video_frame, image=img_tk, bg='#222222')
                            thumb_label.image = img_tk  # Keep reference
                            thumb_label.pack(side='left')
                        else:
                            thumb_label = tk.Label(video_frame, text="No Preview", bg='#222222', fg='#cccccc', width=66, height=21)
                            thumb_label.pack(side='left')

                        # Play button
                        play_btn = tk.Button(video_frame, text="▶ Play", bg='#00bfff', fg='white', relief='flat', font=('Segoe UI', 10, 'bold'), cursor='hand2')
                        play_btn.pack(side='left', padx=8)

                        # Download button
                        download_btn = tk.Button(video_frame, text="⬇ Download", bg='#222222', fg='#00bfff', relief='flat', font=('Segoe UI', 10), cursor='hand2')
                        download_btn.pack(side='left', padx=4)

                        def play_video():
                            # Open a simple player window using OpenCV
                            win = tk.Toplevel(editor.text_area)
                            win.title("Video Player")
                            win.geometry("1920x800")
                            label = tk.Label(win)
                            label.pack(fill='both', expand=True)
                            cap = cv2.VideoCapture(file_path)

                            vid_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            vid_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            aspect_ratio = vid_width / vid_height

                            target_width, target_height = 1920, 1800
                            # Calculate new size keeping aspect ratio
                            if target_width / target_height > aspect_ratio:
                                # window is wider → fit by height
                                new_height = target_height
                                new_width = int(target_height * aspect_ratio)
                            else:
                                # window is taller → fit by width
                                new_width = target_width
                                new_height = int(target_width / aspect_ratio)                            
                            def show_frame():
                                ret, frame = cap.read()
                                if ret:
                                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(frame)
                                    img = img.resize((new_width, new_height), Image.LANCZOS , Image.ANTIALIAS)
                                    img_tk = ImageTk.PhotoImage(img)
                                    label.imgtk = img_tk
                                    label.config(image=img_tk)
                                    win.after(30, show_frame)
                                else:
                                    cap.release()
                            show_frame()
                            win.protocol("WM_DELETE_WINDOW", lambda: (cap.release(), win.destroy()))

                        def download_video():
                            save_path = tk.filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All files", "*.*")])
                            if save_path:
                                shutil.copy(file_path, save_path)
                                messagebox.showinfo("Download", f"Video saved to:\n{save_path}")

                        play_btn.config(command=play_video)
                        download_btn.config(command=download_video)

                        editor.text_area.window_create(tk.INSERT, window=video_frame)

                # Replace previous Insert Video button with embedded version
                insert_video_btn = tk.Button(
                    toolbar, text="Insert Video",
                    command=insert_video_embed,
                    **btn_style
                )
                insert_video_btn.pack(side='left', padx=4)

                # Insert PDF button
                def insert_media(filetypes, placeholder):
                    file_path = tk.filedialog.askopenfilename(filetypes=filetypes)
                    if not file_path:
                        return
                
                    # Insert placeholder text (optional)
                    editor.text_area.insert(tk.INSERT, f"[{placeholder}: {os.path.basename(file_path)}]\n")
                
                    try:
                        # Open PDF and get first page
                        media = fitz.open(file_path)
                        page = media[0]
                        zoom = 1.5
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat)
                
                        # Convert pixmap to PIL Image
                        img_data = pix.tobytes("png")  # Get raw PNG bytes
                        image = Image.open(io.BytesIO(img_data))
                
                        # Optionally resize to a thumbnail
                        image.thumbnail((300, 400))  # Keep aspect ratio
                        tk_img = ImageTk.PhotoImage(image)
                
                        # Create a frame and add thumbnail inside Text widget
                        media_frame = tk.Frame(editor.text_area, bg='#222222', bd=0)
                        thumb_label = tk.Label(media_frame, image=tk_img, bg='#222222')
                        thumb_label.image = tk_img  # Prevent garbage collection
                        thumb_label.pack(side='left', padx=2, pady=2)
                
                        # Embed frame inside the text widget
                        editor.text_area.window_create(tk.INSERT, window=media_frame)
                        thumb_label.bind("<Button-1>", lambda e, path=file_path: open_file(path))
                
                    except Exception as e:
                        print("Error rendering PDF:", e)
                        # Fallback: just insert text
                        editor.text_area.insert(tk.INSERT, "[PDF Preview not available]\n")

                    download_btn = tk.Button(media_frame, text="⬇ Download", bg='#222222', fg='#00bfff', relief='flat', font=('Segoe UI', 10), cursor='hand2')
                    download_btn.pack(side='left', padx=4)
                    
                    def download_media():
                            save_path = tk.filedialog.asksaveasfilename(defaultextension=".pdf ", filetypes=[("Pdf files", "*.pdf"),("DOC" , "*.docx"), ("All files", "*.*")])
                            if save_path:
                                shutil.copy(file_path, save_path)
                                messagebox.showinfo("Download", f"Document saved to:\n{save_path}")

                    download_btn.config(command=download_media)
                    
                    def open_file(file_path):
                        try:
                            if os.name == 'nt':
                                os.startfile(file_path)
                            elif os.name == 'posix':
                                subprocess.run(['xdg-open',file_path], check=False) 
                            elif sys.platform.startswith('darwin'):
                                subprocess.run(['open',file_path], check=False)
                            else:
                                messagebox.showerror("Error","Unsupported OS for opening files.")
                        except Exception as e:
                            messagebox.showerror("Error",f"Failed to open file:\n{e}")


                    
                insert_pdf_btn = tk.Button(
                    toolbar, text="Insert PDF",
                    command=lambda: insert_media(
                        [("PDF files", "*.pdf"), ("All files", "*.*")],
                        "📄 PDF"
                    ),
                    **btn_style
                )
                insert_pdf_btn.pack(side='left', padx=4)

                # Insert Docs button
                insert_docs_btn = tk.Button(
                    toolbar, text="Insert Docs",
                    command=lambda: insert_media(
                        [("Word files", "*.doc *.docx"), ("All files", "*.*")],
                        "📄 DOC"
                    ),
                    **btn_style
                )
                insert_docs_btn.pack(side='left', padx=4)
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
