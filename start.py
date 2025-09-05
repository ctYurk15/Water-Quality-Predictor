from app.dataset import Dataset
from timeseries_builder import build_timeseries

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