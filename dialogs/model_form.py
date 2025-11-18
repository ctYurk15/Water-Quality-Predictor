import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG
from modules.validation_helpers import validate_date, string_is_number, string_to_bool, number_to_bool_string

data_frequencies = ['D', 'W', 'M', 'H', 'Q', 'Y']
regressor_modes = ['additive', 'multiplicative']

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
        if initial != None:
            self.initial_name = initial['name']
        else:
            self.initial_name = ''

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
        self._subheader(r, "Мінімум / максимум", col=0); r += 1
        self.min_value = tk.StringVar(value=(initial or {}).get("min_value", "0"))
        self.max_value = tk.StringVar(value=(initial or {}).get("max_value", "6"))
        ttk.Entry(self.form, textvariable=self.min_value)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.max_value)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Частоти даних
        self._subheader(r, f"Частота навчальних & вихідних даних ({','.join(data_frequencies)})", col=0, colspan=4); r += 1
        self.model_freq = tk.StringVar(value=(initial or {}).get("model_freq", "D"))
        self.result_freq = tk.StringVar(value=(initial or {}).get("result_freq", "D"))
        ttk.Entry(self.form, textvariable=self.model_freq)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.result_freq)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
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

        # Налаштування регресорів (1)
        self._subheader(r, "Вплив регресорів (0.01 -> 10)", col=0, colspan=2)
        self._subheader(r, "Масштабувати регресор? (True, False, auto)", col=2, colspan=2)
        r += 1
        self.regressor_prior_scale = tk.StringVar(value=(initial or {}).get("regressor_prior_scale", 0.5))
        self.regressor_standardize = tk.StringVar(value=(initial or {}).get("regressor_standardize", "auto"))
        regressor_standardize_val = self.regressor_standardize.get().strip()
        self.regressor_standardize.set(number_to_bool_string(regressor_standardize_val))
        ttk.Entry(self.form, textvariable=self.regressor_prior_scale)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.regressor_standardize)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Налаштування регресорів (2)
        self._subheader(r, f"Режим регресора ({','.join(regressor_modes)})", col=0, colspan=2)
        self._subheader(r, "Згладжувати регресор? (True, False)", col=2, colspan=2)
        r += 1
        self.regressor_mode = tk.StringVar(value=(initial or {}).get("regressor_mode", 'additive'))
        self.smooth_regressors = tk.StringVar(value=(initial or {}).get("smooth_regressors", '1'))
        smooth_regressors_val = self.smooth_regressors.get().strip()
        self.smooth_regressors.set(number_to_bool_string(smooth_regressors_val))
        ttk.Entry(self.form, textvariable=self.regressor_mode)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.smooth_regressors)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

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

    def _subheader(self, row, text, col=0, colspan=1):
        tk.Label(self.form, text=text, bg=BLUE_BG, font=("", 10, "bold"), anchor='w')\
            .grid(row=row, column=col, sticky="ww", padx=8, pady=(6,2),columnspan=colspan)

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
        if existing_model != {} and self.initial_name != name:
            messagebox.showwarning("Перевірка", "Така назва вже існує")
            return

        # required params
        ts = self.ts_list.get(self.ts_list.curselection()[0]) if self.ts_list.curselection() else None
        param = self.param_list.get(self.param_list.curselection()[0]) if self.param_list.curselection() else None

        train_from = self.train_from.get().strip()
        train_to = self.train_to.get().strip()

        min_value = self.min_value.get().strip()
        max_value = self.max_value.get().strip()

        result_freq = self.result_freq.get().strip()
        model_freq = self.model_freq.get().strip()

        regressor_prior_scale = self.regressor_prior_scale.get().strip()

        regressor_standardize_raw = self.regressor_standardize.get().strip()
        regressor_standardize = ''
        if regressor_standardize_raw == 'auto': regressor_standardize = 'auto'
        else: regressor_standardize = string_to_bool(regressor_standardize_raw)

        regressor_mode = self.regressor_mode.get().strip()
        smooth_regressors = string_to_bool(self.smooth_regressors.get().strip())

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
        if model_freq not in data_frequencies:
            messagebox.showwarning("Перевірка", f"Вкажіть коректну частоту навчальних даних ({','.join(data_frequencies)})")
            return
        if result_freq not in data_frequencies:
            messagebox.showwarning("Перевірка", f"Вкажіть коректну частоту вихідних даних ({','.join(data_frequencies)})")
            return
        if string_is_number(regressor_prior_scale) == False or regressor_prior_scale == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний вплив регресорів")
            return regressor_standardize
        if type(regressor_standardize) != bool and regressor_standardize != 'auto':
            messagebox.showwarning("Перевірка", "Вкажіть коректне значеня для масштабування регресорів")
            return
        if regressor_mode not in regressor_modes:
            messagebox.showwarning("Перевірка", f"Вкажіть коректний режм регресора ({','.join(regressor_modes)})")
            return
        if type(smooth_regressors) != bool:
            messagebox.showwarning("Перевірка", "Вкажіть коректне значеня для згладжуванння регресорів")
            return

        payload = dict(
            name=name,
            timeseries=ts,
            parameter=param,
            train_from=train_from,
            train_to=train_to,
            min_value=min_value,
            max_value=max_value,
            result_freq=result_freq,
            model_freq=model_freq,
            regressors=sel_regs,
            weights=weights,
            regressor_prior_scale=regressor_prior_scale,
            regressor_standardize=regressor_standardize,
            regressor_mode=regressor_mode,
            smooth_regressors=smooth_regressors,
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
