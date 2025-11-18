import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from theme import BG_PANEL, RED_BG, PURPLE_BG, YELLOW_BG
from pathlib import Path
import shutil, threading, os

from src.forecast import Forecast
from modules.downloader import trigger_file_download

class ForecastsView(ttk.Frame):
    """
    Екран 'Передбачення'.
    - on_add_click: викликається кнопкою ＋
    - on_rows_changed: збереження після дод/видал
    """
    title = "Передбачення"

    def __init__(self, master, on_add_click, models_view, on_rows_changed=None, visualization_view=None):
        super().__init__(master, style="BaseView.TFrame")
        self.on_add_click = on_add_click
        self.on_rows_changed = on_rows_changed or (lambda: None)
        self.rows = []    # [{row, data_dict}]
        self.row_idx = 0
        self.models_view = models_view
        self.visualization_view = visualization_view

        ttk.Label(self, text=self.title, style="Head.TLabel").pack(anchor="n", pady=(18, 8))

        columns = tk.Frame(self, bg=BG_PANEL); columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, minsize=70)
        columns.grid_columnconfigure(1, weight=1)
        columns.grid_rowconfigure(0, weight=1)

        tk.Button(columns, text="＋", font=("", 16, "bold"),
                  width=3, height=1, bg=PURPLE_BG, fg="#3f3356",
                  relief="raised", bd=1, command=self.on_add_click)\
            .grid(row=0, column=0, sticky="n", padx=(18, 8), pady=(24, 0))

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
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._canvas_win_id, width=self.canvas.winfo_width()))

        tk.Frame(self.list_frame, bg=BG_PANEL, height=6).grid(row=0, column=0, sticky="ew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    # ---- API ----
    def add_row(self, data: dict):
        """
        data = {name, prob, model, forecast_from, forecast_to, created_at}
        """
        # Рядок списку: 2 колонки — [білий контейнер][кнопка ✖]
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=self.row_idx + 1, column=0, sticky="ew", pady=6, padx=(24, 24))
        row.grid_columnconfigure(0, weight=1)  # контейнер розтягується
        row.grid_columnconfigure(1, weight=0)

        # Білий контейнер-картка
        box = tk.Frame(row, bg="white", bd=1, relief="solid", padx=6, pady=4)
        box.grid(row=0, column=0, sticky="ew")

        # Вміст картки (як раніше)
        tk.Label(box, text=f"{data.get('name','')}", bg="white", anchor="w").grid(row=0, column=0, sticky="w")
        #tk.Label(box, text=f"{str(data.get('prob','')).strip()}%", bg="white", anchor="w").grid(row=1, column=0, sticky="w")

        parameter = ''
        selected_model = self.models_view.find_model_by_name(data.get("model",""))
        if selected_model != {}:
            parameter = selected_model.get('meta')['parameter']

        tk.Label(box, text=data.get("model",""), bg="white").grid(row=0, column=1, rowspan=2, padx=20)
        tk.Label(box, text=parameter, bg="white").grid(row=0, column=2, rowspan=2, padx=20)

        period = tk.Frame(box, bg="white")
        period.grid(row=0, column=3, rowspan=2, padx=20)
        tk.Label(period, text=data.get("forecast_from",""), bg="white").pack(anchor="w")
        tk.Label(period, text=data.get("forecast_to",""), bg="white").pack(anchor="w")

        accuracy = Forecast.getAccuracy(data.get('name',''))
        accuracy = round(accuracy, 2)

        tk.Label(box, text=f"{accuracy} % (acc. - {str(data.get('prob','')).strip()}%)", bg="white", anchor="w").grid(row=0, column=4, sticky="w")

        ttk.Label(row, text=data.get("created_at",""), style="Item.TLabel").grid(row=0, column=1, padx=10)

        download_btn = tk.Button(
            row, text="⤓", width=3, bg=YELLOW_BG, fg="#8a0f0f",
            bd=1, relief="raised", command=lambda r=row: self._download_data(r)
        )
        download_btn.grid(row=0, column=2, padx=(0, 6))  # прилягає справа до картки

        del_btn = tk.Button(
            row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f",
            bd=1, relief="raised", command=lambda r=row: self._remove_row(r)
        )
        del_btn.grid(row=0, column=3)

        # Зберігаємо
        self.rows.append({"row": row, "data": dict(data)})
        self.row_idx += 1
        self.on_rows_changed()


    def export_state(self):
        return [it["data"] for it in self.rows]

    def import_state(self, items):
        for it in list(self.rows):
            it["row"].destroy()
        self.rows.clear(); self.row_idx = 0
        for obj in items or []:
            self.add_row(obj)
        self.on_rows_changed()

    # ---- internals ----
    def _remove_row(self, row_widget):
        for i, it in enumerate(self.rows):
            if it["row"] is row_widget:
                it["row"].destroy(); 
                self.rows.pop(i); 
                Forecast.deleteItem(it['data'].get('name'))
                self.visualization_view.remove_forecast_row(it['data'].get('name'))
                break
        for idx, it in enumerate(self.rows, start=1):
            it["row"].grid_configure(row=idx)
        self.row_idx = len(self.rows)
        self.on_rows_changed()

    def _download_data(self, row_widget):
        for i, it in enumerate(self.rows):
            if it["row"] is row_widget:
                file_path = Forecast.getDataFilePath(it['data'].get('name'))
                trigger_file_download(file_path, self)
                break

    def find_forecast_by_name(self, search_name):
        result = {}

        for i, it in enumerate(self.rows):
            if it['data'].get("name") == search_name:
                result = it
                break

        return result
