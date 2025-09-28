import tkinter as tk
from tkinter import simpledialog, filedialog
import tkinter.font as tkFont
from PIL import Image, ImageDraw, ImageFont

class FlowchartEditor(tk.Frame):
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
            'bg': '#222222', 'fg': '#cccccc',
            'activebackground': '#333333', 'activeforeground': '#ffffff',
            'relief': 'flat', 'bd': 0,
            'font': ('Segoe UI', 10), 'highlightthickness': 0,
            'padx': 6, 'pady': 4, 'cursor': 'hand2'
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

        parent.bind("<Control-t>", self.text_hotkey)
        parent.bind("<Configure>", lambda e: self.draw_grid())

        self.after_idle(self.draw_grid)

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
        self.current_tool = 'text'
        self.canvas.config(cursor='xterm')

    def measure_text(self, text, font_size=12):
        f = tkFont.Font(family='Segoe UI', size=int(font_size))
        width = f.measure(text) + 20
        height = f.metrics("linespace") + 20
        return width, height

    def update_shape_size(self, shape, text):
        text_width, text_height = self.measure_text(text, self.text_fonts.get(shape,12))
        shape_type = self.canvas.type(shape)
        if shape_type in ['rectangle','oval']:
            aspect_ratio = 2
            width = max(text_width, text_height*aspect_ratio)
            height = width/aspect_ratio
            cx = (self.canvas.coords(shape)[0] + self.canvas.coords(shape)[2])/2
            cy = (self.canvas.coords(shape)[1] + self.canvas.coords(shape)[3])/2
            self.canvas.coords(shape, cx-width/2, cy-height/2, cx+width/2, cy+height/2)
        elif shape_type == 'polygon':
            aspect_ratio = 2
            width = max(text_width, text_height*aspect_ratio)
            height = width/aspect_ratio
            cx = (self.canvas.coords(shape)[0] + self.canvas.coords(shape)[4])/2
            cy = (self.canvas.coords(shape)[1] + self.canvas.coords(shape)[5])/2
            points = [cx, cy-height/2, cx+width/2, cy, cx, cy+height/2, cx-width/2, cy]
            self.canvas.coords(shape, *points)
        if shape in self.text_items:
            self.canvas.coords(self.text_items[shape], cx, cy)
            self.canvas.itemconfig(self.text_items[shape],
                                   font=('Segoe UI', int(self.text_fonts.get(shape,12)*self.zoom_factor)))
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
                item = self.canvas.create_rectangle(x-50,y-25,x+50,y+25,
                                                    fill='#333333', outline='#cccccc', width=2, tags='shape')
            elif self.current_tool == 'oval':
                item = self.canvas.create_oval(x-50,y-25,x+50,y+25,
                                               fill='#333333', outline='#cccccc', width=2, tags='shape')
            elif self.current_tool == 'diamond':
                points = [x,y-30, x+50,y, x,y+30, x-50,y]
                item = self.canvas.create_polygon(points, fill='#333333', outline='#cccccc', width=2, tags='shape')
            self.shapes.append(item)
            self.update_scrollregion()
        elif self.current_tool in ['line','arrow']:
            arrow_type = 'last' if self.current_tool=='arrow' else None
            self.current_item = self.canvas.create_line(self.start_x,self.start_y,self.start_x,self.start_y,
                                                        fill='#cccccc', width=2, arrow=arrow_type)
            self.lines.append(self.current_item)
            self.update_scrollregion()
        elif self.current_tool == 'delete':
            items = self.canvas.find_overlapping(self.start_x-1,self.start_y-1,self.start_x+1,self.start_y+1)
            for item in items:
                if 'shape' in self.canvas.gettags(item) or item in self.lines or item in self.text_items.values():
                    self.canvas.delete(item)
                    if item in self.shapes: self.shapes.remove(item)
                    if item in self.lines: self.lines.remove(item)
                    if item in getattr(self,'text_items',{}).values():
                        key = [k for k,v in self.text_items.items() if v==item][0]
                        del self.text_items[key]
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
                        tid = self.canvas.create_text(tx,ty,text=text, fill='#cccccc', font=('Segoe UI',12))
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

    def on_release(self, event):
        self.current_item=None
        self.move_start=None

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

    def export_png(self):
        file_path = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[("PNG files","*.png")])
        if not file_path: return
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        img = Image.new('RGB', (width, height), color='#1e1e1e')
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("Segoe UI.ttf", 12)
        except:
            font = ImageFont.load_default()
        for shape in self.shapes:
            coords = self.canvas.coords(shape)
            shape_type = self.canvas.type(shape)
            fill = self.canvas.itemcget(shape,'fill')
            outline = self.canvas.itemcget(shape,'outline')
            w = int(float(self.canvas.itemcget(shape,'width')))
            if shape_type == 'rectangle':
                draw.rectangle(coords, fill=fill, outline=outline, width=w)
            elif shape_type == 'oval':
                draw.ellipse(coords, fill=fill, outline=outline, width=w)
            elif shape_type == 'polygon':
                draw.polygon(coords, fill=fill, outline=outline)
        for line in self.lines:
            coords = self.canvas.coords(line)
            color = self.canvas.itemcget(line,'fill')
            w = int(float(self.canvas.itemcget(line,'width')))
            draw.line(coords, fill=color, width=w)
            if self.canvas.itemcget(line,'arrow')=='last':
                x0,y0,x1,y1 = coords
                draw.polygon([(x1,y1),(x1-10,y1-5),(x1-10,y1+5)], fill=color)
        for shape, tid in self.text_items.items():
            text = self.canvas.itemcget(tid,'text')
            x, y = self.canvas.coords(tid)
            draw.text((x, y), text, font=font, fill='#cccccc', anchor='mm')
        img.save(file_path)
        print(f"Flowchart exported to {file_path}")