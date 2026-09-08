"""Small dependency-free Markdown preview for Tkinter."""
import re
import tkinter as tk


def show_markdown_preview(parent, source, title='Markdown preview'):
    window = tk.Toplevel(parent)
    window.title(title)
    window.geometry('850x650')
    window.configure(bg='#111827')
    text = tk.Text(window, wrap='word', bg='#111827', fg='#e5e7eb', relief='flat',
                   padx=32, pady=26, font=('Segoe UI', 11), cursor='arrow')
    text.pack(fill='both', expand=True, padx=12, pady=12)
    text.tag_configure('h1', font=('Segoe UI', 24, 'bold'), foreground='#f9fafb', spacing1=14, spacing3=10)
    text.tag_configure('h2', font=('Segoe UI', 19, 'bold'), foreground='#f9fafb', spacing1=12, spacing3=8)
    text.tag_configure('h3', font=('Segoe UI', 15, 'bold'), foreground='#f9fafb', spacing1=10, spacing3=6)
    text.tag_configure('quote', foreground='#9ca3af', lmargin1=20, lmargin2=20)
    text.tag_configure('code', font=('TkFixedFont', 10), background='#1f2937', foreground='#93c5fd',
                       lmargin1=14, lmargin2=14, spacing1=5, spacing3=5)
    text.tag_configure('bold', font=('Segoe UI', 11, 'bold'))
    text.tag_configure('italic', font=('Segoe UI', 11, 'italic'))
    text.tag_configure('link', foreground='#60a5fa', underline=True)
    in_fence = False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        start = text.index('end-1c')
        tag = None
        rendered = line
        if in_fence:
            tag = 'code'
        elif line.startswith('### '):
            rendered, tag = line[4:], 'h3'
        elif line.startswith('## '):
            rendered, tag = line[3:], 'h2'
        elif line.startswith('# '):
            rendered, tag = line[2:], 'h1'
        elif line.startswith('> '):
            rendered, tag = line[2:], 'quote'
        elif re.match(r'^\s*[-*+] ', line):
            rendered = re.sub(r'^(\s*)[-*+] ', r'\1•  ', line)
        text.insert('end', rendered + '\n', tag or ())
        if not tag:
            _inline_tags(text, start, rendered)
    text.configure(state='disabled')
    return window


def _inline_tags(widget, line_start, rendered):
    patterns = [
        (r'\*\*(.+?)\*\*', 'bold'),
        (r'(?<!\*)\*([^*]+?)\*(?!\*)', 'italic'),
        (r'`([^`]+)`', 'code'),
        (r'\[([^]]+)\]\([^)]+\)', 'link'),
    ]
    for pattern, tag in patterns:
        for match in re.finditer(pattern, rendered):
            widget.tag_add(tag, f'{line_start}+{match.start()}c', f'{line_start}+{match.end()}c')
