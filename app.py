import tkinter as tk
from tkinter import ttk, messagebox
from theme import BG_MAIN, BG_PANEL, BLUE_BG, RED_BG, init_styles
from views.timeseries_view import TimeseriesView
from views.models_view import ModelsView
from dialogs.add_timeseries import AddTimeseriesDialog
from dialogs.model_form import AddOrEditModelDialog

APP_W, APP_H = 1280, 720  # 720p

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ІС — Часові ряди / Моделі")
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(960, 540)
        self.configure(bg=BG_MAIN)

        init_styles()  # спільні стилі ttk

        self._build_menubar()
        self._build_shell()
        self._build_views()

        self.show_view("timeseries")

    # ---------- Menu ----------
    def _build_menubar(self):
        menubar = tk.Menu(self)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Часові ряди", command=lambda: self.show_view("timeseries"))
        view_menu.add_command(label="Моделі", command=lambda: self.show_view("models"))
        menubar.add_cascade(label="Вигляд", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Про програму", command=self._about)
        menubar.add_cascade(label="Допомога", menu=help_menu)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Вихід", command=self.destroy, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Файл", menu=file_menu)

        self.config(menu=menubar)
        self.bind_all("<Control-q>", lambda e: self.destroy())

    # ---------- Shell (left nav + stack) ----------
    def _build_shell(self):
        # ліва навігація
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

        # правий стек екранів
        self.stack = tk.Frame(self, bg=BG_PANEL)
        self.stack.pack(side="left", fill="both", expand=True)

    # ---------- Views ----------
    def _build_views(self):
        # екран Часові ряди
        self.ts_view = TimeseriesView(self.stack,
                                      on_add_click=self._open_add_ts,
                                      on_delete_row=None)
        self.ts_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        for name in ["Timeseries_1_2010_2015", "Timeseries_2_2010_2015", "Timeseries_3_2007_2008"]:
            self.ts_view.add_row(name, files=[])

        # екран Моделі
        self.models_view = ModelsView(self.stack,
                                      on_add_click=self._add_model_modal,
                                      on_edit_click=self._edit_model_modal)
        self.models_view.place(relx=0, rely=0, relwidth=1, relheight=1)
        for name in ["Model_1_2020_2021_Azot", "Model_2_2009_2012_SPAR"]:
            self.models_view.add_row(name)

    def show_view(self, key: str):
        if key == "timeseries":
            self.ts_view.lift()
        else:
            self.models_view.lift()

    # ---------- Actions used by views ----------
    def _open_add_ts(self):
        AddTimeseriesDialog(self, on_save=lambda name, files: self.ts_view.add_row(name, files=files))


    def _add_model_modal(self):
        def on_save(model_dict):
            self.models_view.add_row(model_dict["name"], meta=model_dict)

        AddOrEditModelDialog(
            self,
            on_save=on_save,
            # за бажанням підставте реальні списки:
            timeseries_options=None,
            parameter_options=["A", "Azot", "Ammonium", "SPAR"],
            regressor_options=["A", "Azot", "Ammonium", "SPAR"],
        )

    def _edit_model_modal(self, view: "ModelsView", row_widget):
        # поточні дані
        cur_name, cur_meta = view.get_row_data(row_widget)
        if not cur_meta:
            # якщо модель була створена старою короткою формою — зіб’ємо initial з назви
            cur_meta = {"name": cur_name}

        def on_save(updated):
            view.set_row_data(row_widget, name=updated.get("name", cur_name), meta=updated)

        AddOrEditModelDialog(
            self,
            on_save=on_save,
            timeseries_options=None,
            parameter_options=["A", "Azot", "Ammonium", "SPAR"],
            regressor_options=["A", "Azot", "Ammonium", "SPAR"],
            initial={**cur_meta, "name": cur_name}
        )


    # ---------- Help ----------
    def _about(self):
        messagebox.showinfo("Про програму",
                            "ІС для прогнозування забруднень водних ресурсів України\n"
                            "Каркас GUI (Tkinter).\n© Магістерський проєкт")

if __name__ == "__main__":
    App().mainloop()
