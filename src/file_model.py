import os
import time
import datetime
import shutil

class FileModel:

    file_path = ""

    @classmethod
    def fullPath(cls, file_name):
        return cls.file_path+"/"+file_name

    @classmethod
    def fileExists(cls, file_name):
        return os.path.isfile(cls.fullPath(file_name))

    @classmethod
    def getItems(cls):

        result = {'files': [], 'directories': []}

        items = os.listdir(cls.file_path+"/")
        for item in items:
            item_path = cls.file_path+"/"+item
            item_modification = os.path.getmtime(item_path)
            new_element = {'name': item, 'time': datetime.datetime.fromtimestamp(item_modification)}

            if os.path.isfile(item_path):
                result['files'].append(new_element)
            else:
                result['directories'].append(new_element)

        return result

    @classmethod
    def deleteItem(cls, name):
        item_path = cls.file_path+"/"+name

        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)

    @classmethod
    def safeDeleteFile(cls, file_path):
        if os.path.isfile(file_path): os.remove(file_path)