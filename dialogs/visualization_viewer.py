import tkinter as tk
from theme import BLUE_BG, BG_MAIN, RED_BG
from tkinter import filedialog, messagebox
from math import sin, pi

class VisualizationViewer:
    """
    Модалка перегляду візуалізації з Canvas та кнопкою 'Завантажити'.
    """
    def __init__(self, master, *, title, color):
        self.master = master
        self.color = color or "black"

        self.top = tk.Toplevel(master)
        self.top.title(title or "Візуалізація")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG); self.top.resizable(True, True)

        w, h = 760, 520
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=12, pady=12)
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(frm, bg="white", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12,8))

        tk.Button(frm, text="Завантажити", bg=BG_MAIN, command=self._download).grid(row=1, column=0, sticky="e", padx=12, pady=(0,12))

        self._render(title)

    def _render(self, title):
        c = self.canvas; c.delete("all")
        w = max(c.winfo_width(), 300); h = max(c.winfo_height(), 200)
        pad = 30; x0, y0, x1, y1 = pad, pad, w-pad, h-pad
        c.create_rectangle(x0, y0, x1, y1, outline="#c0c0c0")
        pts = []
        n = 40
        for i in range(n):
            t = i/(n-1)
            y = 0.5 + 0.4*sin(2*pi*t) + 0.1*sin(10*pi*t)
            xp = x0 + t*(x1-x0)
            yp = y1 - y*(y1-y0)
            pts.append((xp, yp))
        for i in range(1, len(pts)):
            c.create_line(pts[i-1][0], pts[i-1][1], pts[i][0], pts[i][1], fill=self.color, width=2)
        c.create_text(w//2, y0-12, text=title, anchor="s")

    def _download(self):
        path = filedialog.asksaveasfilename(defaultextension=".ps", filetypes=[("PostScript", "*.ps"), ("Усі файли", "*.*")])
        if not path: return
        try:
            self.canvas.postscript(file=path, colormode="color")
            messagebox.showinfo("Завантажено", path)
        except Exception as e:
            messagebox.showerror("Помилка", str(e))
