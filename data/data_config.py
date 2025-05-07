import os
import json
import re


current_path = os.path.dirname(os.path.realpath(__file__))

ACROBAT_DATAFILE_NAME = "acrobat_data.json"
SETTINGS_DATAFILE_NAME = "settings_data.json"
WEB_DATAFILE_NAME = "chrome_data.json"

def get_datafile_name(software_name):
    software_name = re.sub(r'[^a-z0-9]', '', software_name.lower())
    if software_name == "settings":
        return SETTINGS_DATAFILE_NAME
    elif software_name == "adobeacrobat":
        return ACROBAT_DATAFILE_NAME
    elif software_name == "googlechrome":
        return WEB_DATAFILE_NAME
    

def load_datafile(software_name):
    datafile_name = get_datafile_name(software_name)
    datafile_path = os.path.join(current_path, datafile_name)
    datafile = json.load(open(datafile_path,'r'))
    return datafile
