import os
import json
import re


current_path = os.path.dirname(os.path.realpath(__file__))

SOFTWARE_DATAFILE_MAP = {
    "settings": "settings_data.json",
    "adobeacrobat": "acrobat_data.json",
    "googlechrome": "chrome_data.json",
    "vlcmediaplayer": "vlc_data.json",
}

def get_datafile_name(software_name: str) -> str:
    normalized = re.sub(r'[^a-z0-9]', '', software_name.lower())
    return SOFTWARE_DATAFILE_MAP.get(normalized)

def load_datafile(software_name):
    datafile_name = get_datafile_name(software_name)
    datafile_path = os.path.join(current_path, datafile_name)
    datafile = json.load(open(datafile_path,'r'))
    return datafile
