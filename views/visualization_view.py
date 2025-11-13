import tkinter as tk
from tkinter import ttk
from theme import BG_PANEL, PURPLE_BG, RED_BG

from src.forecast import Forecast

class VisualizationsView(ttk.Frame):
    """
    Екран 'Візуалізація' як список карток.
    - on_add_click(): відкрити модалку створення
    - on_view_click(viz: dict): відкрити перегляд
    - on_rows_changed(): викликається після дод/видал
    """
    title = "Візуалізація"

    def __init__(self, master, on_add_click, on_view_click, on_rows_changed=None):
        super().__init__(master, style="BaseView.TFrame")
        self.on_add_click = on_add_click
        self.on_view_click = on_view_click
        self.on_rows_changed = on_rows_changed or (lambda: None)
        self.rows = []   # [{row, data}]; data: {forecast_name, color, created_at}

        ttk.Label(self, text=self.title, style="Head.TLabel").pack(anchor="n", pady=(18, 8))

        root = tk.Frame(self, bg=BG_PANEL); root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, minsize=70)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # '+'
        tk.Button(root, text="＋", font=("", 16, "bold"), width=3, height=1,
                  bg=PURPLE_BG, fg="#3f3356", relief="raised", bd=1,
                  command=self.on_add_click).grid(row=0, column=0, sticky="n", padx=(18,8), pady=(24,0))

        # список
        list_container = tk.Frame(root, bg=BG_PANEL)
        list_container.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=(8, 24))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(list_container, bg=BG_PANEL, highlightthickness=0)
        self.vsb = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.list_frame = ttk.Frame(self.canvas, style="List.TFrame")
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win_id = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw", width=1)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win_id, width=self.canvas.winfo_width()))
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")

        tk.Frame(self.list_frame, bg=BG_PANEL, height=6).grid(row=0, column=0, sticky="ew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    # ---- API ----
    def add_row(self, viz: dict):
        """
        viz = {forecast_name:str, color:str('#RRGGBB'), created_at:str}
        """
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=len(self.rows) + 1, column=0, sticky="ew", pady=6, padx=(24, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(0, weight=1)  # картка тягнеться

        # біла картка
        card = tk.Frame(row, bg="white", bd=1, relief="solid", padx=6, pady=4)
        card.grid(row=0, column=0, sticky="ew")

        # контент картки: назва, зразок кольору, дата
        left = tk.Frame(card, bg="white"); left.grid(row=0, column=0, sticky="w")
        tk.Label(left, text=viz.get("forecast_name",""), bg="white", anchor="w").pack(anchor="w")

        tk.Label(card, text="         Моніторинг:", bg="white", anchor="w").grid(row=0, column=1)
        real_data_swatch = tk.Canvas(card, width=20, height=14, bg=viz.get("real_data_color") or "#1f77b4",
                           highlightthickness=1, highlightbackground="#999")
        real_data_swatch.grid(row=0, column=2, padx=12)

        tk.Label(card, text="Передбачення:", bg="white", anchor="w").grid(row=0, column=3)
        forecast_swatch = tk.Canvas(card, width=20, height=14, bg=viz.get("forecast_color") or "#BA1200",
                           highlightthickness=1, highlightbackground="#999")
        forecast_swatch.grid(row=0, column=4, padx=12)

        ttk.Label(row, text=viz.get("created_at",""), style="Item.TLabel").grid(row=0, column=1, padx=12)

        tk.Button(row, text="👁", width=3, bg="#FFE6CC", bd=1, relief="raised",
                  command=lambda d=viz: self.on_view_click(d)).grid(row=0, column=2, padx=(8,6))
        tk.Button(row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f", bd=1, relief="raised",
                  command=lambda r=row: self._remove_row(r)).grid(row=0, column=3)

        self.rows.append({"row": row, "data": dict(viz)})
        self.on_rows_changed()

    def export_state(self):
        return [it["data"] for it in self.rows]

    def import_state(self, items):
        for it in list(self.rows):
            it["row"].destroy()
        self.rows.clear()
        for obj in items or []:
            self.add_row(obj)

    # ---- internals ----
    def _remove_row(self, row_widget):
        for i, it in enumerate(self.rows):
            if it["row"] is row_widget:
                Forecast.clearImages(it['data']['forecast_name'])
                it["row"].destroy()
                self.rows.pop(i)
                break
        for idx, it in enumerate(self.rows, start=1):
            it["row"].grid_configure(row=idx)
        self.on_rows_changed()
