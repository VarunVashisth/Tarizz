
import os
import sys
import tkinter as tk
from tkinter import PhotoImage, messagebox, ttk

from backend.auth_manager_simple import SimpleAuthManager


SECURITY_QUESTIONS = [
    "What is your favorite food?",
    "What was your first pet's name?",
    "What is your birth city?",
    "What was the name of your first school?",
]


def run_auth_gate(auth_manager, create_mode=False) -> bool:
    gate = _AuthWindow(auth_manager, create_mode=create_mode)
    gate.root.mainloop()
    return gate.authenticated


class _AuthWindow:
    def __init__(self, auth_manager, create_mode=False):
        self.auth_manager = auth_manager
        self.authenticated = False
        self.c = {
            'bg':'#0e0e11','card':'#151519','field':'#1d1d23','border':'#2a2932',
            'text':'#f4f3f8','muted':'#9f9eaa','accent':'#9587ff','accent_hover':'#8171ef',
            'danger':'#ff7a7a','success':'#57c99c','warning':'#ffb86b'
        }

        self.root = tk.Tk()
        self.root.title("Tarizz — Private Workspace")
        self.root.geometry("480x680")
        self.root.configure(bg=self.c['bg'])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        if getattr(sys, "frozen", False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        logo_path = os.path.join(base_dir, "data", "tarizzlogo.png")
        if os.path.exists(logo_path):
            self.logo = PhotoImage(file=logo_path)
            self.root.iconphoto(False, self.logo)

        self.create_mode = create_mode or auth_manager.is_first_run()
        self.reset_mode = False

        self.root.update_idletasks()
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sx - 480) // 2}+{(sy - 680) // 2}")

        style=ttk.Style(self.root);style.theme_use('clam');style.configure('Auth.TCombobox',fieldbackground=self.c['field'],background=self.c['field'],foreground=self.c['text'],arrowcolor=self.c['muted'],bordercolor=self.c['border'],padding=7);style.map('Auth.TCombobox',fieldbackground=[('readonly',self.c['field'])],foreground=[('readonly',self.c['text'])])

        self._build_ui()

    def _clear_body(self):
        for child in self.root.winfo_children():
            child.destroy()

    def _build_ui(self):
        self._clear_body()

        tk.Label(self.root,text="PRIVATE  ·  LOCAL  ·  ENCRYPTED",font=("Segoe UI",8,"bold"),fg=self.c['accent'],bg=self.c['bg']).pack(pady=(30,5))
        tk.Label(
            self.root, text="TARIZZ",
            font=("Segoe UI", 25, "bold"), fg=self.c['text'], bg=self.c['bg']
        ).pack(pady=(0, 3))

        tk.Label(
            self.root, text="Your private workspace, ready when you are.",
            font=("Segoe UI", 10), fg=self.c['muted'], bg=self.c['bg']
        ).pack(pady=(0, 20))

        card = tk.Frame(self.root, bg=self.c['card'], padx=30, pady=24,highlightbackground=self.c['border'],highlightthickness=1)
        card.pack(padx=42, pady=0, fill="x")

        if self.reset_mode:
            self._build_reset(card)
        elif self.create_mode:
            self._build_create(card)
        else:
            self._build_login(card)
        tk.Label(self.root,text="YOUR VAULT NEVER LEAVES THIS DEVICE",font=("Segoe UI",8,"bold"),fg='#666570',bg=self.c['bg']).pack(side='bottom',pady=20)

    def _label(self, parent, text):
        tk.Label(
            parent, text=text, font=("Segoe UI", 10),
            fg=self.c['muted'], bg=self.c['card'], anchor="w"
        ).pack(fill="x", pady=(8, 0))

    def _text_entry(self, parent, show=None):
        kwargs = dict(
            font=("Segoe UI", 12),
            bg=self.c['field'], fg=self.c['text'],
            insertbackground=self.c['text'],
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=self.c['border'],
            highlightcolor=self.c['accent'],
        )
        if show is not None:
            kwargs["show"] = show
        e = tk.Entry(parent, **kwargs)
        e.pack(fill="x", ipady=7, pady=(2, 0))
        self._bind_word_navigation(e)
        return e

    @staticmethod
    def _bind_word_navigation(entry):
        """Consistent Ctrl+Arrow word navigation across Tk platforms."""
        def move(direction, select=False):
            value = entry.get()
            pos = entry.index(tk.INSERT)
            if direction < 0:
                while pos > 0 and value[pos - 1].isspace():
                    pos -= 1
                while pos > 0 and not value[pos - 1].isspace():
                    pos -= 1
            else:
                while pos < len(value) and not value[pos].isspace():
                    pos += 1
                while pos < len(value) and value[pos].isspace():
                    pos += 1
            if select:
                try:
                    anchor = entry.index(tk.ANCHOR)
                except tk.TclError:
                    anchor = entry.index(tk.INSERT)
                    entry.selection_from(anchor)
                entry.selection_range(min(anchor, pos), max(anchor, pos))
            else:
                entry.selection_clear()
            entry.icursor(pos)
            entry.xview_moveto(pos / max(1, len(value)))
            return 'break'
        entry.bind('<Control-Left>', lambda _e: move(-1))
        entry.bind('<Control-Right>', lambda _e: move(1))
        entry.bind('<Control-Shift-Left>', lambda _e: move(-1, True))
        entry.bind('<Control-Shift-Right>', lambda _e: move(1, True))

    def _make_button(self, parent, text, command, secondary=False):
        bg = self.c['field'] if secondary else self.c['accent']
        active = '#2a2932' if secondary else self.c['accent_hover']
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 11, "bold"),
            bg=bg, fg=self.c['text'],
            activebackground=active, activeforeground=self.c['text'],
            relief="flat", bd=0, cursor="hand2",
        )
        btn.pack(fill="x", ipady=9, pady=(8, 0))
        return btn

    def _build_create(self, card):
        tk.Label(
            card, text="Create Account",
            font=("Segoe UI", 16, "bold"), fg=self.c['text'], bg=self.c['card']
        ).pack(pady=(0, 8))

        self._label(card, "Username")
        self.username_entry = self._text_entry(card)

        self._label(card, "Password")
        self.pwd_entry = self._text_entry(card, show="•")

        self._label(card, "Confirm Password")
        self.confirm_entry = self._text_entry(card, show="•")

        self.strength_label = tk.Label(
            card, text="At least 8 characters, 1 uppercase, 1 digit",
            font=("Segoe UI", 9), fg=self.c['muted'], bg=self.c['card'], anchor="w", wraplength=340
        )
        self.strength_label.pack(fill="x", pady=(4, 0))
        self.pwd_entry.bind("<KeyRelease>", self._on_pwd_keystroke)

        self._label(card, "Security Question")
        self.question_var = tk.StringVar(value=SECURITY_QUESTIONS[0])
        combo = ttk.Combobox(
            card, textvariable=self.question_var,
            values=SECURITY_QUESTIONS, state="readonly",style='Auth.TCombobox'
        )
        combo.pack(fill="x", pady=(2, 0), ipady=4)

        self._label(card, "Security Answer")
        self.answer_entry = self._text_entry(card)

        self.error_label = tk.Label(
            card, text="", font=("Segoe UI", 9),
            fg=self.c['danger'], bg=self.c['card'], wraplength=340, justify="left"
        )
        self.error_label.pack(fill="x", pady=(8, 0))

        self._make_button(card, "Create Account", self._on_create)
        self.pwd_entry.bind("<Return>", lambda e: self._on_create())
        self.confirm_entry.bind("<Return>", lambda e: self._on_create())

    def _build_login(self, card):
        tk.Label(
            card, text="Welcome Back",
            font=("Segoe UI", 16, "bold"), fg=self.c['text'], bg=self.c['card']
        ).pack(pady=(0, 8))

        stored = self.auth_manager.stored_username() or ""

        self._label(card, "Username")
        self.username_entry = self._text_entry(card)
        if stored:
            self.username_entry.insert(0, stored)

        self._label(card, "Password")
        self.pwd_entry = self._text_entry(card, show="•")

        self.status_label = tk.Label(
            card, text="", font=("Segoe UI", 9),
            fg=self.c['danger'], bg=self.c['card'], anchor="w", wraplength=340
        )
        self.status_label.pack(fill="x", pady=(6, 4))

        self._make_button(card, "Sign In", self._on_login)
        self._make_button(card, "Forgot password?", self._show_reset, secondary=True)
        self.pwd_entry.bind("<Return>", lambda e: self._on_login())
        self.username_entry.bind("<Return>", lambda e: self.pwd_entry.focus_set())

    def _build_reset(self, card):
        tk.Label(
            card, text="Reset Password",
            font=("Segoe UI", 16, "bold"), fg=self.c['text'], bg=self.c['card']
        ).pack(pady=(0, 8))

        stored = self.auth_manager.stored_username() or ""

        self._label(card, "Username")
        self.username_entry = self._text_entry(card)
        if stored:
            self.username_entry.insert(0, stored)

        question = self.auth_manager.get_security_question(stored) if stored else None
        q_text = question or "Enter your username to load the security question."
        self.question_display = tk.Label(
            card, text=q_text, font=("Segoe UI", 10),
            fg=self.c['text'], bg=self.c['card'], wraplength=340, justify="left"
        )
        self.question_display.pack(fill="x", pady=(10, 0))

        def refresh_question(event=None):
            q = self.auth_manager.get_security_question(self.username_entry.get())
            self.question_display.config(
                text=q if q else "No account found for that username."
            )

        self.username_entry.bind("<FocusOut>", refresh_question)
        self.username_entry.bind("<Return>", refresh_question)

        self._label(card, "Security Answer")
        self.answer_entry = self._text_entry(card)

        self._label(card, "New Password")
        self.pwd_entry = self._text_entry(card, show="•")

        self._label(card, "Confirm New Password")
        self.confirm_entry = self._text_entry(card, show="•")

        self.status_label = tk.Label(
            card, text="", font=("Segoe UI", 9),
            fg=self.c['danger'], bg=self.c['card'], wraplength=340, justify="left"
        )
        self.status_label.pack(fill="x", pady=(8, 0))

        self._make_button(card, "Reset Password", self._on_reset)
        self._make_button(card, "Back to Sign In", self._show_login, secondary=True)

    def _show_reset(self):
        self.reset_mode = True
        self.create_mode = False
        self._build_ui()

    def _show_login(self):
        self.reset_mode = False
        self.create_mode = False
        self._build_ui()

    def _on_pwd_keystroke(self, event=None):
        pwd = self.pwd_entry.get()
        ok, reason = SimpleAuthManager.validate_password_strength(pwd)
        if not pwd:
            self.strength_label.config(text="At least 8 characters, 1 uppercase, 1 digit", fg=self.c['muted'])
        elif ok:
            self.strength_label.config(text="✓ Password looks good", fg=self.c['success'])
        else:
            self.strength_label.config(text=reason, fg=self.c['warning'])

    @staticmethod
    def validate_username(username: str) -> tuple:
        if not username or len(username.strip()) == 0:
            return False, "Username cannot be empty."
        username = username.strip()
        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if len(username) > 20:
            return False, "Username cannot exceed 20 characters."
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        if not all(c in allowed for c in username):
            return False, "Username can only contain letters, numbers, and underscores."
        return True, ""

    @staticmethod
    def validate_security_answer(answer: str) -> tuple:
        if not answer or len(answer.strip()) == 0:
            return False, "Answer cannot be empty."
        answer = answer.strip()
        if len(answer) < 2:
            return False, "Answer must be at least 2 characters."
        if len(answer) > 100:
            return False, "Answer cannot exceed 100 characters."
        return True, ""

    def _on_create(self):
        username = self.username_entry.get()
        password = self.pwd_entry.get()
        confirm = self.confirm_entry.get()
        question = self.question_var.get()
        answer = self.answer_entry.get()

        ok, msg = self.validate_username(username)
        if not ok:
            self.error_label.config(text=msg)
            return

        ok, msg = SimpleAuthManager.validate_password_strength(password)
        if not ok:
            self.error_label.config(text=msg)
            messagebox.showerror("Weak Password", msg, parent=self.root)
            return

        if password != confirm:
            self.error_label.config(text="Passwords do not match.")
            messagebox.showerror("Mismatch", "Passwords do not match.", parent=self.root)
            return

        ok, msg = self.validate_security_answer(answer)
        if not ok:
            self.error_label.config(text=msg)
            return

        if not question.strip():
            self.error_label.config(text="Please choose a security question.")
            return

        try:
            created = self.auth_manager.create_account(username, password, question, answer)
        except Exception as e:
            self.error_label.config(text=f"Could not create account: {e}")
            messagebox.showerror("Error", str(e), parent=self.root)
            return

        if not created:
            self.error_label.config(text="An account already exists. Please sign in.")
            return

        self.authenticated = True
        self.root.destroy()

    def _on_login(self):
        if self.auth_manager.is_locked():
            secs = int(self.auth_manager.lockout_remaining_seconds())
            self.status_label.config(text=f"Locked. Try again in {secs}s.")
            self._tick_lockout()
            return

        username = self.username_entry.get().strip()
        password = self.pwd_entry.get()

        if not username:
            self.status_label.config(text="Enter your username.")
            return
        if not password:
            self.status_label.config(text="Enter your password.")
            return

        try:
            ok = self.auth_manager.login(username, password)
        except Exception as e:
            self.status_label.config(text=f"Login failed: {e}")
            return

        if ok:
            self.authenticated = True
            self.root.destroy()
            return

        self.pwd_entry.delete(0, tk.END)
        if self.auth_manager.is_locked():
            self.status_label.config(text="Too many attempts. Locked for 60s.")
            self._tick_lockout()
        else:
            self.status_label.config(text="Invalid username or password.")

    def _on_reset(self):
        username = self.username_entry.get().strip()
        answer = self.answer_entry.get()
        password = self.pwd_entry.get()
        confirm = self.confirm_entry.get()

        ok, msg = self.validate_username(username)
        if not ok:
            self.status_label.config(text=msg)
            return
        ok, msg = self.validate_security_answer(answer)
        if not ok:
            self.status_label.config(text=msg)
            return
        ok, msg = SimpleAuthManager.validate_password_strength(password)
        if not ok:
            self.status_label.config(text=msg)
            return
        if password != confirm:
            self.status_label.config(text="Passwords do not match.")
            return

        try:
            reset_ok = self.auth_manager.reset_password(username, answer, password)
        except Exception as e:
            self.status_label.config(text=str(e))
            return

        if not reset_ok:
            self.status_label.config(text="Could not reset password. Check username and answer.")
            return

        self.authenticated = True
        self.root.destroy()

    def _tick_lockout(self):
        if self.auth_manager.is_locked():
            secs = int(self.auth_manager.lockout_remaining_seconds())
            self.status_label.config(text=f"Locked. Try again in {secs}s.")
            self.root.after(1000, self._tick_lockout)
        else:
            self.status_label.config(text="")

    def _on_close(self):
        self.authenticated = False
        self.root.destroy()
