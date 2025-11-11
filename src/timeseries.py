import os

from src.file_model import FileModel

class Timeseries(FileModel):

    file_path = 'timeseries'

    entries_cache = []

    @classmethod
    def getEntries(cls, force_update = False, only_names = False):
        if cls.entries_cache == [] or force_update:
            items = cls.getItems()
            cls.entries_cache = items['directories']

        if only_names:
            result = []
            for entry in cls.entries_cache: result.append(entry['name'])
            return result
        else:
            return cls.entries_cache


    params_cache = []

    @classmethod
    def getParams(cls, force_update = False):
        if cls.params_cache == [] or force_update:
            entries = cls.getEntries()
            if entries != []:
                path_to_check = cls.file_path+'/'+entries[0]['name']
                items = os.listdir(path_to_check)

                for item in items:
                    item_path = path_to_check+'/'+item

                    if os.path.isfile(item_path):
                        item = item.replace('.csv', '')
                        cls.params_cache.append(item)

        return cls.params_cache