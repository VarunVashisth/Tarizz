# text_formatter.py
"""
Improved text formatting handler with compatible font/size/style combinations.
Fixes the issue where font and size changes reset each other.
"""

import tkinter as tk
from tkinter import font as tkFont


class TextFormatter:
    """
    Manages text formatting tags (bold, italic, font family, font size, etc.)
    with proper compatibility between different formatting options.
    """
    
    def __init__(self, text_widget):
        """Initialize the formatter."""
        self.text = text_widget
        self.default_font = ('Segoe UI', 11)
        self.setup_base_tags()
    
    def setup_base_tags(self):
        """Setup basic formatting tags"""
        self.text.tag_configure('bold', font=tkFont.Font(family='Segoe UI', size=11, weight='bold'))
        self.text.tag_configure('italic', font=tkFont.Font(family='Segoe UI', size=11, slant='italic'))
        self.text.tag_configure('underline', underline=True)
        self.text.tag_configure('highlight', background='#ffff99', foreground='#000000')
    
    def get_current_formatting(self, index):
        """
        Get current formatting at given index.
        Returns dict with font family, size, weight, slant, and tags.
        """
        tags = self.text.tag_names(index)
        
        family = 'Segoe UI'
        size = 11
        weight = 'normal'
        slant = 'roman'
        
        # Extract font family from font_* tags
        for tag in tags:
            if tag.startswith('font_'):
                family = tag.replace('font_', '').replace('_', ' ')
                break
        
        # Extract size from size_* tags
        for tag in tags:
            if tag.startswith('size_'):
                try:
                    size = int(tag.replace('size_', ''))
                except ValueError:
                    pass
                break
        
        # Check for bold
        if 'bold' in tags:
            weight = 'bold'
        
        # Check for italic
        if 'italic' in tags:
            slant = 'italic'
        
        return {
            'family': family,
            'size': size,
            'weight': weight,
            'slant': slant,
            'tags': tags
        }
    
    def apply_font_family(self, family):
        """
        Apply font family to selected text.
        Preserves bold, italic, size, and other formatting.
        """
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            # No selection, apply to cursor position
            sel_start = sel_end = self.text.index(tk.INSERT)
            return
        
        # Get current formatting at selection start
        current = self.get_current_formatting(sel_start)
        
        # Remove old font tag
        for tag in current['tags']:
            if tag.startswith('font_'):
                self.text.tag_remove(tag, sel_start, sel_end)
        
        # Create new combined tag
        tag_name = f"font_{family.replace(' ', '_')}"
        
        # Create font with preserved properties
        font_obj = tkFont.Font(
            family=family,
            size=current['size'],
            weight=current['weight'],
            slant=current['slant']
        )
        
        self.text.tag_configure(tag_name, font=font_obj)
        self.text.tag_add(tag_name, sel_start, sel_end)
    
    def apply_font_size(self, size):
        """
        Apply font size to selected text.
        Preserves family, bold, italic, and other formatting.
        """
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            # No selection, apply to cursor position
            sel_start = sel_end = self.text.index(tk.INSERT)
            return
        
        # Get current formatting at selection start
        current = self.get_current_formatting(sel_start)
        
        # Remove old size tag
        for tag in current['tags']:
            if tag.startswith('size_'):
                self.text.tag_remove(tag, sel_start, sel_end)
        
        # Create new combined tag
        tag_name = f"size_{size}"
        
        # Create font with preserved properties
        font_obj = tkFont.Font(
            family=current['family'],
            size=size,
            weight=current['weight'],
            slant=current['slant']
        )
        
        self.text.tag_configure(tag_name, font=font_obj)
        self.text.tag_add(tag_name, sel_start, sel_end)
    
    def toggle_bold(self):
        """Toggle bold on selected text."""
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        
        current = self.get_current_formatting(sel_start)
        
        if 'bold' in current['tags']:
            # Remove bold
            self.text.tag_remove('bold', sel_start, sel_end)
            
            # Re-apply font with normal weight
            for tag in current['tags']:
                if tag.startswith('font_') or tag.startswith('size_'):
                    self.text.tag_remove(tag, sel_start, sel_end)
            
            font_obj = tkFont.Font(
                family=current['family'],
                size=current['size'],
                weight='normal',
                slant=current['slant']
            )
            
            # Add back size or font tag with normal weight
            if current['slant'] == 'italic' or current['family'] != 'Segoe UI' or current['size'] != 11:
                tag_name = f"fmt_{current['family']}_{current['size']}"
                self.text.tag_configure(tag_name, font=font_obj)
                self.text.tag_add(tag_name, sel_start, sel_end)
        else:
            # Add bold
            self.text.tag_add('bold', sel_start, sel_end)
    
    def toggle_italic(self):
        """Toggle italic on selected text."""
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        
        current = self.get_current_formatting(sel_start)
        
        if 'italic' in current['tags']:
            # Remove italic
            self.text.tag_remove('italic', sel_start, sel_end)
        else:
            # Add italic
            self.text.tag_add('italic', sel_start, sel_end)
    
    def toggle_underline(self):
        """Toggle underline on selected text."""
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        
        current = self.get_current_formatting(sel_start)
        
        if 'underline' in current['tags']:
            self.text.tag_remove('underline', sel_start, sel_end)
        else:
            self.text.tag_add('underline', sel_start, sel_end)
    
    def toggle_highlight(self):
        """Toggle highlight on selected text."""
        try:
            sel_start = self.text.index(tk.SEL_FIRST)
            sel_end = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        
        current = self.get_current_formatting(sel_start)
        
        if 'highlight' in current['tags']:
            self.text.tag_remove('highlight', sel_start, sel_end)
        else:
            self.text.tag_add('highlight', sel_start, sel_end)