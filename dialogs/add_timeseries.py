import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from theme import BLUE_BG, BG_MAIN, RED_BG

class AddTimeseriesDialog:
    """Модалка: назва + вибір кількох файлів з папки raw-datasets (multi-select)."""
    def __init__(self, master, on_save):
        self.master = master
        self.on_save = on_save

        self.top = tk.Toplevel(master)
        self.top.title("Новий часовий ряд")
        self.top.transient(master)
        self.top.grab_set()
        self.top.configure(bg=BLUE_BG)
        self.top.resizable(False, False)

        w, h = 520, 320
        self._center(master, w, h)

        self.dataset_dir = Path.cwd() / "raw-datasets"
        self.dataset_dir.mkdir(exist_ok=True)
        self.selected_files = []

        self._build()

    def _center(self, master, w, h):
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="…Назва часового ряду…", bg=BLUE_BG).grid(row=0, column=0, sticky="w", padx=8, pady=(10,4))
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var).grid(row=1, column=0, columnspan=3, sticky="ew", padx=8)

        choose_frame = tk.Frame(frm, bg=BLUE_BG)
        choose_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=8, pady=(10,4))
        tk.Button(choose_frame, text="Обрати файли…", command=self._browse_files).pack(side="left")

        tk.Label(frm, text="Вибрані файли:", bg=BLUE_BG).grid(row=3, column=0, sticky="w", padx=8, pady=(8,2))
        list_frame = tk.Frame(frm, bg=BLUE_BG)
        list_frame.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=8)
        frm.grid_rowconfigure(4, weight=1)
        frm.grid_columnconfigure(0, weight=1)

        self.files_listbox = tk.Listbox(list_frame, height=6)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.files_listbox.yview)
        self.files_listbox.configure(yscrollcommand=sb.set)
        self.files_listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        ctrl = tk.Frame(frm, bg=BLUE_BG)
        ctrl.grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(6,0))
        tk.Button(ctrl, text="Видалити вибрані", command=self._remove_selected).pack(side="left")
        tk.Button(ctrl, text="Очистити всі", command=self._clear_all).pack(side="left", padx=(6,0))

        btns = tk.Frame(frm, bg=BLUE_BG)
        btns.grid(row=6, column=0, columnspan=3, sticky="e", pady=(12, 8), padx=8)
        tk.Button(btns, text="Зберегти", bg=BG_MAIN, command=self._save).pack(side="left", padx=(0,8))
        tk.Button(btns, text="Скасувати", bg=RED_BG, command=self.top.destroy).pack(side="left")

    def _browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Обрати файли часового ряду",
            initialdir=str(self.dataset_dir),
            filetypes=[("CSV файли", "*.csv"), ("Усі файли", "*.*")]
        )
        for p in paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
                self.files_listbox.insert("end", p)

    def _remove_selected(self):
        for idx in list(self.files_listbox.curselection())[::-1]:
            path = self.files_listbox.get(idx)
            self.files_listbox.delete(idx)
            if path in self.selected_files:
                self.selected_files.remove(path)

    def _clear_all(self):
        self.files_listbox.delete(0, "end")
        self.selected_files.clear()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Перевірка", "Вкажіть назву часового ряду.")
            return
        self.top.grab_release()
        self.top.destroy()
        self.on_save(name, list(self.selected_files))
