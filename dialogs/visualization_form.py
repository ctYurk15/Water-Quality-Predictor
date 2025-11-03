import tkinter as tk
from tkinter import ttk, messagebox
from theme import BLUE_BG, BG_MAIN, RED_BG

class ChooseForecastDialog:
    """
    Модалка вибору передбачення:
    - поле 'Назва візуалізації' (необов’язково)
    - список передбачень (один вибір)
    Повертає: {"forecast_name": str, "label": str}
    """
    def __init__(self, master, on_save, *, forecast_names=None):
        self.master = master
        self.on_save = on_save
        self.names = forecast_names or []

        self.top = tk.Toplevel(master)
        self.top.title("Передбачення")
        self.top.transient(master); self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(False, False)

        w, h = 420, 320
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Передбачення", bg=BLUE_BG, font=("", 10, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(frm, height=6, exportselection=False)
        for n in self.names:
            self.listbox.insert("end", n)
        self.listbox.pack(fill="both", expand=True, pady=(4,8))

        tk.Label(frm, text="Копія (мітка):", bg=BLUE_BG).pack(anchor="w")
        self.label_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.label_var).pack(fill="x", pady=(0,8))

        actions = tk.Frame(frm, bg=BLUE_BG); actions.pack(anchor="e")
        tk.Button(actions, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(actions, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

    def _save(self):
        if not self.listbox.curselection():
            messagebox.showwarning("Перевірка", "Оберіть передбачення.")
            return
        name = self.listbox.get(self.listbox.curselection()[0])
        payload = {"forecast_name": name, "label": self.label_var.get().strip()}
        self.top.grab_release(); self.top.destroy()
        self.on_save(payload)
