from app.dataset import Dataset
from app.timeseries import Timeseries

from timeseries_builder import build_timeseries
from prophet_module import batch_forecast, forecast_one

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

        batch_forecast(
            timeseries_dir=Timeseries.fullPath(timeseries_name),
            freq="MS", 
            agg="mean",
            param="Azot",                # або None для всіх
            station_code=None,           # або '...'
            station_id=None,             # або '26853'
            write_to_disk=True,          # вмикає запис CSV + _manifest.json
            outdir_name="forecasts",
            train_start=train_start_date, train_end=train_end_date,
            fcst_start=forecast_start_date, fcst_end=forecast_end_date,  # periods auto-derived
        )