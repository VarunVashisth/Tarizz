"""Native, formatted clipboard ingestion for Tarizz."""
from html.parser import HTMLParser
import ctypes
import os
import subprocess
import sys
import tkinter as tk


class _HTMLText(HTMLParser):
    BLOCKS = {'p', 'div', 'h1', 'h2', 'h3', 'li', 'pre', 'blockquote'}
    STYLE = {'strong':'bold', 'b':'bold', 'em':'italic', 'i':'italic', 'u':'underline',
             'code':'inline_code', 'pre':'inline_code', 'blockquote':'quote',
             'h1':'heading1', 'h2':'heading2', 'h3':'heading3', 's':'strike', 'del':'strike'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.stack, self.ranges = '', [], []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.BLOCKS and self.text and not self.text.endswith('\n'):
            self.text += '\n'
        if tag == 'li':
            self.text += '• '
        elif tag == 'br':
            self.text += '\n'
        if tag in self.STYLE:
            self.stack.append((tag, self.STYLE[tag], len(self.text)))

    def handle_endtag(self, tag):
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            opened, style, start = self.stack[index]
            if opened == tag:
                self.stack.pop(index)
                if len(self.text) > start:
                    self.ranges.append((style, start, len(self.text)))
                break
        if tag in self.BLOCKS and self.text and not self.text.endswith('\n'):
            self.text += '\n'

    def handle_data(self, data):
        self.text += data.replace('\r\n', '\n').replace('\r', '\n')


def _tk_html(widget):
    targets = []
    try:
        raw = widget.selection_get(selection='CLIPBOARD', type='TARGETS')
        targets = widget.tk.splitlist(raw)
    except tk.TclError:
        pass
    candidates = [t for t in targets if 'html' in str(t).lower()]
    candidates += ['text/html;charset=utf-8', 'text/html', 'HTML Format']
    for target in dict.fromkeys(candidates):
        try:
            value = widget.selection_get(selection='CLIPBOARD', type=target)
            if value and '<' in value:
                return value
        except (tk.TclError, TypeError):
            continue
    return None


def _wayland_html():
    if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('XDG_SESSION_TYPE') == 'wayland'):
        return None
    try:
        result = subprocess.run(['wl-paste', '--no-newline', '--type', 'text/html'],
                                capture_output=True, timeout=2, check=False)
        if result.returncode == 0:
            value = result.stdout.decode('utf-8', errors='replace')
            return value if '<' in value else None
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _windows_html():
    if sys.platform != 'win32':
        return None
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    fmt = user32.RegisterClipboardFormatW('HTML Format')
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(fmt)
        if not handle:
            return None
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return None
        try:
            raw = ctypes.string_at(pointer, kernel32.GlobalSize(handle)).rstrip(b'\0')
            value = raw.decode('utf-8', errors='replace')
            marker = value.find('<')
            return value[marker:] if marker >= 0 else None
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def get_clipboard_html(widget):
    return _windows_html() or _wayland_html() or _tk_html(widget)


def paste_with_formatting(widget, formatter):
    html = get_clipboard_html(widget)
    if not html:
        return False
    parser = _HTMLText()
    try:
        parser.feed(html)
    except Exception:
        return False
    value = parser.text.rstrip('\n')
    if not value:
        return False
    try:
        if widget.tag_ranges('sel'):
            widget.delete('sel.first', 'sel.last')
        start = widget.index('insert')
        widget.insert(start, value)
        for style, begin, end in parser.ranges:
            first, last = f'{start}+{begin}c', f'{start}+{min(end, len(value))}c'
            if style.startswith('heading'):
                size = {'heading1': 22, 'heading2': 18, 'heading3': 15}[style]
                formatter._apply_combined_font(first, last, formatter.default_family, size, 'bold', 'roman')
            else:
                widget.tag_add(style, first, last)
        widget.mark_set('insert', f'{start}+{len(value)}c')
        return True
    except tk.TclError:
        return False
