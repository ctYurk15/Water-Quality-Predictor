import json

from src.file_model import FileModel

class Forecast(FileModel):

    file_path = "forecasts"

    @classmethod
    def getDataFilePath(cls, file_name):
        return cls.fullPath(file_name)+"/data.json"

    @classmethod
    def getData(cls, forecast_name):
        path = cls.getDataFilePath(forecast_name)
        with open(path, 'r') as file:
            data = json.load(file)
        return data['items'][0]

    @classmethod
    def getAccuracy(cls, forecast_name):
        forecast_data = cls.getData(forecast_name)
        key = next(iter(forecast_data['metrics']))
        return float(forecast_data['metrics'][key]['accuracy']) * 100