

import os
import sys
import tkinter as tk
from tkinter import PhotoImage, messagebox


def run_auth_gate(auth_manager , create_mode = False) -> bool:

    gate = _AuthWindow(auth_manager , create_mode=create_mode)
    gate.root.mainloop()
    return gate.authenticated


class _AuthWindow:


    def __init__(self, auth_manager , create_mode=False):
        self.auth_manager  = auth_manager
        self.authenticated = False

        # --- root window ---
        self.root = tk.Tk()
        self.root.title("Tarizz – Unlock Your Vault")
        self.root.geometry("420x550")
  
        self.root.configure(bg="#1a1a1a")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            
        logo_path = os.path.join(base_dir, "data", "tarizzlogo.png")
        if os.path.exists(logo_path):
            self.logo = PhotoImage(file=logo_path)
            self.root.iconphoto(False, self.logo)


        self.create_mode = create_mode

        # Centre on screen

        self.root.update_idletasks()
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sx-420)//2}+{(sy-380)//2}")

        # --- layout ---
        self._build_ui()

    def _build_ui(self):
        # Title
        tk.Label(
            self.root, text="🔒 Tarizz",
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
        if self.create_mode or self.auth_manager.is_first_run():
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
            tk.Label(card, text="Example : Abc123", bg="#2a2a2a", fg="#888888").pack(fill="x" , pady=4)

            # Live strength feedback label
            self.strength_label = tk.Label(
                card, text="", font=("Segoe UI", 9),
                fg="#888888", bg="#2a2a2a", anchor="w"
            )
            self.strength_label.pack(fill="x", pady=(4, 12))
            self.pwd_entry.bind("<KeyRelease>", self._on_pwd_keystroke)

            self._make_button(card, "Create Vault", self._on_create)


        else:
            tk.Label(
                card, text="Welcome Back",
                font=("Segoe UI", 13, "bold"), fg="white", bg="#2a2a2a"
            ).pack(pady=(0, 12))

            # --- Vault Selection ---
            accounts = self.auth_manager.list_accounts()
            self.selected_vault = tk.StringVar()
            
            last_used = self.auth_manager.get_last_used_vault()
            if last_used:
                self.selected_vault.set(last_used)
            
            for acc in accounts:
                vault_id = acc["vault_id"]
                display_name = acc.get("display_name", "My Vault")
                last_login = acc.get("last_login", "Never")
            
                tk.Radiobutton(
                    card,
                    text=f"{display_name}  (Last: {last_login[:10]})",
                    variable=self.selected_vault,
                    value=vault_id,
                    bg="#2a2a2a",
                    fg="white",
                    selectcolor="#333333",
                    activebackground="#2a2a2a",
                    activeforeground="white",
                    anchor="w",
                    font=("Segoe UI", 10)
                ).pack(fill="x", pady=2)
            
            tk.Label(card, text="", bg="#2a2a2a").pack(pady=6)


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
            self._make_button(card, "+ Create New Vault", self._switch_to_create_mode)


            # Bind Enter key
            self.pwd_entry.bind("<Return>", lambda e: self._on_login())



    def _switch_to_create_mode(self):
       self.root.destroy()
       result = run_auth_gate(self.auth_manager, create_mode=True)
       self.authenticated = result



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


    def _on_pwd_keystroke(self, event=None):
        """Live strength feedback while typing (create-password mode)."""
        pwd = self.pwd_entry.get()
        ok, reason = self.auth_manager.validate_password_strength(pwd)
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
        ok, reason = self.auth_manager.validate_password_strength(pwd)
        if not ok:
            messagebox.showerror("Weak Password", reason, parent=self.root)
            return
        if pwd != confirm:
            messagebox.showerror("Mismatch",
                                 "Passwords do not match.", parent=self.root)
            return

        # Create
        self.auth_manager.create_password(pwd)
        self.authenticated = True
        self.root.destroy()

    def _on_login(self):
        """Handle the 'Unlock' button."""
        if self.auth_manager.is_locked():
            secs = int(self.auth_manager.lockout_remaining_seconds())
            self.status_label.config(
                text=f"Locked. Try again in {secs}s."
            )
            self._tick_lockout()
            return

        pwd = self.pwd_entry.get()
        selected_vault_id = self.selected_vault.get()
        
        if not selected_vault_id:
            self.status_label.config(text="Please select a vault.")
            return
        if self.auth_manager.login(pwd, selected_vault_id):
            self.authenticated = True
            self.root.destroy()
        else:
            self.pwd_entry.delete(0, tk.END)
            if self.auth_manager.is_locked():
                self.status_label.config(text="Too many attempts. Locked for 60s.")
                self._tick_lockout()
            else:
                self.status_label.config(text="Invalid password.")

    def _tick_lockout(self):
        """Update the lockout countdown every second."""
        if self.auth_manager.is_locked():
            secs = int(self.auth_manager.lockout_remaining_seconds())
            self.status_label.config(text=f"Locked. Try again in {secs}s.")
            self.root.after(1000, self._tick_lockout)
        else:
            self.status_label.config(text="")

    def _on_close(self):
        """User closed the window without authenticating."""
        self.authenticated = False
        self.root.destroy()