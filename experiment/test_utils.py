import json
import os
import shutil
from pyautogui import hotkey, press
import time
import re
import subprocess


def open_projfile(software_name, projfile_path=None):
    software_name = re.sub(r'[^a-z0-9]', '', software_name.lower())
    
    if software_name == "settings":
        hotkey('win', 'i')

    elif software_name == "adobeacrobat":
        assert projfile_path is not None
        origin_projfile_path = get_origin_projfile_path(software_name, projfile_path)
        # Ensure the file is original
        try:
            shutil.copy2(origin_projfile_path, projfile_path)
        except Exception as e:
            print(e)
        # Open the project file
        subprocess.Popen(["C:\\Program Files\\Adobe\\Acrobat DC\\Acrobat\\Acrobat.exe", projfile_path], shell=True)
        
    elif software_name == "googlechrome":
        subprocess.Popen(["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"])
    elif software_name == "vlcmediaplayer":
        if projfile_path is not None:
            subprocess.Popen(["C:\\Program Files\\VideoLAN\\VLC\\vlc.exe", projfile_path], shell=True)
        else:
            subprocess.Popen(["C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"])


def close_projfile(software_name):
    software_name = re.sub(r'[^a-z0-9]', '', software_name.lower())

    if software_name in ["settings", "googlechrome", "vlcmediaplayer"]:
        hotkey('alt', 'f4')

    elif software_name in ["adobeacrobat"]:
        hotkey('ctrl', 'w')
        press('n')
        press('enter')



def get_projfile_path(software_name, video_path):
    software_name = re.sub(r'[^a-z0-9]', '', software_name.lower())

    if software_name == "adobeacrobat":
        projfile_path = os.path.join(os.path.dirname(video_path), "start.pdf")
    elif software_name == "powerpoint":
        projfile_path = os.path.join(os.path.dirname(video_path), "project.pptx")
    elif software_name == "word":
        projfile_path = os.path.join(os.path.dirname(video_path), "project.docx")
    elif software_name == "excel":
        projfile_path = os.path.join(os.path.dirname(video_path), "project.xlsx")
    elif software_name == "vlcmediaplayer":
        projfile_path = os.path.join(os.path.dirname(video_path), "project.mp4")
    else:
        projfile_path = None

    if not os.path.exists(projfile_path):
        projfile_path = None

    return projfile_path


def get_origin_projfile_path(software_name, projfile_path):
    software_name = re.sub(r'[^a-z0-9]', '', software_name.lower())

    if software_name == "adobeacrobat":
        origin_projfile_path = os.path.join(os.path.dirname(projfile_path), "..", "start.pdf")
    elif software_name == "powerpoint":
        origin_projfile_path = os.path.join(os.path.dirname(projfile_path), "..", "project.pptx")
    elif software_name == "word":
        origin_projfile_path = os.path.join(os.path.dirname(projfile_path), "..", "project.docx")
    elif software_name == "excel":
        origin_projfile_path = os.path.join(os.path.dirname(projfile_path), "..", "project.xlsx")
    else:
        origin_projfile_path = ''

    return origin_projfile_path
