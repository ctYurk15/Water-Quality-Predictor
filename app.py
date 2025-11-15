import tkinter as tk
import datetime
import threading
from tkinter import ttk, messagebox
from theme import BG_MAIN, BG_PANEL, BLUE_BG, RED_BG, init_styles
from views.timeseries_view import TimeseriesView
from views.models_view import ModelsView
from dialogs.add_timeseries import AddTimeseriesDialog
from state import load_state, save_state
from dialogs.model_form import AddOrEditModelDialog
from views.forecasts_view import ForecastsView
from dialogs.forecast_form import AddForecastDialog
from dialogs.visualization_form import ChooseForecastDialog
from dialogs.visualization_create import CreateVisualizationDialog
from dialogs.visualization_viewer import VisualizationViewer
from views.visualization_view import VisualizationsView
from dialogs.loading import LoadingWindow

from src.timeseries import Timeseries
from src.forecast import Forecast
from modules.timeseries_builder import build_timeseries
from prophet_multivar import forecast_with_regressors
from modules.forecast_renderer import render_from_json

APP_W, APP_H = 1280, 720

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

        #view_menu = tk.Menu(menubar, tearoff=0)
        #view_menu.add_command(label="Часові ряди", command=lambda: self.show_view("timeseries"))
        #view_menu.add_command(label="Моделі", command=lambda: self.show_view("models"))
        #menubar.add_cascade(label="Вигляд", menu=view_menu)

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

        self.btn_forecasts = tk.Button(
            self.left, text="Передбачення", bg=BLUE_BG, activebackground=BLUE_BG,
            relief="groove", bd=2, padx=14, pady=10,
            command=lambda: self.show_view("forecasts")
        )
        self.btn_forecasts.pack(padx=16, pady=8, anchor="n", fill="x")

        self.btn_viz = tk.Button(self.left, text="Візуалізація", bg=BLUE_BG, activebackground=BLUE_BG,
                         relief="groove", bd=2, padx=14, pady=10,
                         command=lambda: self.show_view("viz"))
        self.btn_viz.pack(padx=16, pady=8, anchor="n", fill="x")

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

        self.forecasts_view = ForecastsView(
            self.stack, 
            on_add_click=self._add_forecast_modal, 
            on_rows_changed=self._save_state,
            models_view=self.models_view
        )
        self.forecasts_view.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.visualization_view = VisualizationsView(
            self.stack,
            on_add_click=self._viz_create_modal,
            on_view_click=self._viz_open_viewer,
            on_rows_changed=self._save_state
        )
        self.visualization_view.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_view(self, key: str):
        if key == "timeseries":
            self.ts_view.lift()
        elif key == "models":
            self.models_view.lift()
        elif key == "forecasts":
            self.forecasts_view.lift()
        else:  # "viz"
            self.visualization_view.lift()

    # ---------- Actions used by views ----------
    def _open_add_ts(self):
        from dialogs.add_timeseries import AddTimeseriesDialog

        def on_save(name, files):

            lw = LoadingWindow(self, loading_text="Створення часового ряду "+name+"...")
            lw.top.update_idletasks()

            #send timeseries creation to another tread
            def worker():
                err = None
                result = None
                try:
                    result = build_timeseries(
                        datasets=files,
                        set_name=name,
                        out_root=Timeseries.file_path
                    )
                except Exception as e:
                    err = e
                finally:
                    def finish():
                        try:
                            lw.top.destroy()
                        except Exception:
                            pass
                        if err:
                            messagebox.showerror("Помилка", str(err), parent=self)
                        else:
                            messagebox.showinfo("Готово", f"Ряд '{name}' створено.", parent=self)
                            self.ts_view.add_row(name, time=datetime.datetime.now())

                    self.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        AddTimeseriesDialog(self, on_save=on_save)


    def _add_model_modal(self):
        def on_save(model_dict):
            self.models_view.add_row(model_dict["name"], meta=model_dict)
            self._save_state()

        timeseries = Timeseries.getEntries(True, True)
        params = Timeseries.getParams()

        AddOrEditModelDialog(
            self,
            on_save=on_save,
            timeseries_options=timeseries,
            parameter_options=params,
            regressor_options=params,
            models_view=self.models_view
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
            timeseries = Timeseries.getEntries(False, True)
            params = Timeseries.getParams()

            AddOrEditModelDialog(
                self,
                on_save=on_save,
                # при бажанні підстав реальні списки:
                timeseries_options=timeseries,
                parameter_options=params,
                regressor_options=params,
                initial={**cur_meta, "name": cur_name}
            )
        except Exception as e:
            #from tkinter import messagebox
            messagebox.showerror("Помилка редагування", str(e))

    def _add_forecast_modal(self):
        # список назв моделей зі списку models_view
        model_names = self.models_view.get_names()
        params = Timeseries.getParams()

        def on_save(data):
            self._save_state()

            selected_model = self.models_view.find_model_by_name(data['model'])
            if selected_model != {}:
                modal_meta = selected_model.get('meta')

                regressors = {}
                for param, value in modal_meta['weights'].items():
                    regressors[param] = float(value)

                accuracy = float(data['prob']) / 100

                lw = LoadingWindow(self, loading_text="Передбачення даних параметру "+modal_meta['parameter']+"...")
                lw.top.update_idletasks()

                #send forecast to another tread
                def worker():
                    err = None
                    result = None
                    try:
                        
                        forecast_with_regressors(
                            timeseries_dir=Timeseries.fullPath(modal_meta['timeseries']),
                            target=modal_meta['parameter'],
                            regressors=modal_meta['regressors'],
                            station_code=None,              # or "...", optional
                            station_id=None,                # or "26853", optional
                            freq="D", 
                            agg="mean", 
                            growth="linear",
                            model_freq="D",
                            train_start=modal_meta['train_from'], train_end=modal_meta['train_to'],
                            fcst_start=data['forecast_from'], fcst_end=data['forecast_to'],
                            forecast_name=data['name'],           # groups outputs under forecasts/set1/
                            write_to_disk=True,
                            accuracy_tolerance=accuracy,
                            target_min=float(modal_meta['min_value']),             # floor
                            target_max=float(modal_meta['max_value']),             # cap
                            # regularization + smoothing
                            regressor_prior_scale=0.5,          # try 0.05–0.5; smaller → smoother
                            regressor_standardize="auto",
                            regressor_mode="additive",                 # or "additive" explicitly
                            smooth_regressors=True,
                            smooth_window=7,                     # try 14 for extra smoothness
                            changepoint_prior_scale=0.05,        # try 0.02–0.1
                            seasonality_prior_scale=5.0,
                            regressor_global_importance = 0.2,
                            regressor_importance = regressors,
                            regressor_future_ma_window=60,      # try 30–60 for daily data
                            regressor_future_strategy="linear",
                            regressor_future_linear_window=120
                        )

                    except Exception as e:
                        err = e
                    finally:
                        def finish():
                            try:
                                lw.top.destroy()
                            except Exception:
                                pass
                            if err:
                                messagebox.showerror("Помилка", str(err), parent=self)
                            else:
                                messagebox.showinfo("Готово", f"Передбачення для '{modal_meta['parameter']}' створено.", parent=self)
                                self.forecasts_view.add_row(data)

                        self.after(0, finish)

                threading.Thread(target=worker, daemon=True).start()
                

        AddForecastDialog(self, on_save=on_save, model_names=model_names,
                        parameter_options=params)

    def _open_viz_modal(self):
        # імена передбачень беремо з екрана 'Передбачення'
        forecast_names = [it.get("name","") for it in self.forecasts_view.export_state()]
        if not forecast_names:
            #from tkinter import messagebox
            messagebox.showinfo("Візуалізація", "Немає передбачень. Спершу створіть їх на відповідній вкладці.")
            return

        def on_save(payload):
            # оновлюємо картку вгорі і одразу показуємо графік
            self.visualization_view.set_selection(payload["forecast_name"], created_at="")
            self.visualization_view.render_plot()

        ChooseForecastDialog(self, on_save=on_save, forecast_names=forecast_names)

    def _viz_create_modal(self):
        # імена передбачень беремо з екрана 'Передбачення'
        forecast_names = [
            d.get("name","") for d in self.forecasts_view.export_state() 
            if Forecast.hasImages(d.get("name","")) == False
        ]
        if not forecast_names:
            #from tkinter import messagebox
            messagebox.showinfo("Візуалізація", "Немає передбачень для візуалізації.")
            return

        def on_save(viz):
            self._save_state()

            lw = LoadingWindow(self, loading_text="Візуалізація передбачення "+viz.get('forecast_name')+"...")
            lw.top.update_idletasks()

            #send forecast render to another tread
            def worker():
                err = None
                result = None
                try:
                    render_from_json(
                        forecast_name=viz.get('forecast_name'),
                        real_data_color=viz.get('real_data_color'),
                        forecast_color=viz.get('forecast_color'),
                    )
                except Exception as e:
                    err = e
                finally:
                    def finish():
                        try:
                            lw.top.destroy()
                        except Exception:
                            pass
                        if err:
                            messagebox.showerror("Помилка", str(err), parent=self)
                        else:
                            messagebox.showinfo("Готово", f"Візуалізацію для передбачення '{viz.get('forecast_name')}' створено.", parent=self)
                            self.visualization_view.add_row(viz)

                    self.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        CreateVisualizationDialog(self, on_save=on_save, forecast_names=forecast_names)

    def _viz_open_viewer(self, viz: dict):
        if not viz or not viz.get("forecast_name"):
            #from tkinter import messagebox
            messagebox.showinfo("Візуалізація", "Виберіть візуалізацію.")
            return
        VisualizationViewer(self, forecast_title=viz.get("forecast_name"))


    def _collect_state(self):
        return {
            #"timeseries": self.ts_view.export_state(),
            "models": self.models_view.export_state(),
            "forecasts": self.forecasts_view.export_state(),
            "visualizations": self.visualization_view.export_state(),  # <—
        }

    def _load_state(self):
        state = load_state()
        #self.ts_view.import_state(state.get("timeseries"))

        timeseries = Timeseries.getEntries()

        self.ts_view.import_state(timeseries)
        self.models_view.import_state(state.get("models"))
        self.forecasts_view.import_state(state.get("forecasts"))
        self.visualization_view.import_state(state.get("visualizations"))


    def _save_state(self):
        if getattr(self, "_booting", False):
            return
        save_state(self._collect_state())




    # ---------- Help ----------
    def _about(self):
        messagebox.showinfo("Про програму",
                            "ІС для прогнозування забруднень водних ресурсів України\n"
                            "Каркас GUI (Tkinter).\n© Магістерський проект, автор - ctyurk15")

if __name__ == "__main__":
    App().mainloop()
