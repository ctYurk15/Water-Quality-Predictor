from src.dataset import Dataset
from src.timeseries import Timeseries

from modules.timeseries_builder import build_timeseries
from modules.prophet_multivar import forecast_with_regressors
from modules.forecast_renderer import render_from_json

print("\n-----------------------------")
print('Welcome! Please choose an action: ')
print('1 - upload & process datasets')
print('2 - create prediction')
print('3 - view prediction')

action = int(input("\nYour choice: "))
print("\n-----------------------------\n")

match action:
    case 1:
        print('Input dataset(s) name(s) in `raw-datasets` folder. To stop, input empty name')

        datasets = []
        
        while True:
            dataset_name = input("Dataset filename: ").strip()
            if dataset_name == "":
                break

            if Dataset.fileExists(dataset_name):
                if dataset_name not in datasets:
                    datasets.append(Dataset.fullPath(dataset_name))
                else:
                    print(f"Dataset '{(dataset_name)}' is already added")
            else:
                print(f"Dataset '{(dataset_name)}' is not found in `raw-datasets` folder.")

        timeseries_set_name = input('Timeseries set name: ')

        result = build_timeseries(
            datasets=datasets,
            set_name=timeseries_set_name,
            out_root="timeseries"
        )  

        print(f'Timeseries set {timeseries_set_name} was successfully created')

    case 2:
        timeseries_name = input("Timeseries set name: ").strip()

        train_start_date = input("Train start date: ").strip() # 2003-01-02
        train_end_date = input("Train end date: ").strip() # 2010-12-31
        forecast_start_date = input("Forecast start date: ").strip() # 2011-01-01
        forecast_end_date = input("Forecast end date: ").strip() # 2012-12-28
        accuracy_raw = input("Accuracy (maximum % of prediction error, default - 15): ").strip()
        accuracy = 0.15
        if accuracy_raw != "":
            accuracy = int(accuracy_raw) / 100

        min_val = input("Minimum value (default - 0): ").strip()
        target_min = 0.0
        if min_val != "":
            target_min = float(min_val)

        max_val = input("Maximum value (default - 6): ").strip()
        target_max = 6.0
        if max_val != "":
            target_max = float(max_val)


        forecast_name = input("Forecast name: ").strip()

        fcst = forecast_with_regressors(
            timeseries_dir=Timeseries.fullPath(timeseries_name),
            target="SPAR",
            #regressors=["Amoniy"],
            #regressors=["Amoniy", "Atrazin"],
            #regressors=["Amoniy", "Atrazin", "BSK5", "Fosfat", "Hlorid"],
            #regressors=["BSK5", "HSK", "Fosfat", "Nitrat"],
            #regressors=["BSK5", "HSK", "Permanganat", "Amoniy", "Fosfat", "Nitrat"],
            #regressors=["BSK5", "HSK", "Permanganat", "Amoniy"],
            #regressors=["BSK5", "HSK"],
            regressors=["Fosfat", "Nitrat"],
            #regressors=[],
            station_code=None,              # or "...", optional
            station_id=None,                # or "26853", optional
            freq="D", 
            agg="mean", 
            growth="linear",
            model_freq="D",
            train_start=train_start_date, train_end=train_end_date,
            fcst_start=forecast_start_date, fcst_end=forecast_end_date,
            forecast_name=forecast_name,           # groups outputs under forecasts/set1/
            write_to_disk=True,
            accuracy_tolerance=accuracy,
            target_min=target_min,             # floor
            target_max=target_max,             # cap
            # NEW: regularization + smoothing
            regressor_prior_scale=0.5,          # try 0.05–0.5; smaller → smoother
            regressor_standardize="auto",
            regressor_mode="additive",                 # or "additive" explicitly
            smooth_regressors=True,
            smooth_window=7,                     # try 14 for extra smoothness
            changepoint_prior_scale=0.05,        # try 0.02–0.1
            seasonality_prior_scale=5.0,
            regressor_global_importance = 0.2,
            #regressor_importance = {
            #    "Amoniy": 2.0,    # 2× influence vs others
            #    "Atrazin": 0.5,   # 0.5× influence (more shrinkage)
            #}
            # keep your other params (bounds, smoothing, priors) as you had
            #regressor_future_strategy="moving_average",
            regressor_importance = {
                #"BSK5": 2.0,
                #"HSK": 2.0,
                #"Permanganat": 1.5,
                #"Amoniy": 1.2,
                "Fosfat": 1.0,
                "Nitrat": 0.8
            },
            regressor_future_ma_window=60,      # try 30–60 for daily data
            regressor_future_strategy="linear",
            regressor_future_linear_window=120
        )

        print(fcst.head())

    case 3:
        forecast_name = input("Forecast name: ").strip()
        #paths = render_from_json(forecast_name, target="Azot")
        paths = render_from_json(
            forecast_name=forecast_name,
            real_data_color='#0000FF',
            forecast_color='#FF0000'
        )
        print(paths)