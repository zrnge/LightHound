import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zipfile
import json
import math
import random
from collections import deque

class LiteHoundApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LiteHound - Lightweight AD Attack Path Explorer")
        self.root.geometry("1400x900")

        # --- State ---
        self.nodes = {}  # {name: {type: str, x: f, y: f, is_admin: bool, raw_data: dict}}
        self.edges = []  # [{from: name, to: name, label: str}]
        self.selected_node = None
        self.drag_data = {"x": 0, "y": 0}
        self.zoom_level = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.highlighted_path = []

        self.setup_ui()
        
        # Bindings
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Cross-platform zoom support
        self.canvas.bind("<MouseWheel>", self.on_zoom)     # Windows / macOS
        self.canvas.bind("<Button-4>", self.on_zoom)      # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_zoom)      # Linux scroll down
        
        # Panning bindings with "hand" cursor
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-3>", self.stop_pan)
        
        self.canvas.bind("<Motion>", self.on_hover)

    def setup_ui(self):
        # Top Toolbar
        toolbar = tk.Frame(self.root, bg="#f8f9fa", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="📁 Load ZIP", command=self.load_zip).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ Clear", command=self.clear_graph).pack(side=tk.LEFT, padx=5)
        
        tk.Label(toolbar, text="🔍 Start Node:", bg="#f8f9fa").pack(side=tk.LEFT, padx=(20, 5))
        self.search_var = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.search_var, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Find Path to Admin", command=self.find_path_to_admin).pack(side=tk.LEFT, padx=5)

        # Legend
        legend = tk.Frame(toolbar, bg="#f8f9fa")
        legend.pack(side=tk.RIGHT, padx=10)
        types = [("User", "#3498db"), ("Group", "#2ecc71"), ("Computer", "#e67e22"), ("High Value", "#f1c40f")]
        for name, color in types:
            tk.Label(legend, text=name, fg=color, bg="#f8f9fa", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        # Main Layout Split (Graph and Detail Panel) using PanedWindow for resizability
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#2c3e50", sashwidth=6, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Graph Area
        self.canvas = tk.Canvas(self.paned_window, bg="#2c3e50", highlightthickness=0)
        self.paned_window.add(self.canvas, stretch="always")

        # Detail Panel
        self.detail_panel = tk.Frame(self.paned_window, bg="#ecf0f1", width=400)
        self.paned_window.add(self.detail_panel, stretch="never")

        tk.Label(self.detail_panel, text="Object Details", font=("Arial", 14, "bold"), bg="#ecf0f1", pady=10).pack()
        
        self.detail_text = tk.Text(self.detail_panel, wrap=tk.WORD, bg="white", font=("Courier New", 10), state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status Bar with GitHub Link
        footer_frame = tk.Frame(self.root, bg="#34495e")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready. Load a SharpHound ZIP to begin.")
        status_bar = tk.Label(footer_frame, textvariable=self.status_var, bd=1, relief=tk.FLAT, anchor=tk.W, bg="#34495e", fg="white", font=("Arial", 9))
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        github_lbl = tk.Label(footer_frame, text="github.com/zrnge", bg="#34495e", fg="#3498db", font=("Arial", 9, "bold"), cursor="hand2")
        github_lbl.pack(side=tk.RIGHT, padx=10)

    def update_detail_panel(self, node_name):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        
        if node_name in self.nodes:
            data = self.nodes[node_name].get("raw_data", {})
            pretty_json = json.dumps(data, indent=4)
            self.detail_text.insert(tk.END, f"NAME: {node_name}\n")
            self.detail_text.insert(tk.END, "="*30 + "\n")
            self.detail_text.insert(tk.END, pretty_json)
        
        self.detail_text.config(state=tk.DISABLED)

    def add_node(self, name, n_type, raw_data=None):
        name = name.upper()
        if name not in self.nodes:
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(100, 450)
            self.nodes[name] = {
                "type": n_type, 
                "x": 600 + dist * math.cos(angle), 
                "y": 400 + dist * math.sin(angle),
                "is_admin": "DOMAIN ADMINS" in name,
                "raw_data": raw_data or {}
            }
        elif raw_data:
            self.nodes[name]["raw_data"].update(raw_data)

    def add_edge(self, u, v, label):
        u, v = u.upper(), v.upper()
        if not any(e['from'] == u and e['to'] == v and e['label'] == label for e in self.edges):
            self.edges.append({"from": u, "to": v, "label": label})

    def redraw(self):
        self.canvas.delete("all")
        r = 15 * self.zoom_level
        
        # Edges & Labels
        for edge in self.edges:
            if edge['from'] not in self.nodes or edge['to'] not in self.nodes: continue
            u, v = self.nodes[edge['from']], self.nodes[edge['to']]
            x1, y1 = (u['x'] * self.zoom_level) + self.offset_x, (u['y'] * self.zoom_level) + self.offset_y
            x2, y2 = (v['x'] * self.zoom_level) + self.offset_x, (v['y'] * self.zoom_level) + self.offset_y
            
            is_path = any(self.highlighted_path[i] == edge['from'] and self.highlighted_path[i+1] == edge['to'] 
                          for i in range(len(self.highlighted_path)-1))
            
            color = "#e74c3c" if is_path else "#95a5a6"
            width = 3 if is_path else 1
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, arrow=tk.LAST)
            
            if self.zoom_level > 0.6:
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                self.canvas.create_text(mid_x, mid_y, text=edge['label'], fill="white", font=("Arial", int(7*self.zoom_level)))

        # Nodes
        for name, data in self.nodes.items():
            x, y = (data['x'] * self.zoom_level) + self.offset_x, (data['y'] * self.zoom_level) + self.offset_y
            color = "#f1c40f" if data['is_admin'] else \
                    "#3498db" if data['type'] == "User" else \
                    "#2ecc71" if data['type'] == "Group" else "#e67e22"
            
            if name in self.highlighted_path:
                self.canvas.create_oval(x-r-6, y-r-6, x+r+6, y+r+6, outline="#f1c40f", width=3)
            
            node_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=color, outline="white", width=2, tags=("node", name))
            self.canvas.create_text(x, y+r+12, text=name.split('@')[0], fill="white", font=("Arial", int(9*self.zoom_level), "bold"))

    def find_path_to_admin(self):
        start = self.search_var.get().upper()
        admin_node = next((n for n in self.nodes if "DOMAIN ADMINS" in n), None)
        if not admin_node or start not in self.nodes: 
            messagebox.showinfo("Error", "Check start node name and ensure Domain Admins exists.")
            return
        
        queue = deque([[start]])
        visited = {start}
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == admin_node:
                self.highlighted_path = path
                self.status_var.set(f"ATTACK PATH FOUND")
                self.redraw(); return
            for e in self.edges:
                if e['from'] == curr and e['to'] not in visited:
                    visited.add(e['to'])
                    queue.append(path + [e['to']])
        messagebox.showinfo("No Path", "No path found.")

    def load_zip(self):
        path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if not path: return
        try:
            with zipfile.ZipFile(path, 'r') as z:
                for f_name in z.namelist():
                    if not f_name.endswith('.json'): continue
                    with z.open(f_name) as f:
                        data = json.load(f).get("data", [])
                        for item in data:
                            props = item.get("Properties", {})
                            name = (props.get("name") or item.get("ObjectIdentifier", "")).upper()
                            if not name: continue
                            otype = "User" if "user" in f_name.lower() else "Group" if "group" in f_name.lower() else "Computer"
                            
                            self.add_node(name, otype, raw_data=item)
                            
                            for m in item.get("Members", []):
                                m_id = m.get("ObjectIdentifier", "").upper()
                                self.add_node(m_id, "User")
                                self.add_edge(m_id, name, "MemberOf")
                            
                            for ace in item.get("Aces", []):
                                p_name = ace.get("PrincipalName", "").upper()
                                right = ace.get("RightName", "")
                                if p_name and right:
                                    self.add_node(p_name, ace.get("PrincipalType", "User"))
                                    self.add_edge(p_name, name, right)
            self.redraw()
            self.status_var.set(f"Loaded {len(self.nodes)} objects.")
        except Exception as e: messagebox.showerror("Error", str(e))

    # Handlers
    def on_press(self, event):
        item = self.canvas.find_closest(event.x, event.y)
        tags = self.canvas.gettags(item)
        if "node" in tags:
            self.selected_node = tags[1]
            self.drag_data.update({"x": event.x, "y": event.y})
            self.search_var.set(self.selected_node)
            self.update_detail_panel(self.selected_node)

    def on_drag(self, event):
        if self.selected_node:
            dx, dy = (event.x - self.drag_data["x"])/self.zoom_level, (event.y - self.drag_data["y"])/self.zoom_level
            self.nodes[self.selected_node]['x'] += dx
            self.nodes[self.selected_node]['y'] += dy
            self.drag_data.update({"x": event.x, "y": event.y}); self.redraw()

    def on_release(self, _): 
        self.selected_node = None

    def start_pan(self, event):
        self.canvas.config(cursor="fleur")
        self.drag_data.update({"x": event.x, "y": event.y})

    def do_pan(self, event):
        self.offset_x += event.x - self.drag_data["x"]
        self.offset_y += event.y - self.drag_data["y"]
        self.drag_data.update({"x": event.x, "y": event.y})
        self.redraw()

    def stop_pan(self, _):
        self.canvas.config(cursor="")

    def on_zoom(self, event):
        # Handle Linux Button-4 (Up) and Button-5 (Down)
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.zoom_level *= 1.1
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.zoom_level *= 0.9
        
        self.redraw()

    def on_hover(self, event):
        item = self.canvas.find_closest(event.x, event.y); tags = self.canvas.gettags(item)
        if "node" in tags: 
            self.status_var.set(f"Object: {tags[1]} | Click to view full JSON properties.")

    def clear_graph(self):
        self.nodes, self.edges, self.highlighted_path = {}, [], []; self.redraw()

if __name__ == "__main__":
    root = tk.Tk(); app = LiteHoundApp(root); root.mainloop()
