"""Shared visual language for the Tarizz desktop UI."""
COLORS = {
    'app': '#181818', 'sidebar': '#202020', 'panel': '#242424', 'raised': '#2b2b2b',
    'hover': '#333333', 'border': '#3a3a3a', 'text': '#dcddde', 'muted': '#8e8e93',
    'subtle': '#6b6b70', 'accent': '#7c6fdd', 'accent_hover': '#9187e6', 'danger': '#d65d5d',
}


def configure_ttk(root):
    from tkinter import ttk
    c = COLORS
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', background=c['app'], foreground=c['text'], borderwidth=0)
    style.configure('TFrame', background=c['app'])
    style.configure('TLabel', background=c['app'], foreground=c['text'], font=('Segoe UI', 10))
    style.configure('TCombobox', fieldbackground=c['raised'], background=c['raised'],
                    foreground=c['text'], arrowcolor=c['muted'], bordercolor=c['border'])
    style.map('TCombobox', fieldbackground=[('readonly', c['raised'])],
              foreground=[('readonly', c['text'])])
    return style
