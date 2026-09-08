"""Secure diary and daily planning screens for Tarizz."""
import calendar
import hashlib
import hmac
import os
import tkinter as tk
from datetime import date
from tkinter import messagebox, simpledialog, ttk

from backend.database import get_db


BG = '#111827'
PANEL = '#1f2937'
TEXT = '#f3f4f6'
MUTED = '#9ca3af'
ACCENT = '#3b82f6'


def _button(parent, text, command, primary=False):
    return tk.Button(parent, text=text, command=command, relief='flat', bd=0,
                     bg=ACCENT if primary else '#374151', fg='white',
                     activebackground='#2563eb' if primary else '#4b5563',
                     activeforeground='white', padx=14, pady=8, cursor='hand2')


class DiaryWindow:
    def __init__(self, parent):
        self.db = get_db()
        if not self._unlock(parent):
            return
        self.window = tk.Toplevel(parent)
        self.window.title('Tarizz · Private Diary')
        self.window.geometry('850x650')
        self.window.configure(bg=BG)
        self.current_date = date.today().isoformat()

        header = tk.Frame(self.window, bg=BG)
        header.pack(fill='x', padx=24, pady=(20, 12))
        tk.Label(header, text='Private diary', font=('Segoe UI', 20, 'bold'), bg=BG, fg=TEXT).pack(side='left')
        self.date_var = tk.StringVar(value=self.current_date)
        entry = tk.Entry(header, textvariable=self.date_var, width=12, bg=PANEL, fg=TEXT,
                         insertbackground=TEXT, relief='flat', font=('Segoe UI', 11))
        entry.pack(side='right', padx=(8, 0), ipady=7)
        _button(header, 'Open date', self.open_date).pack(side='right')

        tk.Label(self.window, text='Stored inside your encrypted vault and protected by your diary password.',
                 bg=BG, fg=MUTED, font=('Segoe UI', 9)).pack(anchor='w', padx=24)
        self.editor = tk.Text(self.window, wrap='word', undo=True, bg=PANEL, fg=TEXT,
                              insertbackground=TEXT, selectbackground='#374151', relief='flat',
                              padx=20, pady=18, font=('Segoe UI', 12))
        self.editor.pack(fill='both', expand=True, padx=24, pady=14)
        footer = tk.Frame(self.window, bg=BG)
        footer.pack(fill='x', padx=24, pady=(0, 20))
        self.status = tk.Label(footer, text='', bg=BG, fg=MUTED)
        self.status.pack(side='left')
        _button(footer, 'Save entry', self.save, True).pack(side='right')
        self.load()
        self.window.protocol('WM_DELETE_WINDOW', self.close)

    def _unlock(self, parent):
        stored = self.db.get_setting('diary_password')
        if not stored:
            first = simpledialog.askstring('Set diary password', 'Create a password for your private diary:',
                                           parent=parent, show='*')
            if not first:
                return False
            second = simpledialog.askstring('Confirm password', 'Enter it again:', parent=parent, show='*')
            if first != second:
                messagebox.showerror('Password mismatch', 'The passwords did not match.', parent=parent)
                return False
            salt = os.urandom(16)
            digest = hashlib.pbkdf2_hmac('sha256', first.encode(), salt, 240000)
            self.db.set_setting('diary_password', salt.hex() + ':' + digest.hex())
            return True
        password = simpledialog.askstring('Unlock diary', 'Diary password:', parent=parent, show='*')
        if password is None:
            return False
        try:
            salt_hex, digest_hex = stored.split(':', 1)
            test = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), 240000)
            valid = hmac.compare_digest(test.hex(), digest_hex)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            messagebox.showerror('Access denied', 'Incorrect diary password.', parent=parent)
        return valid

    def open_date(self):
        try:
            date.fromisoformat(self.date_var.get())
        except ValueError:
            messagebox.showerror('Invalid date', 'Use YYYY-MM-DD.', parent=self.window)
            return
        self.save()
        self.current_date = self.date_var.get()
        self.load()

    def load(self):
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', self.db.load_diary_entry(self.current_date))
        self.status.configure(text=f'Entry for {self.current_date}')

    def save(self):
        self.db.save_diary_entry(self.current_date, self.editor.get('1.0', 'end-1c'))
        self.status.configure(text=f'Saved {self.current_date}')

    def close(self):
        self.save()
        self.window.destroy()


class PlannerWindow:
    def __init__(self, parent, initial_project_id=None):
        self.db = get_db()
        self.window = tk.Toplevel(parent)
        self.window.title('Tarizz · Calendar & Daily Tasks')
        self.window.geometry('980x680')
        self.window.configure(bg=BG)
        self.selected = date.today()
        self.year, self.month = self.selected.year, self.selected.month
        self.initial_project_id = initial_project_id

        self.calendar_panel = tk.Frame(self.window, bg=PANEL, padx=18, pady=18)
        self.calendar_panel.pack(side='left', fill='y', padx=(20, 10), pady=20)
        self.task_panel = tk.Frame(self.window, bg=BG)
        self.task_panel.pack(side='left', fill='both', expand=True, padx=(10, 20), pady=20)
        self.draw_calendar()
        self.build_tasks()

    def draw_calendar(self):
        for widget in self.calendar_panel.winfo_children():
            widget.destroy()
        nav = tk.Frame(self.calendar_panel, bg=PANEL)
        nav.grid(row=0, column=0, columnspan=7, sticky='ew', pady=(0, 14))
        _button(nav, '‹', lambda: self.change_month(-1)).pack(side='left')
        tk.Label(nav, text=f'{calendar.month_name[self.month]} {self.year}', bg=PANEL, fg=TEXT,
                 font=('Segoe UI', 14, 'bold'), width=18).pack(side='left')
        _button(nav, '›', lambda: self.change_month(1)).pack(side='left')
        for col, name in enumerate(('Mon','Tue','Wed','Thu','Fri','Sat','Sun')):
            tk.Label(self.calendar_panel, text=name, bg=PANEL, fg=MUTED, width=5).grid(row=1, column=col, pady=4)
        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), start=2):
            for col, day in enumerate(week):
                if not day:
                    continue
                target = date(self.year, self.month, day)
                selected = target == self.selected
                tk.Button(self.calendar_panel, text=str(day), relief='flat', width=4, height=2,
                          bg=ACCENT if selected else '#374151', fg='white',
                          command=lambda d=target: self.select_date(d)).grid(row=row, column=col, padx=2, pady=2)

    def change_month(self, delta):
        value = self.year * 12 + self.month - 1 + delta
        self.year, month0 = divmod(value, 12)
        self.month = month0 + 1
        self.draw_calendar()

    def select_date(self, selected):
        self.selected = selected
        self.draw_calendar()
        self.refresh_tasks()

    def build_tasks(self):
        self.heading = tk.Label(self.task_panel, bg=BG, fg=TEXT, font=('Segoe UI', 20, 'bold'))
        self.heading.pack(anchor='w')
        tk.Label(self.task_panel, text='Plan work by day and optionally connect it to a project.',
                 bg=BG, fg=MUTED).pack(anchor='w', pady=(2, 16))
        add = tk.Frame(self.task_panel, bg=BG)
        add.pack(fill='x')
        self.task_text = tk.Entry(add, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief='flat', font=('Segoe UI', 11))
        self.task_text.pack(side='left', fill='x', expand=True, ipady=9)
        projects = self.db.get_all_projects()
        self.project_lookup = {'No project': None, **{p['title']: p['id'] for p in projects}}
        preferred = next((p['title'] for p in projects if p['id'] == self.initial_project_id), 'No project')
        self.project_var = tk.StringVar(value=preferred)
        ttk.Combobox(add, textvariable=self.project_var, state='readonly', width=18,
                     values=list(self.project_lookup)).pack(side='left', padx=8)
        _button(add, 'Add task', self.add_task, True).pack(side='left')
        self.task_text.bind('<Return>', lambda _e: self.add_task())
        self.list_frame = tk.Frame(self.task_panel, bg=BG)
        self.list_frame.pack(fill='both', expand=True, pady=(16, 0))
        self.refresh_tasks()

    def refresh_tasks(self):
        self.heading.configure(text=self.selected.strftime('%A, %d %B %Y'))
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        tasks = self.db.get_tasks(self.selected.isoformat())
        if not tasks:
            tk.Label(self.list_frame, text='No tasks yet. Add one above.', bg=BG, fg=MUTED,
                     font=('Segoe UI', 11)).pack(anchor='w', pady=20)
        for task in tasks:
            row = tk.Frame(self.list_frame, bg=PANEL, padx=12, pady=10)
            row.pack(fill='x', pady=4)
            done = tk.BooleanVar(value=bool(task['completed']))
            tk.Checkbutton(row, variable=done, bg=PANEL, activebackground=PANEL,
                           command=lambda i=task['id'], v=done: self.toggle(i, v)).pack(side='left')
            label = task['title'] + (f"  ·  {task['project_title']}" if task.get('project_title') else '')
            tk.Label(row, text=label, bg=PANEL, fg=MUTED if done.get() else TEXT,
                     font=('Segoe UI', 11, 'overstrike' if done.get() else 'normal')).pack(side='left', padx=6)
            _button(row, 'Delete', lambda i=task['id']: self.delete(i)).pack(side='right')

    def add_task(self):
        title = self.task_text.get().strip()
        if not title:
            return
        self.db.add_task(self.selected.isoformat(), title, self.project_lookup[self.project_var.get()])
        self.task_text.delete(0, 'end')
        self.refresh_tasks()

    def toggle(self, task_id, variable):
        self.db.set_task_completed(task_id, variable.get())
        self.refresh_tasks()

    def delete(self, task_id):
        self.db.delete_task(task_id)
        self.refresh_tasks()


def open_diary(parent):
    return DiaryWindow(parent)


def open_planner(parent, project_id=None):
    return PlannerWindow(parent, project_id)
