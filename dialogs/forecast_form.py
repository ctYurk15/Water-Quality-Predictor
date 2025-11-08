import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG

class AddForecastDialog:
    """
    Проста форма створення передбачення:
    - Назва
    - Модель (із переданого списку)
    - Параметр
    - Період від–до
    - Ймовірність/точність у %
    """
    def __init__(self, master, on_save, *, model_names=None, parameter_options=None):
        self.master = master
        self.on_save = on_save
        self.model_names = model_names or []
        self.parameter_options = parameter_options or []

        self.top = tk.Toplevel(master)
        self.top.title("Нове передбачення")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(False, False)

        w, h = 520, 300
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        PAD = 8

        tk.Label(frm, text="…Назва передбачення…", bg=BLUE_BG).grid(row=0, column=0, sticky="w", padx=PAD)
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var).grid(row=1, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(0,8))

        tk.Label(frm, text="Модель", bg=BLUE_BG).grid(row=2, column=0, sticky="w", padx=PAD)
        self.model_cmb = ttk.Combobox(frm, values=self.model_names, state="readonly")
        if self.model_names: self.model_cmb.current(0)
        self.model_cmb.grid(row=3, column=0, sticky="ew", padx=PAD, pady=(0,8))

        #tk.Label(frm, text="Параметр", bg=BLUE_BG).grid(row=2, column=1, sticky="w", padx=PAD)
        #self.param_cmb = ttk.Combobox(frm, values=self.parameter_options, state="readonly")
        #self.param_cmb.current(0)
        #self.param_cmb.grid(row=3, column=1, sticky="ew", padx=PAD, pady=(0,8))

        tk.Label(frm, text="Період від – до", bg=BLUE_BG).grid(row=4, column=0, sticky="w", padx=PAD, pady=(4,0))
        self.from_var = tk.StringVar(value="2019-01-01")
        self.to_var   = tk.StringVar(value="2019-12-31")
        ttk.Entry(frm, textvariable=self.from_var).grid(row=5, column=0, sticky="ew", padx=PAD)
        ttk.Entry(frm, textvariable=self.to_var).grid(row=5, column=1, sticky="ew", padx=PAD)

        tk.Label(frm, text="Ймовірність/точність, %", bg=BLUE_BG).grid(row=6, column=0, sticky="w", padx=PAD, pady=(6,0))
        self.prob_var = tk.StringVar(value="20")
        ttk.Entry(frm, textvariable=self.prob_var, width=10).grid(row=7, column=0, sticky="w", padx=PAD)

        btns = tk.Frame(frm, bg=BLUE_BG)
        btns.grid(row=8, column=0, columnspan=2, sticky="e", padx=PAD, pady=(10,0))
        tk.Button(btns, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(btns, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

        frm.grid_columnconfigure(0, weight=1)
        frm.grid_columnconfigure(1, weight=1)

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Перевірка", "Вкажіть назву передбачення.")
            return
        data = dict(
            name=name,
            model=self.model_cmb.get().strip(),
            #parameter=self.param_cmb.get().strip(),
            forecast_from=self.from_var.get().strip(),
            forecast_to=self.to_var.get().strip(),
            prob=self.prob_var.get().strip(),
            created_at=datetime.now().strftime("%d.%m.%Y %H:%M"),
        )
        self.top.grab_release(); self.top.destroy()
        self.on_save(data)
