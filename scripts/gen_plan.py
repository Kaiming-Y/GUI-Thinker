import os
import sys
import copy
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.autopc import AutoPC
from agent.utils.gui_capture import get_screenshot, focus_software
from agent.gui_parser.sender import send_gui_parser_request
from agent.actor.utils import format_gui, compress_gui
from agent.config import basic_config
from experiment.test_utils import get_projfile_path, open_projfile, close_projfile


software_name = "VLC media player"
query = "Please add the logo watermark, with the file name 'watermark.png', to the bottom-right corner of the video, aligned with the edges."
video_path = r"D:\data\vlc\VLC09\VLC09.mp4"
have_projfile = True
projfile_path = get_projfile_path(software_name, video_path) if have_projfile else None

open_projfile(software_name, projfile_path)
focus_software(software_name)
import pyautogui
pyautogui.hotkey('alt', 'space')
time.sleep(0.5)
pyautogui.press('x')

autopc = AutoPC(user_id=software_name.replace(" ", ""), project_id="test")

focus_software(software_name)
meta_data, screenshot_path = get_screenshot(software_name)
gui_results = send_gui_parser_request(basic_config['gui_parser']['url'], software_name, screenshot_path, meta_data, task_id="test", step_id="1")
gui_info = compress_gui(copy.deepcopy(gui_results))
gui_info = "\n".join(format_gui(gui_info))

focus_software(software_name)
plan = autopc.run_planner(query, software_name, screenshot_path, gui_info, video_path)
print(plan)

close_projfile(software_name)
