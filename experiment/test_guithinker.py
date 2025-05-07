import os
import sys
import copy
import time
import json
import glob
import shutil
import argparse
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from agent.autopc import AutoPC
from agent.utils.gui_capture import get_screenshot, focus_software
from agent.gui_parser.sender import send_gui_parser_request
from agent.actor.utils import format_gui, compress_gui
from agent.config import basic_config
from data.data_config import load_datafile
from experiment.test_utils import get_projfile_path, open_projfile, close_projfile
from experiment.log_tee import Tee


def main():
    parser = argparse.ArgumentParser(description="GUI-Thinker Locally Running")
    parser.add_argument("--software_name", type=str, default="PowerPoint")
    parser.add_argument("--userquery", type=str, default="Set the transitions of the second ppt to Push")
    parser.add_argument("--projectID", type=str, default="000", help="The ID of current task")
    parser.add_argument("--projfile_path", type=str, default="data/project_files/300. PowerPoint Applying Transitions/project.pptx", help="the file ready to operate")
    parser.add_argument("--maximum_step", type=int, default=20, help="total steps")
    parser.add_argument("--max_critic_trials", type=int, default=3, help="set the maiximum trials of critic times")
    args = parser.parse_args()

    software_name = args.software_name
    task_id = 2
    aug_id = 0

    # Ablation Experiments
    ablation = False
    ablation_exp = "w/o Planner-Critic"
    # ablation_exp = "w/o Step-Check"
    # ablation_exp = "w/o Actor-Critic"
    # ablation_exp = "AssistGUI"
    # ablation_exp = "w/o inst. video"

    # Project Data
    datafile = load_datafile(software_name)[task_id]
    video_path = datafile["video_path"]
    ProjectID = datafile['project_id']
    query = datafile['user_query']
    projfile_path = get_projfile_path(software_name, video_path)

    # Log File Setup
    log = Tee(f"{software_name}_{ProjectID}_output.log")

    # Save Results Path
    saved_folder = "test_results\\%s\\ablation"%(basic_config['planner_critic']['lmm']) if ablation else "test_results\\%s"%(basic_config['planner_critic']['lmm'])
    if ablation:
        if ablation_exp == "w/o Planner-Critic":
            saved_folder = os.path.join(saved_folder, "wo-planner_critic")
        elif ablation_exp == "w/o Step-Check":
            saved_folder = os.path.join(saved_folder, "wo-step_check")
        elif ablation_exp == "w/o Actor-Critic":
            saved_folder = os.path.join(saved_folder, "wo-actor_critic")
        elif ablation_exp == "AssistGUI":
            saved_folder = os.path.join(saved_folder, "assistgui")
        elif ablation_exp == "w/o inst. video":
            saved_folder = os.path.join(saved_folder, "wo-inst-video")

    # Aug data
    augfiles = glob.glob(os.path.join(os.path.dirname(video_path), f'{ProjectID}_aug_*.json'))
    augfiles.insert(0, None)
    augfile = augfiles[aug_id]

    if augfile is not None:
        pre_actions = json.load(open(augfile, 'r'))
        open_projfile(software_name, projfile_path)
        time.sleep(2)
        focus_software(software_name)
        exec(pre_actions)
    else:
        # open_projfile(software_name, projfile_path)
        # time.sleep(2)
        focus_software(software_name)

    # Agent Parameters
    maximum_step = 30
    max_critic_trials = 3
    state = '<Continue>'
    code = ""
    last_screenshot_path = ""
    critic_count = 0

    autopc = AutoPC(user_id=software_name, project_id=ProjectID)

    focus_software(software_name)
    meta_data, screenshot_path = get_screenshot(software_name)

    if augfile:
        aug_name = os.path.basename(augfile).split('.')[0]
    else:
        aug_name = "meta"
    new_screenpath = os.path.join("%s"%(saved_folder), software_name, "%s_%s_start.png"%(ProjectID, aug_name))
    # print('Save result in', new_screenpath)
    os.makedirs(os.path.dirname(new_screenpath), exist_ok=True)
    shutil.copy(screenshot_path, new_screenpath)


    gui_results = send_gui_parser_request(basic_config['gui_parser']['url'], software_name, screenshot_path, meta_data, task_id=ProjectID, step_id="1")
    gui_info = compress_gui(copy.deepcopy(gui_results))
    gui_info = "\n".join(format_gui(gui_info))

    os.system('cls') 
    print('User Query:', query)

    focus_software(software_name)
    plan = autopc.run_planner(query, software_name, screenshot_path, gui_info, video_path)
    print('Plan:', plan)

    for idx in range(maximum_step):
        time.sleep(2)
        meta_data, screenshot_path = get_screenshot(software_name)
        # print("meta data: ", meta_data)
        # print(screenshot_path)
        # os.system('cls') 
        print("===Current task===", "Index:",  idx, state)
        print(autopc.current_task.name.strip())
        code, state, current_task = autopc.run_step(state,
                                                    query,
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
        
        if state == '<Continue>':
            state = '<Critic>'
            ## w/o actorcritic
            # autopc.current_task = autopc.current_task.next()
            # state = '<Continue>'
            # code = ""
            # if autopc.current_task is None:
            #     state = '<Finished>'
            #     print("===Current task===", "Index:",  idx, state)
            #     break
            ## w/o actorcritic

        elif state == '<Next>':
            autopc.current_task = autopc.current_task.next()
            if autopc.current_task:
                state = '<Continue>'
                code = ""
                critic_count = 0
            else:
                state = '<Finished>'
                print("===Current task===", "Index:",  idx, state)
                break
            
        if state == '<Critic>':
            critic_count += 1
        
        if critic_count > max_critic_trials:
            autopc.current_task = autopc.current_task.next()
            if autopc.current_task:
                state = '<Continue>'
                code = ""
                critic_count = 0
            else:
                state = '<Finished>'
                print('current index', idx, state)
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

    log.close()


if __name__ == "__main__":
    main()