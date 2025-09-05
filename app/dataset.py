import pandas
import os

class Dataset:

    datasets_path = "raw-datasets/"

    @staticmethod
    def fullPath(file_name):
        return Dataset.datasets_path+file_name

    @staticmethod
    def fileExists(file_name):
        return os.path.isfile(Dataset.fullPath(file_name))