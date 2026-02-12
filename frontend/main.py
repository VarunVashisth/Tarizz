import tkinter as tk
from tkinter import PhotoImage, ttk
import math
from project_manager import create_project_manager  # <-- Import the function
import os , sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.auth_manager import AuthManager
from backend.auth_ui import run_auth_gate




class EditableLabel:
    """Custom editable label that switches to entry on click"""
    
    def __init__(self, parent, text, font, fg='white', bg='#3a3a3a', on_change_callback=None):
        self.parent = parent
        self.text = text
        self.font = font
        self.fg = fg
        self.bg = bg
        self.is_editing = False
        self.on_change_callback = on_change_callback  # ← NEW: callback for changes

        # Create label
        self.label = tk.Label(
            parent, text=text, font=font, fg=fg, bg=bg,
            cursor='hand2', anchor='w'
        )
        
        # Bind click event
        self.label.bind('<Button-1>', self.start_edit)
        
    def start_edit(self, event):
        """Switch to edit mode"""
        if self.is_editing:
            return
            
        self.is_editing = True
        
        # Hide label and show entry
        self.label.pack_forget()
        
        self.entry = tk.Entry(
            self.parent, font=self.font, fg=self.fg, bg=self.bg,
            relief='flat', highlightthickness=0, insertbackground='white'
        )
        self.entry.pack(fill='both', expand=True, pady=2)
        self.entry.insert(0, self.text)
        self.entry.select_range(0, tk.END)
        self.entry.focus()
        
        # Bind events
        self.entry.bind('<Return>', self.finish_edit)
        self.entry.bind('<FocusOut>', self.finish_edit)
        self.entry.bind('<Escape>', self.cancel_edit)
        
        # Schedule focus after widget is created
        self.parent.after(10, lambda: self.entry.focus_set())
        
    def finish_edit(self, event=None):
        """Save changes and return to label"""
        if not self.is_editing:
            return
            
        new_text = self.entry.get().strip()
        if new_text and new_text != self.text:  # ← CHANGED: check if actually changed
            self.text = new_text
            self.label.config(text=new_text)
            # ← NEW: trigger callback when text actually changes
            if self.on_change_callback:
                self.on_change_callback()
        
        self.entry.destroy()
        self.label.pack(fill='both', expand=True)
        self.is_editing = False
        
    def cancel_edit(self, event=None):
        """Cancel editing and return to label"""
        if not self.is_editing:
            return
            
        self.entry.destroy()
        self.label.pack(fill='both', expand=True)
        self.is_editing = False
        
    def pack(self, **kwargs):
        """Delegate pack to label"""
        self.label.pack(**kwargs)
        
    def get_text(self):
        """Get current text"""
        return self.text
    


class ProjectCard:
    """Draggable project card with editable content"""
    
    def __init__(self, dashboard, title="New Project", description="Click to edit description"):
        self.dashboard = dashboard
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.original_index = 0
        self.current_index = 0

        self.project_data = {}  # Unique project data for this card
        self.db_id = None       # backend attaches this; None = not yet persisted

        # Create card frame with rounded appearance
        self.frame = tk.Frame(
            dashboard.canvas_frame, 
            bg='#3a3a3a', 

            relief='raised', 
            bd=0,
            padx=15, 
            pady=15
        )
        
        # Configure frame appearance
        self.frame.configure(
            highlightbackground='#4a4a4a',
            highlightthickness=1
        )
        
        # Create content
        self.create_content(title, description)
        self.bind_events()
        
    def create_content(self, title, description):
        """Create card content with editable labels"""
        # Create fixed-height containers to prevent layout shifts
        self.title_container = tk.Frame(self.frame, bg='#3a3a3a', height=25)
        self.title_container.pack(fill='x', pady=(0, 8))
        self.title_container.pack_propagate(False)
        
        self.desc_container = tk.Frame(self.frame, bg='#3a3a3a', height=60)
        self.desc_container.pack(fill='both', expand=True)
        self.desc_container.pack_propagate(False)
        
        # ← CHANGED: pass callback to save when edited
        self.title_editor = EditableLabel(
            self.title_container, title, 
            font=('Segoe UI', 12, 'bold'), 
            fg='white', bg='#3a3a3a',
            on_change_callback=self._on_card_edited  # ← NEW
        )
        self.title_editor.pack(fill='both', expand=True)
        
        # ← CHANGED: pass callback to save when edited
        self.desc_editor = EditableLabel(
            self.desc_container, description,
            font=('Segoe UI', 9),
            fg='#cccccc', bg='#3a3a3a',
            on_change_callback=self._on_card_edited  # ← NEW
        )
        self.desc_editor.pack(fill='both', expand=True)
    
    # ← NEW: auto-save callback
    def _on_card_edited(self):
        """Called when title or description changes - triggers immediate save"""
        try:
            from backend.database import _db_instance
            if _db_instance:
                if self.db_id:
                    _db_instance.update_project(
                        self.db_id,
                        self.get_title(),
                        self.get_description(),
                        self.dashboard.get_card_index(self)
                    )
                else:
                    # Create new project in database
                    self.db_id = _db_instance.create_project(
                        self.get_title(),
                        self.get_description(),
                        self.dashboard.get_card_index(self)
                    )
                    self.project_data = {'id': self.db_id}
        except Exception as e:
            print(f"Auto-save failed: {e}")
        
    def bind_events(self):
        """Bind drag and hover events"""
        # Bind drag events only to frame (not labels)
        self.frame.bind('<Button-1>', self.on_click)
        self.frame.bind('<B1-Motion>', self.on_drag)
        self.frame.bind('<ButtonRelease-1>', self.on_release)
        # Open project manager on double-click
        self.frame.bind('<Double-Button-1>', lambda event: self.dashboard.open_project_manager(self))
        
        # Bind hover events to all widgets including containers
        widgets = [self.frame, self.title_container, self.desc_container, 
                  self.title_editor.label, self.desc_editor.label]
        for widget in widgets:
            widget.bind('<Enter>', self.on_hover_enter)
            widget.bind('<Leave>', self.on_hover_leave)
        
        # Bind label clicks for editing (separate from dragging)  
        self.title_editor.label.bind('<Button-1>', self.on_title_click)
        self.desc_editor.label.bind('<Button-1>', self.on_desc_click)

 #   def on_double_click(self, event):
 #       self.open_project_manager()

    def on_click(self, event):
        """Handle card selection and start dragging"""
        # Select this card
        self.dashboard.select_card(self)
        # Start dragging
        self.is_dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        
        # Visual feedback
        self.frame.configure(bg='#4a4a4a')
        self.frame.lift()
        
        # Store original position
        self.original_index = self.dashboard.get_card_index(self)
        
    def on_title_click(self, event):
        """Handle title click for editing"""
        # Select card first
        self.dashboard.select_card(self)
        # Start editing title
        self.title_editor.start_edit(event)
        # Prevent event propagation
        return "break"
    
    def on_desc_click(self, event):
        """Handle description click for editing"""
        # Select card first  
        self.dashboard.select_card(self)
        # Start editing description
        self.desc_editor.start_edit(event)
        # Prevent event propagation
        return "break"
        
    def on_drag(self, event):
        """Handle dragging motion"""
        if not self.is_dragging:
            return
            
        # Calculate movement
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y
        
        # Move card
        current_x = self.frame.winfo_x()
        current_y = self.frame.winfo_y()
        new_x = current_x + dx
        new_y = current_y + dy
        
        # Keep within bounds
        canvas_width = self.dashboard.canvas_frame.winfo_width()
        canvas_height = self.dashboard.canvas_frame.winfo_height()
        card_width = 280
        card_height = 120
        
        new_x = max(20, min(new_x, canvas_width - card_width - 20))
        new_y = max(20, min(new_y, canvas_height - card_height - 20))
        
        self.frame.place(x=new_x, y=new_y, width=card_width, height=card_height)
        
        # Update drag start position
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        
        # Check for position changes
        self.check_position_change(new_x, new_y)
        
    def on_release(self, event):
        """Stop dragging and arrange"""
        if not self.is_dragging:
            return
            
        self.is_dragging = False
        
        # Reset appearance
        self.frame.configure(bg='#3a3a3a')
        
        # Trigger rearrangement
        self.dashboard.arrange_cards()
        
    def check_position_change(self, x, y):
        """Check if card should change position in layout"""
        # Calculate which grid position this corresponds to
        cols = self.dashboard.get_columns()
        col = min(x // 300, cols - 1)
        row = y // 140
        new_index = row * cols + col
        
        # Clamp to valid range
        max_index = len(self.dashboard.cards) - 1
        new_index = max(0, min(new_index, max_index))
        
        if new_index != self.current_index:
            self.current_index = new_index
            self.dashboard.reorder_card(self, new_index)
    
    def on_hover_enter(self, event):
        """Hover effect"""
        if not self.is_dragging and self != self.dashboard.selected_card:
            self.frame.configure(highlightthickness=2, highlightbackground='#666666')
            
    def on_hover_leave(self, event):
        """Remove hover effect"""
        if not self.is_dragging:
            if self == self.dashboard.selected_card:
                self.frame.configure(highlightthickness=2, highlightbackground='#0078d4')
            else:
                self.frame.configure(highlightthickness=1, highlightbackground='#4a4a4a')
    
    def animate_to_position(self, target_x, target_y, callback=None):
        """Smooth animation to target position"""
        current_x = self.frame.winfo_x()
        current_y = self.frame.winfo_y()
        
        # Calculate steps
        steps = 10
        dx = (target_x - current_x) / steps
        dy = (target_y - current_y) / steps
        
        def animate_step(step):
            if step >= steps:
                self.frame.place(x=target_x, y=target_y, width=280, height=120)
                if callback:
                    callback()
                return
                
            new_x = current_x + dx * step
            new_y = current_y + dy * step
            self.frame.place(x=int(new_x), y=int(new_y), width=280, height=120)
            
            self.dashboard.root.after(20, lambda: animate_step(step + 1))
        
        animate_step(1)
    
    def get_title(self):
        """Get card title"""
        return self.title_editor.get_text()
        
    def get_description(self):
        """Get card description"""  
        return self.desc_editor.get_text()
    
    def destroy(self):
        """Clean up card"""
        self.frame.destroy()

class ProjectDashboard:
    """Main dashboard class"""
    
    def __init__(self,auth_manager):
        self.root = tk.Tk()
        self.selected_card = None
        self.auth_manager = auth_manager

        
        self.setup_window()
        self.create_sidebar()
        self.create_canvas()

        from backend.database import get_all_projects , create_project
        self.cards = []
        projects = get_all_projects()

        if projects:
            for proj in sorted(projects , key=lambda p: p['card_order']):
                card = ProjectCard(
                    dashboard = self,
                    title=proj['title'], 
                    description=proj['description'] if proj['description'] else ""
                    )
                card.db_id = proj['id']
                card.project_data = {'id': proj['id']}
                self.cards.append(card)
        else:
            new_id = create_project(
                title = "Sampple Project",
                description = "Welcome to Tarriz",
                card_order = 0
            )

            card = ProjectCard(
                dashboard = self,
                title="Sample Project",
                description="Welcome to Tarizz"
            )
            card.db_id = new_id
            card.project_data = {'id': new_id}
            self.cards.append(card)

        self.arrange_cards()
        
    def setup_window(self):
        """Configure main window"""
        self.root.title(f"Tarizz - Vault: {self.auth_manager.vault_id}")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1a1a1a')
        self.root.minsize(900, 600)


        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_dir, "data", "tarizzlogo.png")
        if os.path.exists(logo_path):
            self.logo = PhotoImage(file=logo_path)
            self.root.iconphoto(False, self.logo)

        # -------------------------
        # Create Menu Bar
        # -------------------------
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        menubar.configure(                    
                    background='#2a2a2a',
                    foreground='white',
                    )

        # Vault Menu
        vault_menu = tk.Menu(menubar, tearoff=0)
        vault_menu.add_command(label="Switch Vault", command=self.switch_vault)
        vault_menu.add_command(label="Create New Vault", command=self.create_new_vault)
        vault_menu.add_separator()
        vault_menu.add_command(label="Exit", command=self.on_close)
        vault_menu.configure(
                    background='#2a2a2a',
                    foreground='white',
                    activebackground='#404040',
                    activeforeground='white'
                )

        menubar.add_cascade(label="Vault", menu=vault_menu)
        
    def create_sidebar(self):
        """Create left sidebar with controls"""
        self.sidebar = tk.Frame(self.root, bg='#2a2a2a', width=200)
        self.sidebar.pack(side='left', fill='y', padx=(10, 5), pady=10)
        self.sidebar.pack_propagate(False)
        
        # Title
        title = tk.Label(
            self.sidebar, text="Projects", 
            bg='#2a2a2a', fg='white', 
            font=('Segoe UI', 16, 'bold')
        )
        title.pack(pady=(20, 30))
        
        # Button style
        btn_style = {
            'bg': '#404040', 'fg': 'white', 
            'font': ('Segoe UI', 10), 'relief': 'flat',
            'padx': 20, 'pady': 12, 'width': 15,
            'cursor': 'hand2', 'activebackground': '#505050',
            'activeforeground': 'white'
        }
        
        # Add Project button
        self.add_btn = tk.Button(
            self.sidebar, text="+ Add Project",
            command=self.add_new_project, **btn_style
        )
        self.add_btn.pack(pady=(0, 10))
        
        # Delete Project button
        self.delete_btn = tk.Button(
            self.sidebar, text="🗑 Delete Selected",
            command=self.delete_selected_project,
            state='disabled', **btn_style
        )
        self.delete_btn.pack(pady=(0, 20))
        
        # Info label
        self.info_label = tk.Label(
            self.sidebar, text="Click a card to select",
            bg='#2a2a2a', fg='#888888',
            font=('Segoe UI', 8), wraplength=180
        )
        self.info_label.pack(pady=20)

        self.hint_label = tk.Label(
        self.sidebar,
        text="Hints:\n• Ctrl+h: Highlight\n• Double-click on card to open \n• Drag and drop to rearrange \n•Codeblock: '''code'''\n•bold/italc/underline: Ctrl+b/i/u",
        bg='#2a2a2a', fg='#AAAAAA',
        font=('Segoe UI', 8), justify='left', wraplength=180
        )
        self.hint_label.pack(side='bottom', pady=10)


        
    def create_canvas(self):
        """Create main canvas area"""
        self.canvas_container = tk.Frame(self.root, bg='#1a1a1a')
        self.canvas_container.pack(side='right', fill='both', expand=True, padx=(5, 10), pady=10)
        
        # Canvas for smooth scrolling (future enhancement)
        self.canvas_frame = tk.Frame(self.canvas_container, bg='#1a1a1a')
        self.canvas_frame.pack(fill='both', expand=True)
        
    def add_new_project(self):
        """Add a new empty project card"""
        self.add_card("New Project", "Click to edit description")
        
    def add_card(self, title="New Project", description="Click to edit"):
        
            # 1. Decide position = last position + 1
            position = len(self.cards)   # new card goes at the end
        
            # 2. Create in DATABASE first → get real id
            from backend.database import create_project   # make sure this import exists at top
        
            project_id = create_project(
                title=title,
                description=description,
                card_order=position
            )
        
            # 3. Now create the visible card with real database id
            card = ProjectCard(self, title=title, description=description)
            card.db_id = project_id
            card.project_data = {'id': project_id}          # crucial for ProjectManager
        
            self.cards.append(card)

            self.arrange_cards()
            self.select_card(card)  # auto-select new card for convenience
    def open_project_manager(self, card):

        if hasattr(card , '_manager_window') and card._manager_window and card._manager_window.winfo_exists():
            card._manager_window.lift()
            card._manager_window.focus_force()
            return
        window = create_project_manager(None, project_data=card.project_data, parent_card=card)
        card._manager_window = window  # attach reference to card for later use

        def on_close():
            card._manager_window = None  # clear reference on close
            window.destroy()
        window.protocol("WM_DELETE_WINDOW", on_close)
        
    def delete_selected_project(self):
            """Delete the currently selected card"""
            if not self.selected_card or self.selected_card not in self.cards:
                    return
        
            from backend.database import delete_project, get_db   # add imports if missing
        
            project_id = getattr(self.selected_card, 'db_id', None)
        
            if project_id is not None:
                db = get_db()
                delete_project(project_id)   # deletes project + cascades to nodes/content/media
        
            # Remove from UI
            self.selected_card.destroy()
            self.cards.remove(self.selected_card)
            self.selected_card = None
            self.update_selection_ui()
            self.arrange_cards()

    def save_cards_to_db(self):
        from backend.database import create_project, update_project
        for index , card in enumerate(self.cards):
            title = card.get_title()
            desc = card.get_description()

            if hasattr(card, 'db_id') and card.db_id is not None:
                # Update existing project
                update_project(
                    project_id = card.db_id,
                    title = title,
                    description = desc,
                    card_order = index
                )
            else:
                new_id = create_project(
                    title = title,
                    description = desc,
                    card_order = index
                )
                card.db_id = new_id
                card.project_data = {'id': new_id}

    def get_columns(self):
        """Calculate number of columns based on canvas width"""
        canvas_width = self.canvas_frame.winfo_width()
        if canvas_width <= 300:
            return 1
        return max(1, (canvas_width - 40) // 300)
    
    def arrange_cards(self):
        """Arrange all cards in a grid with animation"""
        if not self.cards:
            return
            
        cols = self.get_columns()
        card_width = 280
        card_height = 120
        margin = 20
        spacing_x = 20
        spacing_y = 20
        
        for i, card in enumerate(self.cards):
            row = i // cols
            col = i % cols
            
            x = margin + col * (card_width + spacing_x)
            y = margin + row * (card_height + spacing_y)
            
            # Animate to position if not currently dragging
            if not card.is_dragging:
                card.animate_to_position(x, y)
            
            # Update current index
            card.current_index = i
    
    def get_card_index(self, card):
        """Get the current index of a card"""
        try:
            return self.cards.index(card)
        except ValueError:
            return 0
    
    def reorder_card(self, card, new_index):
        """Reorder card to new position"""
        if card not in self.cards:
            return
            
        # Remove card from current position
        self.cards.remove(card)
        
        # Insert at new position
        new_index = max(0, min(new_index, len(self.cards)))
        self.cards.insert(new_index, card)
    
    def select_card(self, card):
        """Select a card"""
        # Deselect previous card
        if self.selected_card:
            self.selected_card.frame.configure(highlightbackground='#4a4a4a', highlightthickness=1)
            
        # Select new card
        self.selected_card = card
        card.frame.configure(highlightbackground='#0078d4', highlightthickness=2)
        self.update_selection_ui()
        
    def update_selection_ui(self):
        """Update UI based on selection"""
        if self.selected_card:
            self.delete_btn.configure(state='normal')
            title = self.selected_card.get_title()
            self.info_label.configure(text=f"Selected: {title[:20]}...")
        else:
            self.delete_btn.configure(state='disabled')
            self.info_label.configure(text="Click a card to select")

    def switch_vault(self):
        """
        Logout current vault and re-run authentication gate.
        """
    
        from backend.database import reset_database, set_db_path, Database
        import sys
    
        # 1️⃣ Destroy current UI FIRST
        self.root.destroy()
    
        # 2️⃣ Logout auth session
        self.auth_manager.logout()
    
        # 3️⃣ Reset database singleton properly
        reset_database()
    
        # 4️⃣ Relaunch authentication window
        authenticated = run_auth_gate(self.auth_manager)
    
        if not authenticated:
            sys.exit()
    
        # 5️⃣ Rebind DB to new vault
        set_db_path(self.auth_manager.get_database_path())
        Database.set_session_key(self.auth_manager.get_session_key())
    
        # 6️⃣ Relaunch dashboard cleanly
        new_app = ProjectDashboard(self.auth_manager)
        new_app.run()
    
    def create_new_vault(self):
        """
        Create a brand new vault and open password setup UI.
        """
    
        from backend.database import reset_database, set_db_path, Database
        import sys
    
        # Destroy dashboard first
        self.root.destroy()
    
        # Reset DB
        reset_database()
    
        # Clear current session
        self.auth_manager.logout()
    
        # Launch auth gate in CREATE MODE
        authenticated = run_auth_gate(self.auth_manager, create_mode=True)
    
        if not authenticated:
            sys.exit()
    
        # Bind new vault DB
        set_db_path(self.auth_manager.get_database_path())
        Database.set_session_key(self.auth_manager.get_session_key())
    
        # Relaunch dashboard
        new_app = ProjectDashboard(self.auth_manager)
        new_app.run()


    def on_close(self):
        """Handle application close - save state"""
        self.save_cards_to_db()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        # Centre window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"1200x700+{x}+{y}")
        
        # Bind window resize
        self.root.bind('<Configure>', self.on_window_resize)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start main loop
        self.root.mainloop()
        
    def on_window_resize(self, event):
        """Handle window resize"""
        if event.widget == self.root:
            self.root.after(100, self.arrange_cards)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    """
    Main entry point with authentication flow.
    
    Flow:
    1. Initialize AuthManager
    2. Show authentication window
    3. If authenticated, launch dashboard
    4. Dashboard uses vault-specific database
    """
    # Determine data directory
    # For development, use a local directory
    # For production, use appropriate user data directory
    if os.name == 'nt':  # Windows
        data_dir = os.path.join(os.environ.get('APPDATA', '.'), 'Tarizz')
    else:  # macOS/Linux
        data_dir = os.path.join(os.path.expanduser('~'), '.tarizz')
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"Tarizz data directory: {data_dir}")
    
    # Initialize authentication manager
    auth_manager = AuthManager(data_dir)
    
    # Show authentication window and wait for login
    authenticated = run_auth_gate(auth_manager)
    
    if not authenticated:
        print("Authentication cancelled")
        return
    
    print(f"Authenticated successfully! Vault: {auth_manager.vault_id}")
    print(f"Database path: {auth_manager.get_database_path()}")

    from backend.database import set_db_path , Database
    
    set_db_path(auth_manager.get_database_path())
    Database.set_session_key(auth_manager.get_session_key())

    # Launch main dashboard with authenticated session
    app = ProjectDashboard(auth_manager)
    app.run()


if __name__ == "__main__":
    main()