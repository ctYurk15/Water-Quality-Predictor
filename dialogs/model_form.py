import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG
from modules.validation_helpers import validate_date, string_is_number

class AddOrEditModelDialog:
    """
    Скролювана форма моделі.
    on_save(payload: dict) викликається при збереженні.
    Може приймати initial: dict для попереднього заповнення.
    """
    def __init__(self, master, on_save, *,
                 timeseries_options=None,
                 parameter_options=None,
                 regressor_options=None,
                 initial=None,
                 models_view=None):
        self.master = master
        self.on_save = on_save

        self.models_view = models_view

        self.timeseries_options = timeseries_options or []
        self.parameter_options = parameter_options or []
        self.regressor_options = regressor_options or []

        self.top = tk.Toplevel(master)
        self.top.title("Нова модель" if not initial else "Редагувати модель")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(True, True)

        # стартовий розмір і центр
        self.top.update_idletasks()
        w, h = 640, 560
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        # --- Скрол-контейнер ---
        outer = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        self.canvas = tk.Canvas(outer, bg=BLUE_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.form = tk.Frame(self.canvas, bg=BLUE_BG)
        self._win_id = self.canvas.create_window((0, 0), window=self.form, anchor="nw")
        self.form.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win_id, width=self.canvas.winfo_width()))

        # ---- Сітка форми (4 колонки: 2 зліва + 2 справа) ----
        for c in range(4):
            self.form.grid_columnconfigure(c, weight=1, uniform="cols")
        PADX = 8
        r = 0

        # Назва
        self._label(r, "…Назва моделі…"); r += 1
        self.name_var = tk.StringVar(value=(initial or {}).get("name",""))
        ttk.Entry(self.form, textvariable=self.name_var)\
            .grid(row=r, column=0, columnspan=4, sticky="ew", padx=PADX, pady=(0,8)); r += 1

        # Заголовки ліво/право
        self._subheader(r, "Часовий ряд", col=0)
        self._subheader(r, "Параметр", col=2); r += 1

        # Часовий ряд (listbox single)
        self.ts_list = self._make_scroll_list(self.form, row=r, column=0, columnspan=2, height=6, padx=PADX, pady=(0,8))
        for item in self.timeseries_options:
            self.ts_list.insert("end", item)

        # Параметр (listbox single)
        self.param_list = self._make_scroll_list(self.form, row=r, column=2, columnspan=2, height=6, padx=PADX, pady=(0,8))
        for p in self.parameter_options: 
            self.param_list.insert("end", p)
        self.param_list.selection_set(0)
        r += 1

        # Навчання від–до
        self._subheader(r, "Навчання від - до", col=0); r += 1
        self.train_from = tk.StringVar(value=(initial or {}).get("train_from", "2003-01-01"))
        self.train_to   = tk.StringVar(value=(initial or {}).get("train_to",   "2005-12-31"))
        ttk.Entry(self.form, textvariable=self.train_from)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.train_to)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Мін/макс
        self._subheader(r, "Мінімум / максимум", col=2); r += 1
        self.min_value = tk.StringVar(value=(initial or {}).get("min_value", "0"))
        self.max_value = tk.StringVar(value=(initial or {}).get("max_value", "6"))
        ttk.Entry(self.form, textvariable=self.min_value)\
            .grid(row=r, column=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.max_value)\
            .grid(row=r, column=3, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Регресори + ваги
        self._subheader(r, "Регресори", col=0)
        self._subheader(r, "Вага регресорів", col=2); r += 1

        self.reg_list = self._make_scroll_list(self.form, row=r, column=0, columnspan=2, height=6, padx=PADX, pady=(0,8))
        self.reg_list.config(selectmode="multiple")
        for rg in self.regressor_options: 
            self.reg_list.insert("end", rg)

        self.weights_frame = tk.Frame(self.form, bg=BLUE_BG)
        self.weights_frame.grid(row=r, column=2, columnspan=2, sticky="nsew", padx=PADX, pady=(0,8))
        r += 1

        self.reg_list.bind("<<ListboxSelect>>", lambda e: self._rebuild_weights())

        # Кнопки
        btns = tk.Frame(self.form, bg=BLUE_BG)
        btns.grid(row=r, column=0, columnspan=4, sticky="e", padx=PADX, pady=(6, 4))
        tk.Button(btns, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(btns, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

        # --- initial selections/weights ---
        self.weights = {}
        if initial:
            # timeseries
            if initial.get("timeseries") in self.timeseries_options:
                self.ts_list.selection_clear(0, "end")
                self.ts_list.selection_set(self.timeseries_options.index(initial["timeseries"]))
                self.ts_list.see(self.timeseries_options.index(initial["timeseries"]))
            # parameter
            if initial.get("parameter") in self.parameter_options:
                self.param_list.selection_clear(0, "end")
                self.param_list.selection_set(self.parameter_options.index(initial["parameter"]))
                self.param_list.see(self.parameter_options.index(initial["parameter"]))
            # regressors + weights
            regs = initial.get("regressors") or []
            idxs = [self.regressor_options.index(r) for r in regs if r in self.regressor_options]
            for i in idxs: self.reg_list.selection_set(i)
            self.weights = {k: str(v) for k, v in (initial.get("weights") or {}).items()}
        self._rebuild_weights()

    # --- helpers -------------------------------------------------------------
    def _label(self, row, text, col=0):
        tk.Label(self.form, text=text, bg=BLUE_BG).grid(row=row, column=col, sticky="w", padx=8, pady=(0,2))

    def _subheader(self, row, text, col=0):
        tk.Label(self.form, text=text, bg=BLUE_BG, font=("", 10, "bold"))\
            .grid(row=row, column=col, sticky="w", padx=8, pady=(6,2))

    def _rebuild_weights(self):
        for w in self.weights_frame.winfo_children(): w.destroy()
        self.weight_vars = {}
        sel_idx = self.reg_list.curselection()
        if not sel_idx:
            tk.Label(self.weights_frame, text="(не вибрано)", bg=BLUE_BG).pack(anchor="w")
            return
        for i in sel_idx:
            name = self.reg_list.get(i)
            var = tk.StringVar(value=self.weights.get(name, "1"))
            self.weight_vars[name] = var
            row = tk.Frame(self.weights_frame, bg=BLUE_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=name, bg=BLUE_BG, width=14, anchor="w").pack(side="left")
            ttk.Entry(row, textvariable=var, width=10).pack(side="left")

    # --- save ----------------------------------------------------------------
    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Перевірка", "Вкажіть назву моделі.")
            return
        existing_model = self.models_view.find_model_by_name(name)
        if existing_model != {}:
            messagebox.showwarning("Перевірка", "Така назва вже існує")
            return

        # required params
        ts = self.ts_list.get(self.ts_list.curselection()[0]) if self.ts_list.curselection() else None
        param = self.param_list.get(self.param_list.curselection()[0]) if self.param_list.curselection() else None
        train_from = self.train_from.get().strip()
        train_to = self.train_to.get().strip()
        min_value = self.min_value.get().strip()
        max_value = self.max_value.get().strip()

        # optional params
        sel_regs = [self.reg_list.get(i) for i in self.reg_list.curselection()]
        weights = {rg: self.weight_vars[rg].get() for rg in self.weight_vars}
        
        if ts == None:
            messagebox.showwarning("Перевірка", "Вкажіть часовий ряд")
            return
        if param == None:
            messagebox.showwarning("Перевірка", "Вкажіть назву параметра")
            return
        if validate_date(train_from) == False:
            messagebox.showwarning("Перевірка", "Вкажіть коректну дату початку навчання")
            return
        if validate_date(train_to) == False:
            messagebox.showwarning("Перевірка", "Вкажіть коректну дату кінця навчання")
            return
        if string_is_number(min_value) == False or min_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне мінімальне значення")
            return
        if string_is_number(max_value) == False or max_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне максимальне значення")
            return

        payload = dict(
            name=name,
            timeseries=ts,
            parameter=param,
            train_from=train_from,
            train_to=train_to,
            min_value=min_value,
            max_value=max_value,
            regressors=sel_regs,
            weights=weights,
            created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        )
        self.top.grab_release(); self.top.destroy()
        self.on_save(payload)

    def _make_scroll_list(self, parent, *, row, column, columnspan=2, height=6, padx=8, pady=(0,8)):
        """Створює Listbox із вертикальним Scrollbar у фіксованій висоті."""
        wrap = tk.Frame(parent, bg=BLUE_BG)
        wrap.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=padx, pady=pady)

        lb = tk.Listbox(wrap, height=height, exportselection=False)
        lb.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(wrap, orient="vertical", command=lb.yview)
        sb.pack(side="right", fill="y")

        lb.configure(yscrollcommand=sb.set)
        return lb
