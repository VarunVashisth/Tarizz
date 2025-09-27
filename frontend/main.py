import tkinter as tk
from tkinter import ttk
import math
from project_manager import create_project_manager  # <-- Import the function

class EditableLabel:
    """Custom editable label that switches to entry on click"""
    
    def __init__(self, parent, text, font, fg='white', bg='#3a3a3a'):
        self.parent = parent
        self.text = text
        self.font = font
        self.fg = fg
        self.bg = bg
        self.is_editing = False
        
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
        if new_text:
            self.text = new_text
            self.label.config(text=new_text)
        
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
        
        # Title (editable)
        self.title_editor = EditableLabel(
            self.title_container, title, 
            font=('Segoe UI', 12, 'bold'), 
            fg='white', bg='#3a3a3a'
        )
        self.title_editor.pack(fill='both', expand=True)
        
        # Description (editable)
        self.desc_editor = EditableLabel(
            self.desc_container, description,
            font=('Segoe UI', 9),
            fg='#cccccc', bg='#3a3a3a'
        )
        self.desc_editor.pack(fill='both', expand=True)
        
    def bind_events(self):
        """Bind drag and hover events"""
        # Bind drag events only to frame (not labels)
        self.frame.bind('<Button-1>', self.on_click)
        self.frame.bind('<B1-Motion>', self.on_drag)
        self.frame.bind('<ButtonRelease-1>', self.on_release)
        # Open project manager on double-click
        self.frame.bind('<Double-Button-1>', self.on_double_click)
        
        # Bind hover events to all widgets including containers
        widgets = [self.frame, self.title_container, self.desc_container, 
                  self.title_editor.label, self.desc_editor.label]
        for widget in widgets:
            widget.bind('<Enter>', self.on_hover_enter)
            widget.bind('<Leave>', self.on_hover_leave)
        
        # Bind label clicks for editing (separate from dragging)  
        self.title_editor.label.bind('<Button-1>', self.on_title_click)
        self.desc_editor.label.bind('<Button-1>', self.on_desc_click)

    def on_double_click(self, event):
        """Open the project manager UI for this card in a new window"""
        self.open_project_manager()

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
        
    def open_project_manager(self):
        """Open the project manager UI for this card in a new window"""
        win = tk.Toplevel(self.dashboard.root)
        win.title(f"Project Manager - {self.get_title()}")
        win.geometry("900x600")
        create_project_manager(win, self.project_data)

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
    
    def __init__(self):
        self.root = tk.Tk()
        self.cards = []
        self.selected_card = None
        
        self.setup_window()
        self.create_sidebar()
        self.create_canvas()
        self.create_sample_cards()
        
    def setup_window(self):
        """Configure main window"""
        self.root.title("Project Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1a1a1a')
        self.root.minsize(900, 600)
        
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
        
    def create_canvas(self):
        """Create main canvas area"""
        self.canvas_container = tk.Frame(self.root, bg='#1a1a1a')
        self.canvas_container.pack(side='right', fill='both', expand=True, padx=(5, 10), pady=10)
        
        # Canvas for smooth scrolling (future enhancement)
        self.canvas_frame = tk.Frame(self.canvas_container, bg='#1a1a1a')
        self.canvas_frame.pack(fill='both', expand=True)
        
    def create_sample_cards(self):
        """Create initial sample cards"""
        sample_projects = [
            ("Website Redesign", "Modernize UI/UX with responsive design"),
            ("Mobile App", "Cross-platform customer engagement app"),
            ("API Integration", "Connect third-party services")
        ]
        
        for title, desc in sample_projects:
            self.add_card(title, desc)
    
    def add_new_project(self):
        """Add a new empty project card"""
        self.add_card("New Project", "Click to edit description")
        
    def add_card(self, title="New Project", description="Click to edit"):
        """Add a card to the dashboard"""
        card = ProjectCard(self, title, description)
        self.cards.append(card)
        self.arrange_cards()
        
    def delete_selected_project(self):
        """Delete the currently selected card"""
        if self.selected_card and self.selected_card in self.cards:
            self.selected_card.destroy()
            self.cards.remove(self.selected_card)
            self.selected_card = None
            self.update_selection_ui()
            self.arrange_cards()
    
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
    
    def run(self):
        """Start the application"""
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (700 // 2)
        self.root.geometry(f"1200x700+{x}+{y}")
        
        # Bind window resize
        self.root.bind('<Configure>', self.on_window_resize)
        
        # Start main loop
        self.root.mainloop()
        
    def on_window_resize(self, event):
        """Handle window resize"""
        if event.widget == self.root:
            self.root.after(100, self.arrange_cards)

# Run the application
if __name__ == "__main__":
    app = ProjectDashboard()
    app.run()