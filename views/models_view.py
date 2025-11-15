import tkinter as tk
from tkinter import ttk
from theme import BG_PANEL, RED_BG, PURPLE_BG, YELLOW_BG

class ModelsView(ttk.Frame):
    """
    Екран 'Моделі'.
    - on_add_click: відкрити форму додавання
    - on_edit_click(view, row_widget): відкрити форму редагування
    - on_rows_changed: викликається після дод/видал/редаг назви
    """
    title = "Моделі"

    def __init__(self, master, on_add_click, on_edit_click, on_rows_changed=None):
        super().__init__(master, style="BaseView.TFrame")
        self.on_add_click = on_add_click
        self.on_edit_click = on_edit_click
        self.on_rows_changed = on_rows_changed or (lambda: None)
        self.rows = []   # [{row, name_var, meta}]
        self.row_idx = 0

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
    def add_row(self, name, meta=None):
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=self.row_idx + 1, column=0, sticky="ew", pady=6, padx=(24, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Білий контейнер
        box = tk.Frame(row, bg="white", bd=1, relief="solid")
        name_lbl = tk.Label(box, text=name, bg="white", anchor="w")
        name_lbl.pack(fill="x", padx=4, pady=2)
        box.grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ttk.Label(row, text=meta.get("created_at",""),
                style="Item.TLabel").grid(row=0, column=1, padx=10)

        tk.Button(row, text="✎", width=3, bg=YELLOW_BG, fg="#6b4b00",
                bd=1, relief="raised", command=lambda r=row: self.on_edit_click(self, r)).grid(row=0, column=2, padx=(0,6))
        tk.Button(row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f",
                bd=1, relief="raised", command=lambda r=row: self._remove_row(r)).grid(row=0, column=3)

        self.rows.append({"row": row, "name": name, "name_label": name_lbl, "meta": dict(meta or {})})
        self.row_idx += 1
        self.on_rows_changed()

    def get_row_data(self, row_widget):
        """Повертає (name:str, meta:dict) для конкретного рядка.
        Підтримує як новий формат (name), так і старий (name_var)."""
        for it in self.rows:
            if it["row"] is row_widget:
                # новий формат
                if "name" in it and it["name"] is not None:
                    name = it["name"]
                # сумісність зі старим
                elif "name_var" in it and it["name_var"] is not None:
                    try:
                        name = it["name_var"].get()
                    except Exception:
                        name = ""
                else:
                    name = ""
                return name, dict(it.get("meta", {}))
        return "", {}

    def set_row_data(self, row_widget, *, name=None, meta=None):
        for it in self.rows:
            if it["row"] is row_widget:
                if name is not None:
                    # новий формат
                    if "name" in it:
                        it["name"] = name
                        # якщо зберігали посилання на Label із назвою — оновимо текст
                        if it.get("name_label"):
                            it["name_label"].config(text=name)
                    # сумісність: старий формат
                    if it.get("name_var") is not None:
                        try:
                            it["name_var"].set(name)
                        except Exception:
                            pass
                if meta is not None:
                    it["meta"] = dict(meta)
                self.on_rows_changed()
                break

    def export_state(self):
        return [{"name": it.get("name") or (it.get("name_var").get() if it.get("name_var") else ""),
                "meta": it.get("meta", {})}
                for it in self.rows]

    def import_state(self, items):
        for it in list(self.rows):
            it["row"].destroy()
        self.rows.clear()
        self.row_idx = 0
        for obj in items or []:
            self.add_row(obj.get("name",""), meta=obj.get("meta", {}))
        self.on_rows_changed()

    def find_model_by_name(self, search_name):
        result = {}

        for it in list(self.rows):
            if it.get("name") == search_name:
                result = it
                break

        return result


    # ---- internals ----
    def _remove_row(self, row_widget):
        for i, it in enumerate(self.rows):
            if it["row"] is row_widget:
                it["row"].destroy()
                self.rows.pop(i)
                break
        for idx, it in enumerate(self.rows, start=1):
            it["row"].grid_configure(row=idx)
        self.row_idx = len(self.rows)
        self.on_rows_changed()

    def get_names(self):
        return [it.get("name") or (it.get("name_var").get() if it.get("name_var") else "") for it in self.rows]

