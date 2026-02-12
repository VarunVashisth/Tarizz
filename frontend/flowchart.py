import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import tkinter.font as tkFont
from PIL import Image, ImageDraw, ImageFont


class FlowchartEditor(tk.Frame):
    global GRID_SIZE
    GRID_SIZE = 20
    def __init__(self, parent):
        super().__init__(parent, bg='#222222')
        self.current_tool = 'pointer'
        self.start_x = self.start_y = None
        self.current_item = None
        self.shapes = []
        self.text_items = {}
        self.text_fonts = {}
        self.lines = []
        self.zoom_factor = 1.0
        self.move_start = None
        self.pan_start = None

        # Toolbar
        toolbar = tk.Frame(self, bg='#222222')
        toolbar.pack(side='top', fill='x')
        btn_style = {
            'bg': '#222222', 'fg': "#3a3636",
            'activebackground': '#333333', 'activeforeground': '#ffffff',
            'relief': 'flat', 'bd': 0,
            'font': ('Segoe UI', 10), 'highlightthickness': 0,
            'padx': 6, 'pady': 4, 'cursor': 'hand2',
            'borderwidth': 1, 'highlightbackground': '#3a3636', 'highlightcolor': '#3a3636',
        }

        for text, tool in [('Pointer','pointer'),('Rectangle','rectangle'),('Oval','oval'),
                           ('Diamond','diamond'),('Line','line'),('Arrow','arrow'),
                           ('Delete','delete'),('Zoom In','zoom_in'),('Zoom Out','zoom_out'),
                           ('Export PNG','export')]:
            tk.Button(toolbar, text=text, command=lambda t=tool: self.set_tool(t), **btn_style).pack(side='left', padx=2)

        # Scrollable Canvas
        self.canvas_container = tk.Frame(self)
        self.canvas_container.pack(fill='both', expand=True, padx=10, pady=10)

        self.h_scroll = tk.Scrollbar(self.canvas_container, orient='horizontal', bg='#222222', troughcolor='#333333', width=16)
        self.h_scroll.pack(side='bottom', fill='x')
        self.v_scroll = tk.Scrollbar(self.canvas_container, orient='vertical', bg='#222222', troughcolor='#333333', width=16)
        self.v_scroll.pack(side='right', fill='y')

        self.canvas = tk.Canvas(self.canvas_container, bg='#1e1e1e', highlightthickness=0,
                                xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.canvas.pack(fill='both', expand=True)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.canvas.config(scrollregion=(0,0,3000,3000))

        # Bindings
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-2>", self.end_pan)

        parent.bind_all("<Control-t>", self.text_hotkey)
        parent.bind("<Configure>", lambda e: self.draw_grid())

        self.canvas.bind("<Escape>", self.cancel_text_mode)

        self.after_idle(self.draw_grid)


    def set_color(self , color):
        self.current_color = color


    def draw_grid(self):
        self.canvas.delete('gridline')
        step = 20
        radius = 1
        max_width = 2000
        max_height = 2000
        for i in range(0, max_width, step):
            for j in range(0, max_height, step):
                self.canvas.create_oval(i-radius, j-radius, i+radius, j+radius,
                                        fill='#333333', outline='', tags='gridline')

    def set_tool(self, tool):
        if tool == 'zoom_in':
            self.zoom(1.2)
            return
        elif tool == 'zoom_out':
            self.zoom(0.8)
            return
        elif tool == 'export':
            self.export_png()
            return
        self.current_tool = tool
        self.current_item = None
        self.canvas.config(cursor='arrow' if tool=='pointer' else 'cross')


    def text_hotkey(self, event):
        """Ctrl+T → Text mode: click shape to add/edit text"""
        # Toggle off if active
        if self.current_tool == 'text':
            self.cancel_text_mode(event)
            return

        self.current_tool = 'text'
        self.canvas.config(cursor='xterm')

        # Hint (persistent)
        self.canvas.delete("text_hint")
        self.canvas.create_text(
            20, 20,
            text="Click a shape to add/edit text\nPress Esc to cancel",
            fill='#888888', font=('Segoe UI', 9), anchor='nw',
            tags="text_hint"
        )

        def handle_click(evt):
            # Safety check
            if self.current_tool != 'text':
                return

            # Find shape
            items = self.canvas.find_overlapping(evt.x-8, evt.y-8, evt.x+8, evt.y+8)
            target = None
            for item in reversed(items):
                if 'shape' in self.canvas.gettags(item):
                    target = item
                    break

            # Show dialog (blocks execution)
            if target:
                current_text = ""
                if target in self.text_items:
                    current_text = self.canvas.itemcget(self.text_items[target], 'text')

                new_text = simpledialog.askstring(
                    "Text",
                    "Enter or edit text for shape:",
                    initialvalue=current_text,
                    parent=self.winfo_toplevel()
                )

                if new_text is not None:  # OK pressed
                    if target not in self.text_items:
                        cx = (self.canvas.coords(target)[0] + self.canvas.coords(target)[2]) / 2
                        cy = (self.canvas.coords(target)[1] + self.canvas.coords(target)[3]) / 2
                        tid = self.canvas.create_text(
                            cx, cy,
                            text=new_text,
                            fill='#e0e0ff',
                            font=('Segoe UI', 14),
                            tags=('attached_text',)
                        )
                        self.text_items[target] = tid
                        self.text_fonts[target] = 14
                    else:
                        tid = self.text_items[target]
                        self.canvas.itemconfig(tid, text=new_text)

                    self.update_shape_size(target, new_text)

            # Exit mode AFTER dialog (or click outside)
            self.cancel_text_mode(evt)

        # Bind click - KEEP ALIVE until explicit cancel
        if hasattr(self, '_text_click_id'):
            try:
                self.canvas.unbind("<Button-1>", self._text_click_id)
            except:
                pass

        self._text_click_id = self.canvas.bind("<Button-1>", handle_click, add=True)  # add=True prevents overwriting other bindings

        print("[TEXT MODE] ENTERED — click shape or Esc to exit")

    def cancel_text_mode(self, event=None):
        if self.current_tool == 'text':
            self.current_tool = 'pointer'
            self.canvas.config(cursor='arrow')
            self.canvas.delete("text_hint")
            if hasattr(self, '_text_click_id'):
                try:
                    self.canvas.unbind("<Button-1>", self._text_click_id)
                    del self._text_click_id
                except:
                    pass
            print("[TEXT MODE] EXITED")
    def measure_text(self, text, font_size=12):
        f = tkFont.Font(family='Segoe UI', size=int(font_size))
        width = f.measure(text) + 20
        height = f.metrics("linespace") + 20
        return width, height

    def update_shape_size(self, shape, text):
        if not text:
            return

        base_font_size = self.text_fonts.get(shape, 12)
        text_width, text_height = self.measure_text(text, base_font_size)

        # Generous symmetric padding
        padding_x = 50
        padding_y = 40

        # Minimum sizes to avoid tiny shapes
        min_width = 140
        min_height = 70

        width = max(text_width + padding_x * 2, min_width)
        height = max(text_height + padding_y * 2, min_height)

        shape_type = self.canvas.type(shape)

        cx = (self.canvas.coords(shape)[0] + self.canvas.coords(shape)[2]) / 2
        cy = (self.canvas.coords(shape)[1] + self.canvas.coords(shape)[3]) / 2

        if shape_type in ['rectangle', 'oval']:
            self.canvas.coords(shape,
                               cx - width/2, cy - height/2,
                               cx + width/2, cy + height/2)

        elif shape_type == 'polygon':  # diamond
            points = [
                cx, cy - height/2,
                cx + width/2, cy,
                cx, cy + height/2,
                cx - width/2, cy
            ]
            self.canvas.coords(shape, *points)

        # Center text
        if shape in self.text_items:
            self.canvas.coords(self.text_items[shape], cx, cy)
            self.canvas.itemconfig(self.text_items[shape],
                                   font=('Segoe UI', int(base_font_size * self.zoom_factor)))

        self.update_scrollregion()
    def update_scrollregion(self):
        bbox = self.canvas.bbox('all')
        if bbox:
            x0, y0, x1, y1 = bbox
            margin = 200
            self.canvas.config(scrollregion=(x0-margin, y0-margin, x1+margin, y1+margin))
        self.draw_grid()

    def on_click(self, event):
        self.start_x, self.start_y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.current_tool == 'pointer':
            items = self.canvas.find_overlapping(self.start_x-1,self.start_y-1,self.start_x+1,self.start_y+1)
            for item in reversed(items):
                if 'shape' in self.canvas.gettags(item):
                    self.current_item = item
                    self.move_start = (self.start_x, self.start_y)
                    break
        elif self.current_tool in ['rectangle','oval','diamond']:
            x, y = self.start_x, self.start_y

            if self.current_tool == 'rectangle':
                item = self.canvas.create_rectangle(
                    x-60, y-30, x+60, y+30,
                    fill='#2a2a3a',           # safe dark fill
                    outline='#6666aa',        # safe outline
                    width=3,
                    tags='shape'
                )
            elif self.current_tool == 'oval':
                item = self.canvas.create_oval(
                    x-60, y-30, x+60, y+30,
                    fill='#2a2a3a',
                    outline='#6666aa',
                    width=3,
                    tags='shape'
                )
            elif self.current_tool == 'diamond':
                points = [x, y-35, x+70, y, x, y+35, x-70, y]
                item = self.canvas.create_polygon(
                    points,
                    fill='#2a2a3a',
                    outline='#6666aa',
                    width=3,
                    smooth=False,  # nice rounded diamond
                    tags='shape'
                )

            self.shapes.append(item)
            self.update_scrollregion()
        elif self.current_tool in ['line','arrow']:
            arrow_type = 'last' if self.current_tool=='arrow' else None
            self.current_item = self.canvas.create_line(self.start_x,self.start_y,self.start_x,self.start_y,
                                                        fill='#e0e0ff', width=2, arrow=arrow_type)
            self.lines.append(self.current_item)
            self.update_scrollregion()
        elif self.current_tool == 'delete':
                    items = self.canvas.find_overlapping(self.start_x-5, self.start_y-5,
                                                         self.start_x+5, self.start_y+5)
                    for item in items:
                        tags = self.canvas.gettags(item)
                        if 'shape' in tags or item in self.lines or item in self.text_items.values():
                            # If it's a shape with text, delete the text too
                            if 'shape' in tags and item in self.text_items:
                                self.canvas.delete(self.text_items[item])
                                del self.text_items[item]
                                if item in self.text_fonts:
                                    del self.text_fonts[item]
        
                            self.canvas.delete(item)
                            if item in self.shapes:
                                self.shapes.remove(item)
                            if item in self.lines:
                                self.lines.remove(item)
                            self.update_scrollregion()
                            break
        elif self.current_tool == 'text':
            items = self.canvas.find_overlapping(self.start_x-1,self.start_y-1,self.start_x+1,self.start_y+1)
            target = None
            for item in reversed(items):
                if 'shape' in self.canvas.gettags(item):
                    target = item
                    break
            if target:
                text = simpledialog.askstring("Input","Enter text for shape:")
                if text:
                    if target not in self.text_items:
                        tx, ty = (self.canvas.coords(target)[0]+self.canvas.coords(target)[2])/2, \
                                 (self.canvas.coords(target)[1]+self.canvas.coords(target)[3])/2
                        tid = self.canvas.create_text(tx,ty,text=text, fill='#e0e0ff', font=('Segoe UI',12))
                        self.text_items[target] = tid
                        self.text_fonts[target] = 12
                    else:
                        self.canvas.itemconfig(self.text_items[target], text=text)
                    self.update_shape_size(target, text)

    def on_drag(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.current_tool == 'pointer' and self.current_item:
            dx = x - self.move_start[0]
            dy = y - self.move_start[1]
            self.canvas.move(self.current_item, dx, dy)
            if self.current_item in self.text_items:
                self.canvas.move(self.text_items[self.current_item], dx, dy)
            self.move_start = (x, y)
            self.update_scrollregion()
        elif self.current_tool in ['line','arrow'] and self.current_item:
            self.canvas.coords(self.current_item,self.start_x,self.start_y,x,y)
            self.update_scrollregion()
        self.save_flowchart(self.current_node_id)  # save after every change

    def snap(value):
        return round(value/GRID_SIZE)*GRID_SIZE
    
    def on_release(self, event):
        if self.current_item is None:
            return

        try:
            # Only attempt coords if item still exists
            if self.current_item in self.canvas.find_all():
                coords = self.canvas.coords(self.current_item)
                # Optional snap
                # snapped = [round(c / GRID_SIZE) * GRID_SIZE for c in coords]
                # self.canvas.coords(self.current_item, *snapped)
            else:
                print("[FLOW] Item was deleted during drag")
        except tk.TclError:
            print("[FLOW] Coords failed - item likely gone")

        self.current_item = None
        self.move_start = None
        self.save_flowchart(self.current_node_id)  # save after every change
    def start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def do_pan(self, event):
        dx, dy = event.x - self.pan_start[0], event.y - self.pan_start[1]
        self.canvas.xview_scroll(-int(dx), "units")
        self.canvas.yview_scroll(-int(dy), "units")
        self.pan_start = (event.x, event.y)

    def end_pan(self, event):
        self.pan_start = None

    def zoom(self, factor):
        self.zoom_factor *= factor
        self.canvas.scale('all', 0, 0, factor, factor)
        for shape, tid in self.text_items.items():
            base_size = self.text_fonts.get(shape, 12)
            self.canvas.itemconfig(tid, font=('Segoe UI', int(base_size*self.zoom_factor)))
        self.update_scrollregion()
    
    def save_flowchart(self, node_id):
        """Save full canvas state including attached text"""
        items_data = []

        for item in self.shapes + self.lines:
            try:
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                fill = self.canvas.itemcget(item, 'fill')
                outline = self.canvas.itemcget(item, 'outline')
                width = float(self.canvas.itemcget(item, 'width'))
                tags = self.canvas.gettags(item)

                data = {
                    'type': item_type,
                    'coords': coords,
                    'fill': fill,
                    'outline': outline,
                    'width': width,
                    'tags': list(tags)
                }

                if item_type == 'line':
                    data['arrow'] = self.canvas.itemcget(item, 'arrow')

                # Attached text
                if item in self.text_items:
                    tid = self.text_items[item]
                    data['text'] = self.canvas.itemcget(tid, 'text')
                    data['text_font'] = self.canvas.itemcget(tid, 'font')
                    data['text_fill'] = self.canvas.itemcget(tid, 'fill')
                    data['text_coords'] = self.canvas.coords(tid)

                items_data.append(data)
            except:
                pass

        state = {
            'items': items_data,
            'zoom_factor': self.zoom_factor,
            'scroll_x': self.canvas.xview(),
            'scroll_y': self.canvas.yview()
        }

        from backend.database import save_subpage
        save_subpage(node_id, state)  # Pass dict directly, not JSON string
        print(f"[FLOW SAVE] Saved {len(items_data)} items")

    def load_flowchart(self, node_id):
        """Load full canvas state with attached text"""
        from backend.database import load_subpage
        data = load_subpage(node_id)

        if not data:
            return

        try:
            # load_subpage now returns a dict directly
            if isinstance(data, str):
                # Legacy format - parse JSON string
                import json
                state = json.loads(data)
            else:
                # New format - already a dict
                state = data

            self.canvas.delete('all')
            self.shapes.clear()
            self.lines.clear()
            self.text_items.clear()
            self.text_fonts.clear()
            
            # Reset zoom factor to 1.0 before loading to prevent cumulative zoom
            self.zoom_factor = 1.0

            for item_data in state.get('items', []):
                try:
                    if item_data['type'] == 'rectangle':
                        item = self.canvas.create_rectangle(*item_data['coords'],
                                                            fill=item_data['fill'],
                                                            outline=item_data['outline'],
                                                            width=item_data['width'],
                                                            tags=item_data['tags'])
                        self.shapes.append(item)

                    elif item_data['type'] == 'oval':
                        item = self.canvas.create_oval(*item_data['coords'],
                                                       fill=item_data['fill'],
                                                       outline=item_data['outline'],
                                                       width=item_data['width'],
                                                       tags=item_data['tags'])
                        self.shapes.append(item)

                    elif item_data['type'] == 'polygon':
                        item = self.canvas.create_polygon(item_data['coords'],
                                                          fill=item_data['fill'],
                                                          outline=item_data['outline'],
                                                          width=item_data['width'],
                                                          smooth=False,  # diamond sharp
                                                          tags=item_data['tags'])
                        self.shapes.append(item)

                    elif item_data['type'] == 'line':
                        item = self.canvas.create_line(*item_data['coords'],
                                                       fill=item_data['fill'],
                                                       width=item_data['width'],
                                                       arrow=item_data.get('arrow'),
                                                       tags=item_data['tags'])
                        self.lines.append(item)

                    # Restore attached text
                    if 'text' in item_data:
                        tx, ty = item_data.get('text_coords', item_data['coords'][:2])
                        tid = self.canvas.create_text(tx, ty,
                                                      text=item_data['text'],
                                                      fill=item_data.get('text_fill', '#e0e0ff'),
                                                      font=item_data.get('text_font', ('Segoe UI', 14)),
                                                      tags=item_data['tags'])
                        self.text_items[item] = tid
                        self.text_fonts[item] = int(item_data['text_font'].split()[-1].replace('-', ''))

                except Exception as e:
                    print(f"[FLOW LOAD] Failed item: {e}")

            # Saved zoom is restored by setting zoom_factor, but we don't re-apply it
            # to avoid cumulative scaling on repeated loads
            saved_zoom = state.get('zoom_factor', 1.0)
            # We keep zoom_factor at 1.0 to prevent cumulative zoom on switching

            scroll_x, scroll_y = state.get('scroll_x', (0,1)), state.get('scroll_y', (0,1))
            self.canvas.xview_moveto(scroll_x[0])
            self.canvas.yview_moveto(scroll_y[0])

            self.update_scrollregion()
            self.draw_grid()
            print(f"[FLOW LOAD] Loaded {len(state.get('items', []))} items")

        except Exception as e:
            print(f"[FLOW LOAD] Full load failed: {e}")

    def export_png(self):
        """Export flowchart as PNG with smart bounding box"""
        file_path = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[("PNG files", "*.png")],
            initialfile="flowchart.png"
        )
        if not file_path:
            return
        
        # Calculate bounding box of all items
        all_items = self.shapes + self.lines
        if not all_items:
            messagebox.showwarning("Empty Flowchart", "No shapes to export!")
            return
        
        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')
        
        for item in all_items:
            coords = self.canvas.coords(item)
            for i in range(0, len(coords), 2):
                if i + 1 < len(coords):
                    x, y = coords[i], coords[i + 1]
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
        
        # Add text bounds
        for shape, tid in self.text_items.items():
            tx, ty = self.canvas.coords(tid)
            min_x = min(min_x, tx - 100)  # Approximate text width
            min_y = min(min_y, ty - 20)
            max_x = max(max_x, tx + 100)
            max_y = max(max_y, ty + 20)
        
        # Add padding
        padding = 50
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding
        
        width = int(max_x - min_x)
        height = int(max_y - min_y)
        
        # Create image
        img = Image.new('RGB', (width, height), color='#1e1e1e')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("segoeui.ttf", 14)
        except:
            try:
                font = ImageFont.truetype("Segoe UI.ttf", 14)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                except:
                    font = ImageFont.load_default()
        
        # Draw shapes
        for shape in self.shapes:
            coords = self.canvas.coords(shape)
            translated = [(coords[i] - min_x, coords[i+1] - min_y) for i in range(0, len(coords), 2)]
            flat_coords = [c for pair in translated for c in pair]
            
            shape_type = self.canvas.type(shape)
            fill = self.canvas.itemcget(shape, 'fill')
            outline = self.canvas.itemcget(shape, 'outline')
            w = int(float(self.canvas.itemcget(shape, 'width')))
            
            if shape_type == 'rectangle':
                draw.rectangle(flat_coords, fill=fill, outline=outline, width=w)
            elif shape_type == 'oval':
                draw.ellipse(flat_coords, fill=fill, outline=outline, width=w)
            elif shape_type == 'polygon':
                draw.polygon(flat_coords, fill=fill, outline=outline)
        
        # Draw lines
        for line in self.lines:
            coords = self.canvas.coords(line)
            translated = [(coords[i] - min_x, coords[i+1] - min_y) for i in range(0, len(coords), 2)]
            flat_coords = [c for pair in translated for c in pair]
            
            color = self.canvas.itemcget(line, 'fill')
            w = int(float(self.canvas.itemcget(line, 'width')))
            draw.line(flat_coords, fill=color, width=w)
            
            if self.canvas.itemcget(line, 'arrow') == 'last':
                x1, y1 = flat_coords[-2], flat_coords[-1]
                draw.polygon([(x1, y1), (x1-10, y1-5), (x1-10, y1+5)], fill=color)
        
        # Draw text
        for shape, tid in self.text_items.items():
            text = self.canvas.itemcget(tid, 'text')
            x, y = self.canvas.coords(tid)
            tx, ty = x - min_x, y - min_y
            
            # Center text
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text((tx - text_width/2, ty - text_height/2), text, font=font, fill='#e0e0ff')
        
        img.save(file_path)
        messagebox.showinfo("Export Complete", f"Flowchart exported to:\n{file_path}")
        print(f"Flowchart exported to {file_path}")