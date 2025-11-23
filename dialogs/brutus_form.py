import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG
from modules.validation_helpers import validate_date, string_is_number, string_to_bool, number_to_bool_string
from modules.brutus_generator import BrutusGenerator

data_frequencies = ['D', 'W', 'M', 'H', 'Q', 'Y']
regressor_modes = ['additive', 'multiplicative']

class BrutusDialog:
    """
    Скролювана форма підбору оптимальних параметрів для моделі.
    """
    def __init__(self, master, *,
                 timeseries_options=None,
                 parameter_options=None,
                 regressor_options=None,
                 models_view=None):
        self.master = master

        self.models_view = models_view

        self.timeseries_options = timeseries_options or []
        self.parameter_options = parameter_options or []
        self.regressor_options = regressor_options or []

        self.top = tk.Toplevel(master)
        self.top.title("Режим Brutus")
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

        self._subheader(1, "Вкажіть налаштування параметрів і межі для перебору.", col=0, colspan=4)
        self._subheader(2, "В кінці створиться одна модель з оптимальними налаштуваннями,", col=0, colspan=4)
        self._subheader(3, "що показала найкращий результат.", col=0, colspan=4)
        self._subheader(4, "", col=0, colspan=4)

        r = 5

        #----- Цільові параметри

        # Назва
        self._subheader(r, "Назва моделі", col=0, colspan=4)
        r += 1
        self.name_var = tk.StringVar(value='')
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

        # Мін/макс
        self._subheader(r, "Мінімум / максимум", col=0, colspan=2); r += 1
        self.min_value = tk.StringVar(value=0)
        self.max_value = tk.StringVar(value=6)
        ttk.Entry(self.form, textvariable=self.min_value)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.max_value)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Частоти даних
        self._subheader(r, f"Частота навчальних & вихідних даних ({','.join(data_frequencies)})", col=0, colspan=4); r += 1
        self.model_freq = tk.StringVar(value="D")
        self.result_freq = tk.StringVar(value="D")
        ttk.Entry(self.form, textvariable=self.model_freq)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.result_freq)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1
        
        # Навчання від–до
        self._subheader(r, "Цільові межі передбачення (від - до)", col=0, colspan=2); r += 1
        self.target_forecast_from = tk.StringVar(value="2006-01-01")
        self.target_forecast_to = tk.StringVar(value="2006-12-31")
        ttk.Entry(self.form, textvariable=self.target_forecast_from)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.target_forecast_to)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        #----- Параметри для перебору

        # Навчання від–до
        self._subheader(r, "Межі навчання від - до (роки)", col=0, colspan=2); r += 1
        self.train_from_year = tk.StringVar(value="2003")
        self.train_to_year = tk.StringVar(value="2005")
        ttk.Entry(self.form, textvariable=self.train_from_year)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.train_to_year)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Мін/макс вплив регресорів
        self._subheader(r, "Вплив індивідуальних регресорів (мінімум - максимум)", col=0, colspan=4); r += 1
        self.min_single_regressor_value = tk.StringVar(value=0.1)
        self.max_single_regressor_value = tk.StringVar(value=5)
        ttk.Entry(self.form, textvariable=self.min_single_regressor_value)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.max_single_regressor_value)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Налаштування регресорів (1)
        self._subheader(r, "Вплив регресорів (від - до)", col=0, colspan=2)
        r += 1
        self.regressor_prior_scale_min = tk.StringVar(value=0.5)
        self.regressor_prior_scale_max = tk.StringVar(value=10)
        ttk.Entry(self.form, textvariable=self.regressor_prior_scale_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.regressor_prior_scale_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Налаштування регресорів (2)
        self._subheader(r, "Кількість останніх точок для лінійної екстраполяції (від - до)", col=0, colspan=4)
        r += 1
        self.regressor_future_linear_window_min = tk.StringVar(value=3)
        self.regressor_future_linear_window_max = tk.StringVar(value=30)
        ttk.Entry(self.form, textvariable=self.regressor_future_linear_window_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.regressor_future_linear_window_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Other settings (1)
        self._subheader(r, "Розмір вікна згладжування (від - до)", col=0, colspan=2)
        r += 1
        self.smooth_window_min = tk.StringVar(value=3)
        self.smooth_window_max = tk.StringVar(value=30)
        ttk.Entry(self.form, textvariable=self.smooth_window_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.smooth_window_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Other settings (2)
        self._subheader(r, "Чутливість до зміни тренду (шумність) (від - до)", col=0, colspan=4)
        r += 1
        self.changepoint_prior_scale_min = tk.StringVar(value=0.01)
        self.changepoint_prior_scale_max = tk.StringVar(value=1)
        ttk.Entry(self.form, textvariable=self.changepoint_prior_scale_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.changepoint_prior_scale_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Other settings (3)
        self._subheader(r, "Сила впливу сезонності (від - до)", col=0, colspan=4)
        r += 1
        self.seasonality_prior_scale_min = tk.StringVar(value=0.01)
        self.seasonality_prior_scale_max = tk.StringVar(value=1)
        ttk.Entry(self.form, textvariable=self.seasonality_prior_scale_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.seasonality_prior_scale_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Other settings (4)
        self._subheader(r, "Множник важливості регресора (від - до)", col=0, colspan=4)
        r += 1
        self.regressor_global_importance_min = tk.StringVar(value=0.1)
        self.regressor_global_importance_max = tk.StringVar(value=5)
        ttk.Entry(self.form, textvariable=self.regressor_global_importance_min)\
            .grid(row=r, column=0, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        ttk.Entry(self.form, textvariable=self.regressor_global_importance_max)\
            .grid(row=r, column=2, columnspan=2, sticky="ew", padx=PADX, pady=(0,8))
        r += 1

        # Кнопки
        btns = tk.Frame(self.form, bg=BLUE_BG)
        btns.grid(row=r, column=0, columnspan=4, sticky="e", padx=PADX, pady=(6, 4))
        tk.Button(btns, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(btns, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

        # --- initial selections/weights ---
        #self.weights = {}

    # --- helpers -------------------------------------------------------------
    def _label(self, row, text, col=0):
        tk.Label(self.form, text=text, bg=BLUE_BG).grid(row=row, column=col, sticky="w", padx=8, pady=(0,2))

    def _subheader(self, row, text, col=0, colspan=1):
        tk.Label(self.form, text=text, bg=BLUE_BG, font=("", 10, "bold"), anchor='w')\
            .grid(row=row, column=col, sticky="ww", padx=8, pady=(6,2),columnspan=colspan)

    #def _rebuild_weights(self):
    #    for w in self.weights_frame.winfo_children(): w.destroy()
    #    self.weight_vars = {}
    #    sel_idx = self.reg_list.curselection()
    #    if not sel_idx:
    #        tk.Label(self.weights_frame, text="(не вибрано)", bg=BLUE_BG).pack(anchor="w")
    ##        return
    #    for i in sel_idx:
    #        name = self.reg_list.get(i)
    #        var = tk.StringVar(value=self.weights.get(name, "1"))
    #        self.weight_vars[name] = var
    #        row = tk.Frame(self.weights_frame, bg=BLUE_BG)
    #        row.pack(fill="x", pady=2)
    #        tk.Label(row, text=name, bg=BLUE_BG, width=14, anchor="w").pack(side="left")
    #        ttk.Entry(row, textvariable=var, width=10).pack(side="left")

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

        target_forecast_from = self.target_forecast_from.get().strip()
        target_forecast_to = self.target_forecast_to.get().strip()

        result_freq = self.result_freq.get().strip()
        model_freq = self.model_freq.get().strip()

        min_value = self.min_value.get().strip()
        max_value = self.max_value.get().strip()

        train_from_year = self.train_from_year.get().strip()
        train_to_year = self.train_to_year.get().strip()

        min_single_regressor_value = self.min_single_regressor_value.get().strip()
        max_single_regressor_value = self.max_single_regressor_value.get().strip()

        regressor_prior_scale_min = self.regressor_prior_scale_min.get().strip()
        regressor_prior_scale_max = self.regressor_prior_scale_max.get().strip()

        regressor_future_linear_window_min = self.regressor_future_linear_window_min.get().strip()
        regressor_future_linear_window_max = self.regressor_future_linear_window_max.get().strip()

        smooth_window_min = self.smooth_window_min.get().strip()
        smooth_window_max = self.smooth_window_max.get().strip()

        changepoint_prior_scale_min = self.changepoint_prior_scale_min.get().strip()
        changepoint_prior_scale_max = self.changepoint_prior_scale_max.get().strip()

        seasonality_prior_scale_min = self.seasonality_prior_scale_min.get().strip()
        seasonality_prior_scale_max = self.seasonality_prior_scale_max.get().strip()

        regressor_global_importance_min = self.regressor_global_importance_min.get().strip()
        regressor_global_importance_max = self.regressor_global_importance_max.get().strip()

        #auto-filled
        regressors = self.regressor_options
        regressor_standardize = [True, False, "auto"]
        regressor_mode = regressor_modes
        smooth_regressors = [True, False]

        ###

        # optional params
        #sel_regs = [self.reg_list.get(i) for i in self.reg_list.curselection()]
        #weights = {rg: self.weight_vars[rg].get() for rg in self.weight_vars}
        
        if ts == None:
            messagebox.showwarning("Перевірка", "Вкажіть часовий ряд")
            return
        if param == None:
            messagebox.showwarning("Перевірка", "Вкажіть назву параметра")
            return
        if validate_date(target_forecast_from) == False:
            messagebox.showwarning("Перевірка", "Вкажіть коректну цільову дату початку передбачення")
            return
        if validate_date(target_forecast_to) == False:
            messagebox.showwarning("Перевірка", "Вкажіть коректну цільову дату кінця передбачення")
            return
        if model_freq not in data_frequencies:
            messagebox.showwarning("Перевірка", f"Вкажіть коректну частоту навчальних даних ({','.join(data_frequencies)})")
            return
        if result_freq not in data_frequencies:
            messagebox.showwarning("Перевірка", f"Вкажіть коректну частоту вихідних даних ({','.join(data_frequencies)})")
            return
        if string_is_number(train_from_year) == False or train_from_year == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний початковий рік навчання")
            return
        if string_is_number(train_to_year) == False or train_to_year == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний кінцевий рік навчання")
            return
        if string_is_number(min_value) == False or min_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне мінімальне значення")
            return
        if string_is_number(max_value) == False or max_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне максимальне значення")
            return
        if string_is_number(min_single_regressor_value) == False or min_single_regressor_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне мінімальне значення впливу індивідуальних регресорів")
            return
        if string_is_number(max_single_regressor_value) == False or max_single_regressor_value == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне максимальне значення впливу індивідуальних регресорів")
            return
        if string_is_number(regressor_prior_scale_min) == False or regressor_prior_scale_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне мінімальне значення впливу регресорів")
            return
        if string_is_number(regressor_prior_scale_max) == False or regressor_prior_scale_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректне максимальне значення впливу регресорів")
            return
        if string_is_number(regressor_future_linear_window_min) == False or regressor_future_linear_window_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну мінімальну кількість останніх точок для лінійної екстраполяції")
            return
        if string_is_number(regressor_future_linear_window_max) == False or regressor_future_linear_window_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну максимальну кількість останніх точок для лінійної екстраполяції")
            return
        if string_is_number(smooth_window_min) == False or smooth_window_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний мінімальний розмір вікна згладжування")
            return
        if string_is_number(smooth_window_max) == False or smooth_window_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний максимальний розмір вікна згладжування")
            return
        if string_is_number(changepoint_prior_scale_min) == False or changepoint_prior_scale_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну мінімальну чутливість до зміни тренду")
            return
        if string_is_number(changepoint_prior_scale_max) == False or changepoint_prior_scale_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну максимальну чутливість до зміни тренду")
            return
        if string_is_number(seasonality_prior_scale_min) == False or seasonality_prior_scale_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну мінімальну cилу впливу сезонності")
            return
        if string_is_number(seasonality_prior_scale_max) == False or seasonality_prior_scale_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректну максимальну cилу впливу сезонності")
            return
        if string_is_number(regressor_global_importance_min) == False or regressor_global_importance_min == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний мінімальний множник важливості регресора")
            return
        if string_is_number(regressor_global_importance_max) == False or regressor_global_importance_max == '':
            messagebox.showwarning("Перевірка", "Вкажіть коректний максимальний множник важливості регресора")
            return

        payload = dict(
            name=name,
            timeseries=ts,
            parameter=param,
            target_forecast_from=target_forecast_from,
            target_forecast_to=target_forecast_to,
            result_freq=result_freq,
            model_freq=model_freq,
            min_value=min_value,
            max_value=max_value,
            train_from_year=train_from_year,
            train_to_year=train_to_year,
            min_single_regressor_value=min_single_regressor_value,
            max_single_regressor_value=max_single_regressor_value,
            regressor_prior_scale_min=regressor_prior_scale_min,
            regressor_prior_scale_max=regressor_prior_scale_max,
            regressor_future_linear_window_min=regressor_future_linear_window_min,
            regressor_future_linear_window_max=regressor_future_linear_window_max,
            smooth_window_min=smooth_window_min,
            smooth_window_max=smooth_window_max,
            changepoint_prior_scale_min=changepoint_prior_scale_min,
            changepoint_prior_scale_max=changepoint_prior_scale_max,
            seasonality_prior_scale_min=seasonality_prior_scale_min,
            seasonality_prior_scale_max=seasonality_prior_scale_max,
            regressor_global_importance_min=regressor_global_importance_min,
            regressor_global_importance_max=regressor_global_importance_max,
            
            regressors=regressors,
            regressor_standardize=regressor_standardize,
            regressor_mode=regressor_mode,
            smooth_regressors=smooth_regressors,

            #created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        )

        self.top.grab_release()
        self.top.destroy()
        
        self.start_process(payload)

    def start_process(self, payload):
        #print(payload)

        generator = BrutusGenerator(self.master, payload)
        generator.start()

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
