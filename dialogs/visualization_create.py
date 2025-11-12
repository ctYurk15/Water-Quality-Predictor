import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
from datetime import datetime
from theme import BLUE_BG, BG_MAIN, RED_BG

class CreateVisualizationDialog:
    """
    Модалка створення візуалізації:
      - вибір передбачення (Combobox)
      - вибір кольору (color picker)
    on_save -> dict: {forecast_name, color, created_at}
    """
    def __init__(self, master, on_save, *, forecast_names):
        self.master = master
        self.on_save = on_save
        self.names = forecast_names or []

        self.top = tk.Toplevel(master)
        self.top.title("Створити візуалізацію")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG); self.top.resizable(False, False)

        w, h = 420, 220
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Передбачення", bg=BLUE_BG).grid(row=0, column=0, sticky="w")
        self.cmb = ttk.Combobox(frm, values=self.names, state="readonly")
        if self.names: self.cmb.current(0)
        self.cmb.grid(row=1, column=0, sticky="ew", pady=(0,8))

        tk.Label(frm, text="Колір лінії реальних даних", bg=BLUE_BG).grid(row=2, column=0, sticky="w")
        real_data_color_row = tk.Frame(frm, bg=BLUE_BG)
        real_data_color_row.grid(row=3, column=0, sticky="w", pady=(0,8))
        self.real_data_color = "#1f77b4"
        self.real_data_preview = tk.Canvas(real_data_color_row, width=28, height=18, bg=self.real_data_color, highlightthickness=1, highlightbackground="#888")
        self.real_data_preview.pack(side="left", padx=(0,6))
        ttk.Button(real_data_color_row, text="Обрати колір…", command=self._pick_real_data_color).pack(side="left")

        tk.Label(frm, text="Колір лінії передбачення", bg=BLUE_BG).grid(row=2, column=0, sticky="w")
        forecast_color_row = tk.Frame(frm, bg=BLUE_BG)
        forecast_color_row.grid(row=4, column=0, sticky="w", pady=(0,8))
        self.forecast_color = "#BA1200"
        self.forecast_preview = tk.Canvas(forecast_color_row, width=28, height=18, bg=self.forecast_color, highlightthickness=1, highlightbackground="#888")
        self.forecast_preview.pack(side="left", padx=(0,6))
        ttk.Button(forecast_color_row, text="Обрати колір…", command=self._pick_forecast_color).pack(side="left")

        actions = tk.Frame(frm, bg=BLUE_BG)
        actions.grid(row=5, column=0, sticky="e")
        tk.Button(actions, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(actions, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

        frm.grid_columnconfigure(0, weight=1)

    def _pick_real_data_color(self):
        self._pick('real_data')

    def _pick_forecast_color(self):
        self._pick('forecast')

    def _pick(self, element):

        source = self.real_data_color if element == 'forecast' else self.forecast_color

        rgb, hx = colorchooser.askcolor(color=source, title="Колір лінії")
        if hx:
            if element == 'real_data':
                self.real_data_color = hx
                self.real_data_preview.configure(bg=hx)
            else:
                self.forecast_color = hx
                self.forecast_preview.configure(bg=hx)

    def _save(self):
        name = (self.cmb.get() or "").strip()
        if not name:
            messagebox.showwarning("Перевірка", "Оберіть передбачення.")
            return
        payload = {
            "forecast_name": name,
            "real_data_color": self.real_data_color,
            "forecast_color": self.forecast_color,
            "created_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        self.top.grab_release(); self.top.destroy()
        self.on_save(payload)
