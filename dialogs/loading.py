import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG

class LoadingWindow:
    """
    Модалка завантаження:
        loading_text - текст, що показувати під час завантаження
    """
    def __init__(self, master, loading_text):
        self.master = master
        #self.on_save = on_save
        #self.names = forecast_names or []

        self.top = tk.Toplevel(master)
        self.top.title("Загрузка...")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG); self.top.resizable(False, False)

        w, h = 250, 70
        #self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        #frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        #frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(self.top, text=loading_text, bg=BLUE_BG).grid(row=0, column=0, sticky="w")
        #self.cmb = ttk.Combobox(frm, values=self.names, state="readonly")
        #if self.names: self.cmb.current(0)
        #self.cmb.grid(row=1, column=0, sticky="ew", pady=(0,8))

        #tk.Label(frm, text="Колір лінії", bg=BLUE_BG).grid(row=2, column=0, sticky="w")
        #color_row = tk.Frame(frm, bg=BLUE_BG)
        #color_row.grid(row=3, column=0, sticky="w", pady=(0,8))
        #self.color = "#1f77b4"
        #self.preview = tk.Canvas(color_row, width=28, height=18, bg=self.color, highlightthickness=1, highlightbackground="#888")
        #self.preview.pack(side="left", padx=(0,6))
        #ttk.Button(color_row, text="Обрати колір…", command=self._pick).pack(side="left")

        #actions = tk.Frame(frm, bg=BLUE_BG)
        #actions.grid(row=4, column=0, sticky="e")
        #tk.Button(actions, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        #tk.Button(actions, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

        #frm.grid_columnconfigure(0, weight=1)
