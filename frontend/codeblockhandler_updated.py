# codeblockhandler.py (UPDATED)
"""
Code block detector and styler with multiple theme options.
"""

import re
import tkinter as tk
from tkinter import font as tkFont


class CodeBlockHandler:
    """
    Detects code blocks (text between ''') and applies styling.
    Supports multiple themes for code block styling.
    """
    
    CODE_BLOCK_PATTERN = r"'''(.*?)'''"
    
    # Theme options
    THEMES = {
        'github_dark': {
            'background': '#0b1220',
            'foreground': '#d7e0ea',
            'font': ('Cascadia Code', 10),
            'lmargin1': 24, 'lmargin2': 24,
            'rmargin': 18,
            'spacing1': 10, 'spacing3': 10,
        },
        'monokai': {
            'background': '#272822',
            'foreground': '#f8f8f2',
            'font': ('Courier New', 11),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'dracula': {
            'background': '#282a36',
            'foreground': '#f8f8f2',
            'font': ('Consolas', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'nord': {
            'background': '#2e3440',
            'foreground': '#eceff4',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'solarized': {
            'background': '#002b36',
            'foreground': '#839496',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'one_dark': {
            'background': '#282c34',
            'foreground': '#abb2bf',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'material': {
            'background': '#263238',
            'foreground': '#eeffff',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'tomorrow': {
            'background': '#2d2d2d',
            'foreground': '#cccccc',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
        'light': {
            'background': '#f5f5f5',
            'foreground': '#383a42',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
        },
    }
    
    def __init__(self, text_widget, theme='github_dark'):
        """
        Initialize the CodeBlockHandler.
        
        Args:
            text_widget: The tkinter Text widget
            theme: Theme name (default: 'github_dark')
                  Options: github_dark, monokai, dracula, nord, solarized, 
                          one_dark, material, tomorrow, light
        """
        self.text = text_widget
        self.theme = theme if theme in self.THEMES else 'github_dark'
        self.setup_tags()
    
    def setup_tags(self):
        """Configure the code_block tag with theme styling"""
        style = self.THEMES[self.theme]
        
        try:
            # Check if code_block tag already exists
            self.text.tag_cget('code_block', 'foreground')
        except tk.TclError:
            # Tag doesn't exist, create it
            pass
        
        # Configure with theme style
        self.text.tag_configure(
            'code_block',
            font=tkFont.Font(
                family=style['font'][0],
                size=style['font'][1]
            ),
            background=style['background'],
            foreground=style['foreground'],
            lmargin1=style.get('lmargin1', 16),
            lmargin2=style.get('lmargin2', 16),
            rmargin=style.get('rmargin', 8),
            spacing1=style.get('spacing1', 6),
            spacing3=style.get('spacing3', 6),
            wrap='word'
            , relief='flat', borderwidth=1,
            tabs=('2c', '4c', '6c', '8c')
        )
        self.text.tag_configure(
            'code_delimiter',
            elide=True,
        )
        self.text.tag_configure('code_keyword', foreground='#ff7b72')
        self.text.tag_configure('code_string', foreground='#a5d6ff')
        self.text.tag_configure('code_comment', foreground='#8b949e')
        self.text.tag_configure('code_number', foreground='#79c0ff')
        # Highlight sits under code styling so yellow never overwrites code colors.
        try:
            self.text.tag_lower('highlight')
        except tk.TclError:
            pass
        self.text.tag_raise('code_block')
    
    def change_theme(self, theme):
        """Change the code block theme at runtime."""
        if theme in self.THEMES:
            self.theme = theme
            self.setup_tags()
            # Retag existing code blocks
            self.apply_code_block_styling()
    
    def apply_code_block_styling(self, event=None):
        """
        Detect ''' ''' blocks and apply code_block tag.
        Safe to call from event bindings.
        """
        try:
            content = self.text.get('1.0', tk.END)
            
            # Remove existing code_block tags
            self.text.tag_remove('code_block', '1.0', tk.END)
            self.text.tag_remove('code_delimiter', '1.0', tk.END)
            for syntax_tag in ('code_keyword', 'code_string', 'code_comment', 'code_number'):
                self.text.tag_remove(syntax_tag, '1.0', tk.END)
            
            # Find all code block matches and apply tag
            for match in re.finditer(self.CODE_BLOCK_PATTERN, content, re.DOTALL):
                open_start = f"1.0 + {match.start()} chars"
                code_start = f"1.0 + {match.start() + 3} chars"
                code_end = f"1.0 + {match.end() - 3} chars"
                close_end = f"1.0 + {match.end()} chars"
                self.text.tag_add('code_delimiter', open_start, code_start)
                self.text.tag_add('code_block', code_start, code_end)
                self.text.tag_add('code_delimiter', code_end, close_end)
                code = match.group(1)
                base = match.start() + 3
                patterns = (
                    ('code_comment', r'(?m)(#|//).*?$'),
                    ('code_string', r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')'),
                    ('code_number', r'\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b'),
                    ('code_keyword', r'\b(?:and|as|async|await|break|case|catch|class|const|continue|def|do|else|elif|except|export|false|finally|for|from|function|if|import|in|is|let|new|none|null|or|pass|raise|return|switch|throw|true|try|var|while|with|yield)\b'),
                )
                for syntax_tag, pattern in patterns:
                    for token in re.finditer(pattern, code, re.IGNORECASE):
                        token_start = f"1.0 + {base + token.start()} chars"
                        token_end = f"1.0 + {base + token.end()} chars"
                        self.text.tag_add(syntax_tag, token_start, token_end)
            try:
                self.text.tag_lower('highlight')
                self.text.tag_raise('code_block')
                self.text.tag_raise('code_delimiter')
                # Broad tokens first; strings/comments win when ranges overlap.
                for syntax_tag in ('code_keyword', 'code_number', 'code_string', 'code_comment'):
                    self.text.tag_raise(syntax_tag)
            except tk.TclError:
                pass
        except tk.TclError:
            pass
