import tkinter as tk
from tkinter import ttk, messagebox
from theme import BG_MAIN, BG_PANEL, BLUE_BG, RED_BG, init_styles
from views.timeseries_view import TimeseriesView
from views.models_view import ModelsView
from dialogs.add_timeseries import AddTimeseriesDialog
from state import load_state, save_state
from dialogs.model_form import AddOrEditModelDialog
from views.forecasts_view import ForecastsView
from dialogs.forecast_form import AddForecastDialog

APP_W, APP_H = 1280, 720  # 720p

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ІС — Часові ряди / Моделі")
        self.geometry(f"{APP_W}x{APP_H}")
        self.minsize(960, 540)
        self.configure(bg=BG_MAIN)

        init_styles()  # спільні стилі ttk

        self._booting = True
        self._build_menubar()
        self._build_shell()
        self._build_views()

        self._load_state()
        self._booting = False 

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

        self.btn_models = tk.Button(
            self.left, text="Моделі", bg=BLUE_BG, activebackground=BLUE_BG,
            relief="groove", bd=2, padx=14, pady=10,
            command=lambda: self.show_view("models")
        )
        self.btn_models.pack(padx=16, pady=8, anchor="n", fill="x")

        # <<< ОЦЕ МАЄ БУТИ >>> 
        self.btn_forecasts = tk.Button(
            self.left, text="Передбачення", bg=BLUE_BG, activebackground=BLUE_BG,
            relief="groove", bd=2, padx=14, pady=10,
            command=lambda: self.show_view("forecasts")
        )
        self.btn_forecasts.pack(padx=16, pady=8, anchor="n", fill="x")

        # правий стек екранів
        self.stack = tk.Frame(self, bg=BG_PANEL)
        self.stack.pack(side="left", fill="both", expand=True)

    # ---------- Views ----------
    def _build_views(self):
        self.ts_view = TimeseriesView(
            self.stack,
            on_add_click=self._open_add_ts,
            on_rows_changed=self._save_state
        )
        self.ts_view.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.models_view = ModelsView(
            self.stack,
            on_add_click=self._add_model_modal,
            on_edit_click=self._edit_model_modal,
            on_rows_changed=self._save_state
        )
        self.models_view.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.forecasts_view = ForecastsView(self.stack, on_add_click=self._add_forecast_modal, on_rows_changed=self._save_state)
        self.forecasts_view.place(relx=0, rely=0, relwidth=1, relheight=1)


    def show_view(self, key: str):
        if key == "timeseries":
            self.ts_view.lift()
        elif key == "models":
            self.models_view.lift()
        else:
            self.forecasts_view.lift()

    # ---------- Actions used by views ----------
    def _open_add_ts(self):
        from dialogs.add_timeseries import AddTimeseriesDialog
        def on_save(name, files):
            self.ts_view.add_row(name, files=files)
            self._save_state()
        AddTimeseriesDialog(self, on_save=on_save)


    def _add_model_modal(self):
        def on_save(model_dict):
            self.models_view.add_row(model_dict["name"], meta=model_dict)
            self._save_state()
        #AddOrEditModelDialog(self, on_save=on_save)

        AddOrEditModelDialog(
            self,
            on_save=on_save,
            # за бажанням підставте реальні списки:
            timeseries_options=None,
            parameter_options=["A", "Azot", "Ammonium", "SPAR"],
            regressor_options=["A", "Azot", "Ammonium", "SPAR"],
        )

    def _edit_model_modal(self, view, row_widget):
        # дістати поточні дані з рядка
        cur_name, cur_meta = view.get_row_data(row_widget)
        if not cur_meta:
            cur_meta = {"name": cur_name}

        def on_save(updated):
            # оновити назву та метадані в рядку і зберегти стан
            view.set_row_data(row_widget,
                            name=updated.get("name", cur_name),
                            meta=updated)
            self._save_state()

        try:
            AddOrEditModelDialog(
                self,
                on_save=on_save,
                # при бажанні підстав реальні списки:
                timeseries_options=None,
                parameter_options=["A", "Azot", "Ammonium", "SPAR"],
                regressor_options=["A", "Azot", "Ammonium", "SPAR"],
                initial={**cur_meta, "name": cur_name}
            )
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Помилка редагування", str(e))

    def _add_forecast_modal(self):
        # список назв моделей зі списку models_view
        model_names = self.models_view.get_names()
        def on_save(data):
            self.forecasts_view.add_row(data)
            self._save_state()
        AddForecastDialog(self, on_save=on_save, model_names=model_names,
                        parameter_options=["A", "Azot", "Ammonium", "SPAR"])


    def _collect_state(self):
        return {
            "timeseries": self.ts_view.export_state(),
            "models": self.models_view.export_state(),
            "forecasts": self.forecasts_view.export_state(),
        }

    def _load_state(self):
        state = load_state()
        self.ts_view.import_state(state.get("timeseries"))
        self.models_view.import_state(state.get("models"))
        self.forecasts_view.import_state(state.get("forecasts"))
        # опціональні демо при першому запуску:
        if not state.get("forecasts"):
            self.forecasts_view.add_row({
                "name":"Forecast_3_BSK", "prob":"20",
                "model":"Model1", "parameter":"BSK",
                "train_from":"01.01.2019", "train_to":"31.12.2019",
                "created_at":"13.10.2025 18:10"
            })

        # якщо хочеш мати стартові демо при першому запуску:
        if not state.get("timeseries") and not state.get("models"):
            self.ts_view.add_row("Timeseries_1_2010_2015", files=[])
            self.ts_view.add_row("Timeseries_2_2010_2015", files=[])
            self.models_view.add_row("Model_1_2020_2021_Azot", meta={"name":"Model_1_2020_2021_Azot"})


    def _save_state(self):
        if getattr(self, "_booting", False):
            return
        save_state(self._collect_state())




    # ---------- Help ----------
    def _about(self):
        messagebox.showinfo("Про програму",
                            "ІС для прогнозування забруднень водних ресурсів України\n"
                            "Каркас GUI (Tkinter).\n© Магістерський проєкт")

if __name__ == "__main__":
    App().mainloop()
