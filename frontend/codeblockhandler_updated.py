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
            'background': '#0d1117',
            'foreground': '#c9d1d9',
            'font': ('Courier New', 10),
            'lmargin1': 16, 'lmargin2': 16,
            'rmargin': 8,
            'spacing1': 6, 'spacing3': 6,
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
        )
    
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
            
            # Find all code block matches and apply tag
            for match in re.finditer(self.CODE_BLOCK_PATTERN, content, re.DOTALL):
                start_idx = f"1.0 + {match.start()} chars"
                end_idx = f"1.0 + {match.end()} chars"
                self.text.tag_add('code_block', start_idx, end_idx)
        except tk.TclError:
            pass