import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path

# ---- Colors ----
BG_MAIN  = "#D5E8D4"   # app bg
BG_PANEL = "#CFE3C9"   # right pane
BLUE_BG  = "#DAE8FC"   # left menu buttons / modal
RED_BG   = "#F8CECC"
PURPLE_BG= "#E1D5E7"

APP_W, APP_H = 1280, 720  # 720p

# ---------- Base view with common layout (left gutter + right scroll list) ----------
class BaseListView(ttk.Frame):
    title = ""

    def __init__(self, master, on_add_click):
        super().__init__(master)
        self.configure(style="BaseView.TFrame")
        self.on_add_click = on_add_click

        # header
        head = ttk.Label(self, text=self.title, style="Head.TLabel")
        head.pack(anchor="n", pady=(18, 8))

        # 2 columns: left gutter for "+" and right scrollable list
        columns = tk.Frame(self, bg=BG_PANEL)
        columns.pack(fill="both", expand=True)

        columns.grid_columnconfigure(0, minsize=70)
        columns.grid_columnconfigure(1, weight=1)
        columns.grid_rowconfigure(0, weight=1)

        self.add_btn = tk.Button(
            columns, text="＋", font=("", 16, "bold"),
            width=3, height=1, bg=PURPLE_BG, fg="#3f3356",
            relief="raised", bd=1, command=self.on_add_click
        )
        self.add_btn.grid(row=0, column=0, sticky="n", padx=(18, 8), pady=(24, 0))

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
        self.canvas.bind("<Configure>", lambda e: self._update_canvas_width())

        self.row_idx = 0
        self.rows = []  # store per-view as needed

        spacer = tk.Frame(self.list_frame, bg=BG_PANEL, height=6)
        spacer.grid(row=0, column=0, sticky="ew")
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _update_canvas_width(self):
        self.canvas.itemconfigure(self._canvas_win_id, width=self.canvas.winfo_width())

    def _timestamp(self):
        return datetime.now().strftime("%d.%m.%Y %H:%M")

# ---------- Timeseries view ----------
class TimeseriesView(BaseListView):
    title = "Часові ряди"

    def __init__(self, master, on_add_click):
        super().__init__(master, on_add_click)

    def add_row(self, name, files=None):
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=self.row_idx + 1, column=0, sticky="ew", pady=8, padx=(24, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)

        name_var = tk.StringVar(value=name)
        ttk.Entry(row, textvariable=name_var, width=60).grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ttk.Label(row, text=self._timestamp(), style="Item.TLabel").grid(row=0, column=1, padx=10)

        tk.Button(row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f",
                  bd=1, relief="raised", command=lambda r=row: self._remove_row(r)).grid(row=0, column=2)

        self.rows.append((row, name_var, files or []))
        self.row_idx += 1
        self._update_canvas_width()

    def _remove_row(self, row_widget):
        for i, (frm, *_rest) in enumerate(self.rows):
            if frm == row_widget:
                frm.destroy()
                self.rows.pop(i)
                break
        for idx, (frm, *_rest) in enumerate(self.rows, start=1):
            frm.grid_configure(row=idx)
        self.row_idx = len(self.rows)
        self._update_canvas_width()

# ---------- Models view ----------
class ModelsView(BaseListView):
    title = "Моделі"

    def __init__(self, master, on_add_click, on_edit_click):
        super().__init__(master, on_add_click)
        self.on_edit_click = on_edit_click

    def add_row(self, name):
        row = tk.Frame(self.list_frame, bg=BG_PANEL)
        row.grid(row=self.row_idx + 1, column=0, sticky="ew", pady=8, padx=(24, 24))
        self.list_frame.grid_columnconfigure(0, weight=1)

        name_var = tk.StringVar(value=name)
        ttk.Entry(row, textvariable=name_var, width=60).grid(row=0, column=0, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        ttk.Label(row, text=self._timestamp(), style="Item.TLabel").grid(row=0, column=1, padx=10)

        # edit (pencil) + delete
        tk.Button(row, text="✎", width=3, bg="#FFE6CC", fg="#6b4b00",
                  bd=1, relief="raised",
                  command=lambda nv=name_var: self.on_edit_click(nv)).grid(row=0, column=2, padx=(0,6))
        tk.Button(row, text="✖", width=3, bg=RED_BG, fg="#8a0f0f",
                  bd=1, relief="raised",
                  command=lambda r=row: self._remove_row(r)).grid(row=0, column=3)

        self.rows.append((row, name_var))
        self.row_idx += 1
        self._update_canvas_width()

    def _remove_row(self, row_widget):
        for i, (frm, *_rest) in enumerate(self.rows):
            if frm == row_widget:
                frm.destroy()
                self.rows.pop(i)
                break
        for idx, (frm, *_rest) in enumerate(self.rows, start=1):
            frm.grid_configure(row=idx)
        self.row_idx = len(self.rows)
        self._update_canvas_width()

# ---------- Modal dialogs ----------
class AddTimeseriesDialog:
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

class EditModelDialog:
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
        self._center(master, w, h)
        self._build()

    def _center(self, master, w, h):
        self.top.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - w) // 2
        y = master.winfo_y() + (master.winfo_height() - h) // 2
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        frm = tk.Frame(self.top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(frm, text="Нова назва моделі:", bg=BLUE_BG).pack(anchor="w")
        entry = ttk.Entry(frm, textvariable=self.name_var, width=40)
        entry.pack(fill="x", pady=8)
        entry.focus_set()

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

# ---------- Main app ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ІС — Часові ряди / Моделі")
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(960, 540)
        self.configure(bg=BG_MAIN)

        self._init_style()
        self._build_shell()
        self._build_views()
        self.show_view("timeseries")

    def _init_style(self):
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("BaseView.TFrame", background=BG_PANEL)
        style.configure("Head.TLabel", font=("", 16, "bold"), background=BG_PANEL, foreground="#333")
        style.configure("List.TFrame", background=BG_PANEL)
        style.configure("Item.TLabel", background=BG_PANEL, foreground="#333")

    def _build_shell(self):
        # left menu
        self.left = tk.Frame(self, width=220, bg=BG_MAIN)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)

        self.btn_ts = tk.Button(self.left, text="Часові ряди", bg=BLUE_BG, activebackground=BLUE_BG,
                                relief="groove", bd=2, padx=14, pady=10,
                                command=lambda: self.show_view("timeseries"))
        self.btn_ts.pack(padx=16, pady=(16,8), anchor="n", fill="x")

        self.btn_models = tk.Button(self.left, text="Моделі", bg=BLUE_BG, activebackground=BLUE_BG,
                                    relief="groove", bd=2, padx=14, pady=10,
                                    command=lambda: self.show_view("models"))
        self.btn_models.pack(padx=16, pady=8, anchor="n", fill="x")

        # right area (stacked views)
        self.stack = tk.Frame(self, bg=BG_PANEL)
        self.stack.pack(side="left", fill="both", expand=True)

    def _build_views(self):
        # Timeseries
        self.ts_view = TimeseriesView(self.stack, on_add_click=self._open_add_ts)
        self.ts_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        for name in ["Timeseries_1_2010_2015", "Timeseries_2_2010_2015", "Timeseries_3_2007_2008"]:
            self.ts_view.add_row(name, files=[])

        # Models
        self.models_view = ModelsView(self.stack, on_add_click=self._add_model_modal, on_edit_click=self._edit_model_modal)
        self.models_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        for name in ["Model_1_2020_2021_Azot", "Model_2_2009_2012_SPAR"]:
            self.models_view.add_row(name)

    def show_view(self, key: str):
        # raise the desired view
        if key == "timeseries":
            self.ts_view.lift()
        else:
            self.models_view.lift()

    # ---- Actions ----
    def _open_add_ts(self):
        AddTimeseriesDialog(self, on_save=lambda name, files: self.ts_view.add_row(name, files=files))

    def _add_model_modal(self):
        # simplest add: ask for a name
        def save_name():
            name = entry_var.get().strip()
            if not name:
                messagebox.showwarning("Перевірка", "Вкажіть назву моделі.")
                return
            top.grab_release(); top.destroy()
            self.models_view.add_row(name)

        top = tk.Toplevel(self)
        top.title("Нова модель")
        top.transient(self); top.grab_set(); top.configure(bg=BLUE_BG); top.resizable(False, False)
        w, h = 420, 160
        top.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        top.geometry(f"{w}x{h}+{x}+{y}")

        frm = tk.Frame(top, bg=BLUE_BG, bd=2, relief="groove")
        frm.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(frm, text="…Назва моделі…", bg=BLUE_BG).pack(anchor="w")
        entry_var = tk.StringVar()
        ttk.Entry(frm, textvariable=entry_var).pack(fill="x", pady=8)
        actions = tk.Frame(frm, bg=BLUE_BG); actions.pack(anchor="e")
        tk.Button(actions, text="Зберегти", bg=BG_MAIN, command=save_name).pack(side="left", padx=(0,8))
        tk.Button(actions, text="Скасувати", bg=RED_BG, command=top.destroy).pack(side="left")

    def _edit_model_modal(self, name_var: tk.StringVar):
        EditModelDialog(self, name_var)

# ---------- run ----------
if __name__ == "__main__":
    app = App()
    app.mainloop()
