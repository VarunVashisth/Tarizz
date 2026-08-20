# text_formatter.py
"""
Text formatting with combined font tags so bold/italic/size/family compose,
and highlight that does not bleed onto newly typed text.
"""

import tkinter as tk
from tkinter import font as tkFont


PRESERVE_TAGS = {
    'sel', 'sel.last',
    'bold', 'italic', 'underline', 'highlight',
    'code_block',
}


class TextFormatter:
    """Manages text formatting tags without leaking styles onto new typing."""

    def __init__(self, text_widget):
        self.text = text_widget
        self.default_family = 'Segoe UI'
        self.default_size = 11
        self._strip_highlight = False
        self.setup_base_tags()
        self._bind_highlight_guard()

    def setup_base_tags(self):
        # Marker tags: no font, so they never override size/family.
        self.text.tag_configure('bold')
        self.text.tag_configure('italic')
        self.text.tag_configure('underline', underline=True)
        self.text.tag_configure(
            'highlight',
            background='#ffff99',
            foreground='#000000',
            relief='flat',
            borderwidth=0,
            overstrike=False,
        )
        self.text.tag_lower('highlight')

    def _bind_highlight_guard(self):
        """Stop Tkinter from inheriting highlight when typing at the end of a range."""
        self.text.bind('<KeyPress>', self._on_keypress, add='+')

    def _on_keypress(self, event):
        if event.state & 0x4:  # Control
            return
        if event.keysym in (
            'BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down',
            'Home', 'End', 'Return', 'Tab', 'Shift_L', 'Shift_R',
            'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Escape',
        ):
            return
        if not event.char:
            return

        insert = self.text.index(tk.INSERT)
        self._strip_highlight = False
        ranges = self.text.tag_ranges('highlight')
        for i in range(0, len(ranges), 2):
            end = str(ranges[i + 1])
            if self.text.compare(insert, '==', end):
                self._strip_highlight = True
                break

        if self._strip_highlight:
            self.text.after_idle(self._strip_new_highlight)

    def _strip_new_highlight(self):
        if not self._strip_highlight:
            return
        self._strip_highlight = False
        try:
            insert = self.text.index(tk.INSERT)
            start = self.text.index(f'{insert}-1c')
            self.text.tag_remove('highlight', start, insert)
        except tk.TclError:
            pass

    def get_current_formatting(self, index):
        tags = self.text.tag_names(index)

        family = self.default_family
        size = self.default_size
        weight = 'normal'
        slant = 'roman'

        for tag in tags:
            parsed = self._parse_fmt_tag(tag)
            if parsed:
                family, size, weight, slant = parsed
                break

        for tag in tags:
            if tag.startswith('font_') and not tag.startswith('fmt_'):
                family = tag[5:].replace('_', ' ')
                break

        for tag in tags:
            if tag.startswith('size_'):
                try:
                    size = int(tag[5:])
                except ValueError:
                    pass
                break

        if 'bold' in tags:
            weight = 'bold'
        if 'italic' in tags:
            slant = 'italic'

        return {
            'family': family,
            'size': size,
            'weight': weight,
            'slant': slant,
            'tags': tags,
            'is_highlighted': 'highlight' in tags,
        }

    @staticmethod
    def _parse_fmt_tag(tag):
        if not tag.startswith('fmt_'):
            return None
        parts = tag.split('_')
        if len(parts) < 5:
            return None
        slant = parts[-1]
        weight = parts[-2]
        try:
            size = int(parts[-3])
        except ValueError:
            return None
        family = ' '.join(parts[1:-3]).replace('_', ' ')
        if slant not in ('roman', 'italic') or weight not in ('normal', 'bold'):
            return None
        return family, size, weight, slant

    def _fmt_tag_name(self, family, size, weight, slant):
        fam = family.replace(' ', '_')
        return f"fmt_{fam}_{size}_{weight}_{slant}"

    def _apply_combined_font(self, sel_start, sel_end, family, size, weight, slant):
        current_tags = self.text.tag_names(sel_start)
        for tag in current_tags:
            if tag.startswith('fmt_') or tag.startswith('font_') or tag.startswith('size_'):
                self.text.tag_remove(tag, sel_start, sel_end)

        tag_name = self._fmt_tag_name(family, size, weight, slant)
        font_obj = tkFont.Font(family=family, size=size, weight=weight, slant=slant)
        self.text.tag_configure(tag_name, font=font_obj)
        self.text.tag_add(tag_name, sel_start, sel_end)

        font_tag = f"font_{family.replace(' ', '_')}"
        size_tag = f"size_{size}"
        self.text.tag_configure(font_tag, font=font_obj)
        self.text.tag_configure(size_tag, font=font_obj)
        self.text.tag_add(font_tag, sel_start, sel_end)
        self.text.tag_add(size_tag, sel_start, sel_end)

        if weight == 'bold':
            self.text.tag_add('bold', sel_start, sel_end)
        else:
            self.text.tag_remove('bold', sel_start, sel_end)

        if slant == 'italic':
            self.text.tag_add('italic', sel_start, sel_end)
        else:
            self.text.tag_remove('italic', sel_start, sel_end)

    def _selection(self):
        try:
            return self.text.index(tk.SEL_FIRST), self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return None

    def _clear_selection(self, sel_end=None):
        try:
            self.text.tag_remove('sel', '1.0', tk.END)
        except tk.TclError:
            pass
        if sel_end is not None:
            try:
                self.text.mark_set(tk.INSERT, sel_end)
            except tk.TclError:
                pass

    def apply_font_family(self, family):
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        current = self.get_current_formatting(sel_start)
        self._apply_combined_font(
            sel_start, sel_end, family, current['size'], current['weight'], current['slant']
        )
        self._clear_selection(sel_end)

    def apply_font_size(self, size):
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        current = self.get_current_formatting(sel_start)
        self._apply_combined_font(
            sel_start, sel_end, current['family'], int(size), current['weight'], current['slant']
        )
        self._clear_selection(sel_end)

    def toggle_bold(self):
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        current = self.get_current_formatting(sel_start)
        new_weight = 'normal' if current['weight'] == 'bold' else 'bold'
        self._apply_combined_font(
            sel_start, sel_end, current['family'], current['size'], new_weight, current['slant']
        )
        self._clear_selection(sel_end)

    def toggle_italic(self):
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        current = self.get_current_formatting(sel_start)
        new_slant = 'roman' if current['slant'] == 'italic' else 'italic'
        self._apply_combined_font(
            sel_start, sel_end, current['family'], current['size'], current['weight'], new_slant
        )
        self._clear_selection(sel_end)

    def toggle_underline(self):
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        if 'underline' in self.text.tag_names(sel_start):
            self.text.tag_remove('underline', sel_start, sel_end)
        else:
            self.text.tag_add('underline', sel_start, sel_end)
        self._clear_selection(sel_end)

    def toggle_highlight(self):
        """Toggle highlight on the selection only; new typing at the end stays unhighlighted."""
        sel = self._selection()
        if not sel:
            return
        sel_start, sel_end = sel
        if 'highlight' in self.text.tag_names(sel_start):
            self.text.tag_remove('highlight', sel_start, sel_end)
        else:
            self.text.tag_add('highlight', sel_start, sel_end)
            self.text.tag_lower('highlight')
        self._clear_selection(sel_end)

    def configure_saved_tag(self, tag_name):
        """Reconfigure a tag name loaded from storage."""
        parsed = self._parse_fmt_tag(tag_name)
        if parsed:
            family, size, weight, slant = parsed
            self.text.tag_configure(
                tag_name,
                font=tkFont.Font(family=family, size=size, weight=weight, slant=slant),
            )
            return
        if tag_name.startswith('font_'):
            family = tag_name[5:].replace('_', ' ')
            self.text.tag_configure(
                tag_name,
                font=tkFont.Font(family=family, size=self.default_size),
            )
        elif tag_name.startswith('size_'):
            try:
                size = int(tag_name[5:])
            except ValueError:
                return
            self.text.tag_configure(
                tag_name,
                font=tkFont.Font(family=self.default_family, size=size),
            )
        elif tag_name == 'highlight':
            self.setup_base_tags()
        elif tag_name == 'underline':
            self.text.tag_configure('underline', underline=True)

    def apply_tags_map(self, tags_data):
        """Restore {tag: [[start, end], ...]} from storage."""
        if not tags_data:
            return
        for tag_name, ranges_list in tags_data.items():
            if tag_name in ('sel', 'sel.last'):
                continue
            self.configure_saved_tag(tag_name)
            for start_end in ranges_list:
                try:
                    start, end = start_end
                    self.text.tag_add(tag_name, start, end)
                except (tk.TclError, ValueError, TypeError):
                    pass
        try:
            self.text.tag_lower('highlight')
            self.text.tag_raise('code_block')
        except tk.TclError:
            pass

    def collect_tags_map(self):
        """Serialize user formatting for persistence."""
        tags = {}
        skip = {'sel', 'sel.last'}
        for tag_name in self.text.tag_names():
            if tag_name in skip:
                continue
            ranges = self.text.tag_ranges(tag_name)
            if not ranges:
                continue
            tags[tag_name] = [
                [str(ranges[i]), str(ranges[i + 1])]
                for i in range(0, len(ranges), 2)
            ]
        return tags
