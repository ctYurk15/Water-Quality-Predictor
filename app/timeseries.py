import pandas
import os

class Timeseries:

    timeseries_path = "timeseries/"

    @staticmethod
    def fullPath(file_name):
        return Timeseries.timeseries_path+file_name

    @staticmethod
    def fileExists(file_name):
        return os.path.isfile(Timeseries.fullPath(file_name))