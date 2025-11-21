import time
import math
import decimal
import tkinter as tk
import threading
from tkinter import ttk, messagebox
from tkinter import ttk, colorchooser, messagebox

from dialogs.loading import LoadingWindow
from modules.prophet_multivar import forecast_with_regressors

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
                )

                max_steps = 50

                iteration_params = dict(
                    train_year=self.get_variations_in_range(
                        float(self.payload['train_from_year']), 
                        float(self.payload['train_to_year']), 
                        1),
                    single_regressor_value=self.get_variations_in_range(
                        float(self.payload['min_single_regressor_value']), 
                        float(self.payload['max_single_regressor_value']), 
                        max_steps=max_steps),
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
                )

                print(target_params)
                print("\n")
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
                        self.iterate_variants()
                    

                self.container.after(0, finish)


        threading.Thread(target=worker, daemon=True).start()

    def iterate_variants(self):

        total_combinations_count = 10

        self.lw.change_text(f"Прогрес: 0 / {total_combinations_count} комбінацій...")
        self.lw.top.update_idletasks()

        #send forecast to another tread
        def worker():
            err = None
            result = None
            try:
                for i in range(total_combinations_count):
                    # текст для оновлення
                    text = f"Прогрес: {i+1} / {total_combinations_count} комбінацій..."

                    # безпечно просимо main-thread оновити лейбл
                    self.container.after(
                        0,
                        lambda t=text: self.lw.change_text(t)
                    )

                    time.sleep(0.1)  # тут можна хоч важкі обчислення робити

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

        decimal_digits = 0

        print([min_val, max_val])

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