import tkinter as tk
from tkinter import ttk, messagebox
from theme import BLUE_BG, BG_MAIN, RED_BG

class EditModelDialog:
    """Модалка перейменування моделі (редагує переданий tk.StringVar)."""
    def __init__(self, master, name_var: tk.StringVar):
        self.master = master
        self.name_var = name_var

        self.top = tk.Toplevel(master)
        self.top.title("Перейменувати модель")
        self.top.transient(master)
        self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(False, False)

        w, h = 420, 160
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Нова назва моделі:", bg=BLUE_BG).pack(anchor="w")
        entry = ttk.Entry(frm, textvariable=self.name_var, width=40)
        entry.pack(fill="x", pady=8); entry.focus_set()

        actions = tk.Frame(frm, bg=BLUE_BG)
        actions.pack(anchor="e")
        tk.Button(actions, text="OK", bg=BG_MAIN, command=self._ok).pack(side="left", padx=(0,8))
        tk.Button(actions, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

    def _ok(self):
        if not self.name_var.get().strip():
            messagebox.showwarning("Перевірка", "Назва не може бути порожньою.")
            return
        self.top.grab_release()
        self.top.destroy()
