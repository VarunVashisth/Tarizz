"""
auth_ui.py  —  Tarizz Authentication Window
============================================
Responsibility : Provide the Tkinter UI for password creation (first run)
                 and login (subsequent runs).  This window is shown BEFORE
                 the main ProjectDashboard and blocks until the user
                 successfully authenticates or closes the app.

Why a separate file?
--------------------
  • The auth window has a completely different layout from the dashboard.
  • It must be destroyed before the dashboard is created (Tkinter root
    rules).
  • Keeping it isolated means we can swap it for a different UI toolkit
    later without touching dashboard code.

Design decisions
----------------
  • Uses a single Tk() root that is destroyed on success — the bootstrap
    layer then creates the real Tk() root for the dashboard.
  • Password fields use show='•' to hide input.
  • Strength feedback updates live as the user types.
  • Lockout countdown updates every 1 second via .after().
  • No network, no file I/O except what SessionManager does internally.
"""

import tkinter as tk
from tkinter import messagebox

from .session_manager import SessionManager


def run_auth_gate(session: SessionManager) -> bool:
    """
    Block until the user authenticates or closes the window.

    Inputs
      session – the SessionManager instance (already constructed,
                NOT yet logged in).
    Output
      True  – user authenticated; session is active.
      False – user closed the window without authenticating.
    Side-effects
      • Creates and destroys a Tk() root window.
      • Calls session.create_password() or session.login().
    """
    gate = _AuthWindow(session)
    gate.root.mainloop()
    return gate.authenticated


class _AuthWindow:
    """
    Internal class.  Not imported anywhere outside this module.

    Attributes
      root          – the Tk() root window.
      authenticated – set to True only on successful login/create.
    """

    def __init__(self, session: SessionManager):
        self.session       = session
        self.authenticated = False

        # --- root window ---
        self.root = tk.Tk()
        self.root.title("Tarizz — Unlock Your Vault")
        self.root.geometry("420x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Centre on screen
        self.root.update_idletasks()
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sx-420)//2}+{(sy-380)//2}")

        # --- layout ---
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="🔐 Tarizz",
            font=("Segoe UI", 24, "bold"), fg="white", bg="#1a1a1a"
        ).pack(pady=(40, 4))

        tk.Label(
            self.root, text="Your private, encrypted workspace",
            font=("Segoe UI", 10), fg="#888888", bg="#1a1a1a"
        ).pack(pady=(0, 30))

        # Card frame (slightly lighter background for contrast)
        card = tk.Frame(self.root, bg="#2a2a2a", padx=30, pady=25)
        card.pack(padx=40, pady=0, fill="x")

        # --- first run: create password ---
        if self.session.is_first_run():
            tk.Label(
                card, text="Create Master Password",
                font=("Segoe UI", 13, "bold"), fg="white", bg="#2a2a2a"
            ).pack(pady=(0, 12))

            tk.Label(card, text="Password", font=("Segoe UI", 10),
                     fg="#aaaaaa", bg="#2a2a2a", anchor="w").pack(fill="x")
            self.pwd_entry = self._make_entry(card)

            tk.Label(card, text="Confirm Password", font=("Segoe UI", 10),
                     fg="#aaaaaa", bg="#2a2a2a", anchor="w").pack(fill="x", pady=(8, 0))
            self.confirm_entry = self._make_entry(card)

            # Live strength feedback label
            self.strength_label = tk.Label(
                card, text="", font=("Segoe UI", 9),
                fg="#888888", bg="#2a2a2a", anchor="w"
            )
            self.strength_label.pack(fill="x", pady=(4, 12))
            self.pwd_entry.bind("<KeyRelease>", self._on_pwd_keystroke)

            self._make_button(card, "Create Vault", self._on_create)

        # --- subsequent runs: login ---
        else:
            tk.Label(
                card, text="Welcome Back",
                font=("Segoe UI", 13, "bold"), fg="white", bg="#2a2a2a"
            ).pack(pady=(0, 12))

            tk.Label(card, text="Master Password", font=("Segoe UI", 10),
                     fg="#aaaaaa", bg="#2a2a2a", anchor="w").pack(fill="x")
            self.pwd_entry = self._make_entry(card)

            # Status label (wrong password / lockout messages)
            self.status_label = tk.Label(
                card, text="", font=("Segoe UI", 9),
                fg="#ff6b6b", bg="#2a2a2a", anchor="w"
            )
            self.status_label.pack(fill="x", pady=(4, 12))

            self._make_button(card, "Unlock", self._on_login)

            # Bind Enter key
            self.pwd_entry.bind("<Return>", lambda e: self._on_login())

    # ------------------------------------------------------------------
    # Helpers for building styled widgets
    # ------------------------------------------------------------------
    def _make_entry(self, parent) -> tk.Entry:
        e = tk.Entry(
            parent,
            show="•",
            font=("Segoe UI", 12),
            bg="#333333", fg="white",
            insertbackground="white",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#444444",
            highlightcolor="#0078d4",
        )
        e.pack(fill="x", ipady=8, pady=(2, 0))
        return e

    def _make_button(self, parent, text: str, command) -> tk.Button:
        btn = tk.Button(
            parent, text=text, command=command,
            font=("Segoe UI", 11, "bold"),
            bg="#0078d4", fg="white",
            activebackground="#006cbd", activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
        )
        btn.pack(fill="x", ipady=10, pady=(4, 0))
        return btn

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _on_pwd_keystroke(self, event=None):
        """Live strength feedback while typing (create-password mode)."""
        pwd = self.pwd_entry.get()
        ok, reason = self.session.auth.validate_password_strength(pwd)
        if not pwd:
            self.strength_label.config(text="", fg="#888888")
        elif ok:
            self.strength_label.config(text="✓ Password looks good", fg="#4caf50")
        else:
            self.strength_label.config(text=reason, fg="#ff9800")

    def _on_create(self):
        """Handle the 'Create Vault' button."""
        pwd     = self.pwd_entry.get()
        confirm = self.confirm_entry.get()

        # Validation
        ok, reason = self.session.auth.validate_password_strength(pwd)
        if not ok:
            messagebox.showerror("Weak Password", reason, parent=self.root)
            return
        if pwd != confirm:
            messagebox.showerror("Mismatch",
                                 "Passwords do not match.", parent=self.root)
            return

        # Create
        self.session.create_password(pwd)
        self.authenticated = True
        self.root.destroy()

    def _on_login(self):
        """Handle the 'Unlock' button."""
        if self.session.is_locked():
            secs = int(self.session.lockout_remaining())
            self.status_label.config(
                text=f"Locked. Try again in {secs}s."
            )
            self._tick_lockout()
            return

        pwd = self.pwd_entry.get()
        if self.session.login(pwd):
            self.authenticated = True
            self.root.destroy()
        else:
            self.pwd_entry.delete(0, tk.END)
            if self.session.is_locked():
                self.status_label.config(text="Too many attempts. Locked for 60s.")
                self._tick_lockout()
            else:
                self.status_label.config(text="Invalid password.")

    def _tick_lockout(self):
        """Update the lockout countdown every second."""
        if self.session.is_locked():
            secs = int(self.session.lockout_remaining())
            self.status_label.config(text=f"Locked. Try again in {secs}s.")
            self.root.after(1000, self._tick_lockout)
        else:
            self.status_label.config(text="")

    def _on_close(self):
        """User closed the window without authenticating."""
        self.authenticated = False
        self.root.destroy()
