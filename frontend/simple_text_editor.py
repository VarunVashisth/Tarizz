# simple_text_editor.py
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import fitz
import cv2
import os
from io import BytesIO
import re

class SimpleTextEditor:
    def __init__(self, parent=None):
        """If parent is None, creates standalone window, else embeds in parent frame"""
        self.embedded_in_frame = parent is not None
        self.root = parent if parent else tk.Toplevel()
        if not self.embedded_in_frame:
            self.root.title("Text Editor")
            self.root.geometry("900x700")
        self.current_file = None
        self.embedded_media = []
        self.embedded_widgets = []
        self.selected_widget = None
        self.create_ui()
        # Removed menu bar creation
        self.text_area.bind('<KeyRelease>', self.check_code_blocks)
        self.bind_hotkeys()

    def create_ui(self):
        self.text_area = tk.Text(
            self.root,
            bg='#1a1a1a',
            fg='#e0e0e0',
            insertbackground='#ffffff',
            selectbackground='#404040',
            selectforeground='#ffffff',
            font=('Consolas', 12),
            wrap='word',
            relief='flat',
            borderwidth=0,
            padx=15,
            pady=15
        )
        self.text_area.pack(fill='both', expand=True)
        self.text_area.tag_configure('code_block', background='#2d2d2d', foreground='#00ff88', font=('Courier', 11))

        # Add tags for formatting
        self.text_area.tag_configure('bold', font=('Consolas', 12, 'bold'))
        self.text_area.tag_configure('italic', font=('Consolas', 12, 'italic'))
        self.text_area.tag_configure('underline', font=('Consolas', 12, 'underline'))
        self.text_area.tag_configure('heading', font=('Consolas', 18, 'bold'))
        self.text_area.tag_configure('subheading', font=('Consolas', 14, 'bold'))
        self.text_area.tag_configure('normal', font=('Consolas', 12, 'normal'))

    def bind_hotkeys(self):
        # File operations
        self.root.bind('<Control-n>', lambda e: self.new_file())
        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<Control-S>', lambda e: self.save_as_file())
        # Text formatting
        self.text_area.bind('<Control-a>', self.select_all)
        self.text_area.bind('<Control-b>', self.make_bold)
        self.text_area.bind('<Control-i>', self.upload_image)  # Changed to image upload
        self.text_area.bind('<Control-u>', self.make_underline)
        self.text_area.bind('<Control-1>', self.make_heading)
        self.text_area.bind('<Control-2>', self.make_subheading)
        self.text_area.bind('<Control-3>', self.make_normal)
        # Font change hotkey example (Ctrl+Shift+F)
        self.text_area.bind('<Control-Shift-F>', self.change_font)

    def select_all(self, event=None):
        self.text_area.tag_add('sel', '1.0', 'end-1c')
        return 'break'

    def make_bold(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            # Toggle bold: remove if present, add if not
            if 'bold' in self.text_area.tag_names('sel.first'):
                self.text_area.tag_remove('bold', start, end)
            else:
                self.text_area.tag_add('bold', start, end)
        except tk.TclError:
            pass
        return 'break'

    def make_italic(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            if 'italic' in self.text_area.tag_names('sel.first'):
                self.text_area.tag_remove('italic', start, end)
            else:
                self.text_area.tag_add('italic', start, end)
        except tk.TclError:
            pass
        return 'break'

    def make_underline(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            if 'underline' in self.text_area.tag_names('sel.first'):
                self.text_area.tag_remove('underline', start, end)
            else:
                self.text_area.tag_add('underline', start, end)
        except tk.TclError:
            pass
        return 'break'

    def make_heading(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            self.text_area.tag_remove('subheading', start, end)
            self.text_area.tag_remove('normal', start, end)
            self.text_area.tag_add('heading', start, end)
        except tk.TclError:
            pass
        return 'break'

    def make_subheading(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            self.text_area.tag_remove('heading', start, end)
            self.text_area.tag_remove('normal', start, end)
            self.text_area.tag_add('subheading', start, end)
        except tk.TclError:
            pass
        return 'break'

    def make_normal(self, event=None):
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            self.text_area.tag_remove('heading', start, end)
            self.text_area.tag_remove('subheading', start, end)
            self.text_area.tag_add('normal', start, end)
        except tk.TclError:
            pass
        return 'break'

    # Simple file operations (you can expand to include media support)
    def new_file(self):
        self.text_area.delete('1.0', tk.END)
        self.current_file = None

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files","*.txt")])
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.text_area.delete('1.0', tk.END)
            self.text_area.insert('1.0', content)
            self.current_file = file_path

    def save_file(self):
        if self.current_file:
            self.write_file(self.current_file)
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files","*.txt")])
        if file_path:
            self.write_file(file_path)
            self.current_file = file_path

    def write_file(self, file_path):
        content = self.text_area.get('1.0', 'end-1c')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def check_code_blocks(self, event=None):
        content = self.text_area.get('1.0', tk.END)
        self.text_area.tag_remove('code_block','1.0',tk.END)
        for match in re.finditer(r"'''(.*?)'''", content, re.DOTALL):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add('code_block', start, end)

    def upload_image(self, event=None):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            try:
                img = Image.open(file_path)
                img.thumbnail((300, 300))
                img_tk = ImageTk.PhotoImage(img)
                self.text_area.image_create(tk.INSERT, image=img_tk)
                # Keep reference to avoid garbage collection
                self.embedded_media.append(img_tk)
            except Exception as e:
                messagebox.showerror("Image Error", f"Failed to insert image: {e}")
        return 'break'

    def change_font(self, event=None, font_family='Consolas', font_size=12):
        # Example: change font family and size for selected text
        try:
            start, end = self.text_area.index('sel.first'), self.text_area.index('sel.last')
            tag_name = f"custom_font_{font_family}_{font_size}"
            self.text_area.tag_configure(tag_name, font=(font_family, font_size))
            self.text_area.tag_add(tag_name, start, end)
        except tk.TclError:
            pass
        return 'break'

def create_text_editor(parent=None):
    """Function to create a TextEditor, optionally embedded in a frame"""
    return SimpleTextEditor(parent)
