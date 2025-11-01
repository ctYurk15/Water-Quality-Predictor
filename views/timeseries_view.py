import tkinter as tk
from tkinter import ttk
from datetime import datetime
from theme import BG_PANEL, RED_BG, PURPLE_BG

class TimeseriesView(ttk.Frame):
    """Екран 'Часові ряди' зі списком і кнопкою '+' у лівому жолобі."""
    title = "Часові ряди"

    def __init__(self, master, on_add_click, on_delete_row=None):
        super().__init__(master, style="BaseView.TFrame")

        self.on_add_click = on_add_click
        self.on_delete_row = on_delete_row

        head = ttk.Label(self, text=self.title, style="Head.TLabel")
        head.pack(anchor="n", pady=(18, 8))

        columns = tk.Frame(self, bg=BG_PANEL)
        columns.pack(fill="both", expand=True)

        columns.grid_columnconfigure(0, minsize=70)
        columns.grid_columnconfigure(1, weight=1)
        columns.grid_rowconfigure(0, weight=1)

        # кнопка +
        tk.Button(columns, text="＋", font=("", 16, "bold"),
                  width=3, height=1, bg=PURPLE_BG, fg="#3f3356",
                  relief="raised", bd=1, command=self.on_add_click)\
          .grid(row=0, column=0, sticky="n", padx=(18, 8), pady=(24, 0))

        # прокручуваний список
        list_container = tk.Frame(columns, bg=BG_PANEL)
        list_container.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=(8, 24))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(list_container, bg=BG_PANEL, highlightthickness=0)
        self.vsb = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.list_frame = ttk.Frame(self.canvas, style="List.TFrame")
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._canvas_win_id = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw", width=1)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.canvas.bind("<Configure>", lambda e: self._update_canvas_width())

        self.row_idx = 0
        self.rows = []  # (frame, name_var, files)

        # верхній відступ
        tk.Frame(self.list_frame, bg=BG_PANEL, height=6).grid(row=0, column=0, sticky="ew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    # --- API ---
    def add_row(self, name, files=None):
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=self.row_idx + 1, column=0, sticky="ew", pady=8, padx=(24, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)

        name_var = tk.StringVar(value=name)
        ttk.Entry(row, textvariable=name_var, width=60).grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ttk.Label(row, text=self._timestamp(), style="Item.TLabel").grid(row=0, column=1, padx=10)

        tk.Button(row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f",
                  bd=1, relief="raised", command=lambda r=row: self._remove_row(r)).grid(row=0, column=2)

        self.rows.append((row, name_var, files or []))
        self.row_idx += 1
        self._update_canvas_width()

    # --- Internals ---
    def _timestamp(self):
        return datetime.now().strftime("%d.%m.%Y %H:%M")

    def _remove_row(self, row_widget):
        for i, (frm, *_rest) in enumerate(self.rows):
            if frm == row_widget:
                frm.destroy()
                self.rows.pop(i)
                break
        for idx, (frm, *_rest) in enumerate(self.rows, start=1):
            frm.grid_configure(row=idx)
        self.row_idx = len(self.rows)
        self._update_canvas_width()

    def _update_canvas_width(self):
        self.canvas.itemconfigure(self._canvas_win_id, width=self.canvas.winfo_width())
