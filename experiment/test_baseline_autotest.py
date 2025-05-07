import os
import sys
import copy
import time
import json
import glob
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.autopc import AutoPC
from agent.utils.gui_capture import get_screenshot, focus_software
from agent.gui_parser.sender import send_gui_parser_request
from agent.actor.utils import format_gui, compress_gui
from agent.config import basic_config
from data.data_config import load_datafile
from experiment.test_utils import get_projfile_path, open_projfile, close_projfile


software_name = "Settings"

begin_idx = 6
end_idx = None

aug_begin_idx = 0
aug_end_idx = None

datafile = load_datafile(software_name)[begin_idx:end_idx]

# Save Results Path
saved_folder = "test_results\\baseline\\%s"%(basic_config['planner_critic']['lmm'])


for i in range(len(datafile)):
    video_path = datafile[i]['video_path']
    ProjectID = datafile[i]['project_id']
    query = datafile[i]['user_query']
    projfile_path = get_projfile_path(software_name, video_path)

    # Aug data
    augfiles = glob.glob(os.path.join(os.path.dirname(video_path), f'{ProjectID}_aug_*.json'))
    # augfiles = glob.glob(os.path.join('D:\\data\\settings\\711', f'{ProjectID}_aug_*.json')) # Settings 711
    augfiles.insert(0, None)
    ## if you want set exact index of augfiles
    augfiles = augfiles[aug_begin_idx:aug_end_idx]

    for augfile in augfiles:
        open_projfile(software_name, projfile_path)
        time.sleep(2)
        focus_software(software_name)

        if augfile:
            pre_actions = json.load(open(augfile, 'r'))
            exec(pre_actions)

        # Agent Parameters
        maximum_step = 20
        state = '<Continue>'
        code = ""
        last_screenshot_path = ""

        autopc = AutoPC(software_name=software_name, project_id=ProjectID)

        focus_software(software_name)
        meta_data, screenshot_path = get_screenshot(software_name)

        if augfile:
            aug_name = os.path.basename(augfile).split('.')[0]
        else:
            aug_name = "meta"
        new_screenpath = os.path.join("%s"%(saved_folder), software_name, "%s_%s_start.png"%(ProjectID, aug_name))
        print('Save result in', new_screenpath)
        os.makedirs(os.path.dirname(new_screenpath), exist_ok=True)
        shutil.copy(screenshot_path, new_screenpath)


        gui_results = send_gui_parser_request(basic_config['gui_parser']['url'], software_name, screenshot_path, meta_data, task_id=ProjectID, step_id="1")
        gui_info = compress_gui(copy.deepcopy(gui_results))
        gui_info = "\n".join(format_gui(gui_info))

        print('User Query:', query)

        focus_software(software_name)
        plan = autopc.run_planner(query, software_name, screenshot_path, gui_info, video_path)
        print(plan)

        for idx in range(maximum_step):
            time.sleep(2)
            meta_data, screenshot_path = get_screenshot(software_name)
            # print("meta data: ", meta_data)
            # print(screenshot_path)
            
            print("===Current task===", "Index:",  idx, state)
            print(autopc.current_task.name.strip())
            code, state, current_task = autopc.run_step(state,
                                                        code,
                                                        autopc.current_task, 
                                                        meta_data, 
                                                        last_screenshot_path,
                                                        screenshot_path, 
                                                        software_name,
                                                        if_screenshot=True)
            
            ## execute the action code
            if code != "":
                focus_software(software_name)
                exec(code)
                last_screenshot_path = screenshot_path
            
            autopc.current_task = autopc.current_task.next()
            state = '<Continue>'
            code = ""
            if autopc.current_task is None:
                state = '<Finished>'
                print("===Current task===", "Index:",  idx, state)
                break

        time.sleep(1)
        meta_data, screenshot_path = get_screenshot(software_name)

        if augfile:
            aug_name = os.path.basename(augfile).split('.')[0]
        else:
            aug_name = "meta"
        new_screenpath = os.path.join("%s"%(saved_folder), software_name, "%s_%s_end.png"%(ProjectID, aug_name))
        print('Save result in', new_screenpath)
        os.makedirs(os.path.dirname(new_screenpath), exist_ok=True)
        shutil.copy(screenshot_path, new_screenpath)

        focus_software(software_name)
        try:
            close_projfile(software_name)
            time.sleep(1)
        except Exception as e:
            print(e)
