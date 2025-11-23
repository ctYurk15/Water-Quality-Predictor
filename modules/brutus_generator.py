import time
import math
import decimal
import tkinter as tk
import threading
import os
from tkinter import ttk, messagebox
from tkinter import ttk, colorchooser, messagebox
from datetime import datetime

from dialogs.loading import LoadingWindow
from modules.prophet_multivar import forecast_with_regressors
from modules.helpers import smart_param_generator
from src.forecast import Forecast
from src.timeseries import Timeseries

class BrutusGenerator:
    """
    Генератор найкращих налаштувань моделі шляхом перебору
    """
    def __init__(self, container, payload):
        self.container = container
        self.payload = payload
        self.lw = LoadingWindow(self.container, loading_text=f"Підготовка комбінацій...")
    
    def start(self):

        self.lw.top.update_idletasks()

        target_params = {}
        variations = {}

        def worker():
            err = None
            result = None
            try:
                
                target_params = dict(
                    name=self.payload['name'],
                    timeseries=self.payload['timeseries'],
                    parameter=self.payload['parameter'],
                    target_forecast_from=self.payload['target_forecast_from'],
                    target_forecast_to=self.payload['target_forecast_to'],
                    result_freq=self.payload['result_freq'],
                    model_freq=self.payload['model_freq'],
                    min_value=self.payload['min_value'],
                    max_value=self.payload['max_value'],
                    train_year_max=int(self.payload['train_to_year'])
                )

                max_steps = 25

                single_regressor_value=self.get_variations_in_range(
                    float(self.payload['min_single_regressor_value']), 
                    float(self.payload['max_single_regressor_value']), 
                    max_steps=10)

                regressors = {}
                for regressor in self.payload['regressors']:
                    if regressor != self.payload['parameter']: regressors[regressor] = single_regressor_value

                iteration_params = dict(
                    train_year=self.get_variations_in_range(
                        float(self.payload['train_from_year']), 
                        float(self.payload['train_to_year']), 
                        1),
                    regressor_prior_scale=self.get_variations_in_range(
                        min_val=float(self.payload['regressor_prior_scale_min']), 
                        max_val=float(self.payload['regressor_prior_scale_max']),
                        max_steps=max_steps),
                    regressor_future_linear_window=self.get_variations_in_range(
                        min_val=float(self.payload['regressor_future_linear_window_min']), 
                        max_val=float(self.payload['regressor_future_linear_window_max']),
                        max_steps=max_steps),   
                    smooth_window=self.get_variations_in_range(
                        min_val=float(self.payload['smooth_window_min']), 
                        max_val=float(self.payload['smooth_window_max']),
                        max_steps=max_steps), 
                    changepoint_prior_scale=self.get_variations_in_range(
                        min_val=float(self.payload['changepoint_prior_scale_min']), 
                        max_val=float(self.payload['changepoint_prior_scale_max']),
                        max_steps=max_steps),
                    seasonality_prior_scale=self.get_variations_in_range(
                        min_val=float(self.payload['seasonality_prior_scale_min']), 
                        max_val=float(self.payload['seasonality_prior_scale_max']),
                        max_steps=max_steps),
                    regressor_global_importance=self.get_variations_in_range(
                        min_val=float(self.payload['regressor_global_importance_min']), 
                        max_val=float(self.payload['regressor_global_importance_max']),
                        max_steps=max_steps),
                    regressor_standardize=self.payload['regressor_standardize'],
                    regressor_mode=self.payload['regressor_mode'],
                    smooth_regressors=self.payload['smooth_regressors'],
                    regressors=regressors
                )

                print(target_params)
                print("\n")
                #170 000 000 000 000 000 000 000 000 000 000 000 000 000 (max-steps - 50)
                print(iteration_params)

            except Exception as e:
                err = e
            finally:
                def finish():
                    try:
                        print('Combinations calculated')
                    except Exception:
                        pass
                    if err:
                        messagebox.showerror("Помилка", str(err), parent=self.container)
                    else:
                        self.iterate_variants(target_params, iteration_params)
                    

                self.container.after(0, finish)


        threading.Thread(target=worker, daemon=True).start()

    def iterate_variants(self, target_params, iteration_params):

        #n_main_samples = 2000
        n_main_samples = 10
        #n_regressor_sets = 30
        n_regressor_sets = 2

        max_combinations_count = n_main_samples * (n_regressor_sets + 1)

        executions_folder = "brutus_run_"+(datetime.now().strftime('%Y_%m_%d_%H_%M_%S'))
        executions_path = Forecast.file_path + "/" + executions_folder
        if os.path.isdir(executions_path): messagebox.showerror("Помилка", "Такий шлях уже існує - "+executions_path, parent=self.container)
        os.mkdir(executions_path)
        print('Output - '+executions_path)

        self.lw.change_text(f"Прогрес: 0 / {max_combinations_count} комбінацій...")
        self.lw.top.update_idletasks()

        #send forecast to another tread
        def worker():
            err = None
            result = None
            try:
                index = 0
                current_leader = ""
                current_max_accuracy = 0
                for variation in smart_param_generator(iteration_params, n_main_samples=n_main_samples, n_regressor_sets=n_regressor_sets):
                    # текст для оновлення
                    text = f"Прогрес: {index+1} / {max_combinations_count} комбінацій...\n"
                    if current_leader  != "":
                        text += f"Теперішній лідер - {current_leader} ( {current_max_accuracy} %)"

                    # безпечно просимо main-thread оновити лейбл
                    self.container.after(
                        0,
                        lambda t=text: self.lw.change_text(t)
                    )

                    #print(variation)

                    accuracy = 0.01
                    execution_name = 'run-'+str(index)
                    execution_folder = executions_folder+'/' + execution_name
                    forecast_with_regressors(
                        timeseries_dir=Timeseries.fullPath(target_params['timeseries']),
                        target=target_params['parameter'],
                        regressors=list(variation['regressors'].keys()),
                        station_code=None,              # or "...", optional
                        station_id=None,                # or "26853", optional
                        freq=target_params['result_freq'], 
                        agg="mean", 
                        growth="linear",
                        model_freq=target_params['model_freq'],

                        train_start=str(int(variation['train_year']))+'-01-01', 
                        train_end=str(target_params['train_year_max'])+'-12-31',

                        fcst_start=target_params['target_forecast_from'], 
                        fcst_end=target_params['target_forecast_to'],

                        forecast_name=execution_folder,           # groups outputs under forecasts/set1/
                        write_to_disk=True,
                        accuracy_tolerance=accuracy,
                        target_min=float(target_params['min_value']),             # floor
                        target_max=float(target_params['max_value']),             # cap
                        # regularization + smoothing
                        regressor_prior_scale=float(variation['regressor_prior_scale']),          # try 0.05–0.5; smaller → smoother
                        regressor_standardize=variation['regressor_standardize'],
                        regressor_mode=variation['regressor_mode'],                 # or "additive" explicitly
                        smooth_regressors=variation['smooth_regressors'],
                        smooth_window=int(variation['smooth_window']),                     # try 14 for extra smoothness
                        changepoint_prior_scale=float(variation['changepoint_prior_scale']),        # try 0.02–0.1
                        seasonality_prior_scale=float(variation['seasonality_prior_scale']),
                        regressor_global_importance=float(variation['regressor_global_importance']),
                        regressor_importance=variation['regressors'],
                        #regressor_future_ma_window=60,      # try 30–60 for daily data
                        regressor_future_strategy="linear",
                        regressor_future_linear_window=variation['regressor_future_linear_window']
                    )
                    
                    result_accuracy = Forecast.getAccuracy(execution_folder)
                    if result_accuracy > current_max_accuracy:
                        current_leader = execution_name
                        current_max_accuracy = result_accuracy

                    index += 1
                    #print("\n")

                    #time.sleep(0.1)  # тут можна хоч важкі обчислення робити

            except Exception as e:
                err = e
            finally:
                def finish():
                    try:
                        self.lw.top.destroy()
                    except Exception:
                        pass
                    if err:
                        messagebox.showerror("Помилка", str(err), parent=self.container)
                    else:
                        messagebox.showinfo("Готово", f"Модель створено.", parent=self.container)

                self.container.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def get_variations_in_range(self, min_val, max_val, step=None, max_steps=None):
        result = [min_val]

        if min_val == 0:
            min_val = 1.0
            result.append(1.0)

        # find step size
        if step == None:
            min_integer = self.to_full_int(min_val)
            multiplicator = min_integer / min_val

            steps_count = (max_val * multiplicator - min_integer) + 1
            step_raw = max_val / steps_count
            
            decimal_digits = int(math.log10(multiplicator))
            step = round(float(step_raw), decimal_digits)

            if max_steps != None and max_steps < steps_count:
                step_raw = (steps_count * step_raw) / max_steps
                step = round(float(step_raw), decimal_digits)
        else:
            d = decimal.Decimal(str(step))
            decimal_digits = abs(d.as_tuple().exponent)

        item = min_val
        while (item + step) <= max_val:
            item += step
            result.append(round(item, decimal_digits))

        if max_val not in result: result.append(max_val)

        return result

    def to_full_int(self, number):
        while int(number) != number:
            number *= 10
        return number