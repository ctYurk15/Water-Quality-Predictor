import json
import os

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

    @classmethod
    def getImagePath(cls, forecast_name, type):
        path = ''
        forecast_path = cls.fullPath(forecast_name)

        match type:
            case 'actuals':
                path = forecast_path+'/actuals.png'
            case 'forecast':
                path = forecast_path+'/forecast.png'
            case 'comparison':
                path = forecast_path+'/actuals_vs_forecast.png'

        return path

    @classmethod
    def hasImages(cls, forecast_name):
        if os.path.isfile(cls.getImagePath(forecast_name, 'actuals')) and os.path.isfile(cls.getImagePath(forecast_name, 'forecast')) and os.path.isfile(cls.getImagePath(forecast_name, 'comparison')):
            return True
        else:
            return False

    @classmethod
    def clearImages(cls, forecast_name):
        cls.safeDeleteFile(cls.getImagePath(forecast_name, 'actuals'))
        cls.safeDeleteFile(cls.getImagePath(forecast_name, 'forecast'))
        cls.safeDeleteFile(cls.getImagePath(forecast_name, 'comparison'))
