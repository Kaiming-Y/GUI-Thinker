import os
import sys
from pathlib import Path
import copy
import time
import json
from typing import Dict
import pyautogui
import shutil
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from agent.autopc import AutoPC
from agent.utils.gui_capture import get_screenshot, focus_software
from agent.gui_parser.sender import send_gui_parser_request
from agent.actor.utils import format_gui, compress_gui
from agent.config import basic_config
from winarena.setup import WindowsSetupController, DOMAIN_LIST


domain_idx = 9
task_uid = "215dfd39-f493-4bc3-a027-8a97d72c61bf-WOS"
# task_uid = None

WINARENA_ROOT = Path("D:/data/winarena")
DONE_LOG = WINARENA_ROOT / "finished_tasks.log"

def load_jsondata(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def open_task(software_name: str, controller: WindowsSetupController, pre_config: str):
    controller.setup(pre_config)
    focus_software(software_name)
    pyautogui.hotkey('alt', 'space')
    time.sleep(0.5)
    pyautogui.press('x')

def close_task(software_name: str):
    focus_software(software_name)
    pyautogui.hotkey('alt', 'f4')

def load_done_set() -> set[str]:
    if DONE_LOG.exists():
        return set(DONE_LOG.read_text(encoding="utf-8").splitlines())
    return set()

def save_done(task_id: str):
    with DONE_LOG.open("a", encoding="utf-8") as fp:
        fp.write(task_id + "\n")

def run_task(task_id: str,
             task_data: Dict,
             software_name: str):
    # Task-related data(task id, user query, config)    
    ProjectID = task_data["id"]
    query = task_data["instruction"]
    pre_config = task_data["config"]
    print('Task ID:', ProjectID)
    print('User Query:', query)

    # Open the Project File and Prepare the Initial State
    controller = WindowsSetupController(cache_dir=os.path.join(WINARENA_ROOT, ".cache", task_id))
    open_task(software_name, controller, pre_config)

    # time.sleep(1)
    # focus_software(software_name)

    ### <<<GUI-Thinker Starting...>>>
    # Agent Parameters
    maximum_step = 30
    max_critic_trials = 3
    state = '<Continue>'
    code = ""
    last_screenshot_path = ""
    critic_count = 0

    # Init Agent
    autopc = AutoPC(user_id=software_name, project_id=ProjectID)

    # Observe the Screen
    time.sleep(0.5)
    focus_software(software_name)
    meta_data, screenshot_path = get_screenshot(software_name)

    # Record the Initial Screen State
    start_screenpath = os.path.join(saved_folder, software_name, ProjectID, "start.png")
    print('Save result in', start_screenpath)
    os.makedirs(os.path.dirname(start_screenpath), exist_ok=True)
    shutil.copy(screenshot_path, start_screenpath)

    # Parsing the Screen
    gui_results = send_gui_parser_request(basic_config['gui_parser']['url'], software_name, screenshot_path, meta_data, task_id=ProjectID, step_id="1")
    gui_info = compress_gui(copy.deepcopy(gui_results))
    gui_info = "\n".join(format_gui(gui_info))

    # Planning
    focus_software(software_name)
    plan = autopc.run_planner(query, software_name, screenshot_path, gui_info, video_path=None)
    print(plan)

    # Executing Phase
    for idx in range(maximum_step):
        time.sleep(1)
        meta_data, screenshot_path = get_screenshot(software_name)
        # print("meta data: ", meta_data)
        # print(screenshot_path)
        
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
            # focus_software(software_name)
            exec(code)
            last_screenshot_path = screenshot_path
        
        if state == '<Continue>':
            state = '<Critic>'

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

    # Record the Finished Screen State
    time.sleep(1)
    meta_data, screenshot_path = get_screenshot(software_name)
    end_screenpath = os.path.join(saved_folder, software_name, ProjectID, "end.png")
    print('Save result in', end_screenpath)
    os.makedirs(os.path.dirname(end_screenpath), exist_ok=True)
    shutil.copy(screenshot_path, end_screenpath)

    ### <<<GUI-Thinker Ending...>>>

    # Close the project file
    try:
        close_task(software_name)
        time.sleep(1)
    except Exception as e:
        print(e)
    controller.shutdown()


if __name__ == "__main__":
    # Domain & Software Name
    domain = DOMAIN_LIST[f"{domain_idx}"]["domain"]
    software_name = DOMAIN_LIST[f"{domain_idx}"]["software_name"]

    # WindowsAgentArena Bench File Paths
    tasks_file_root = WINARENA_ROOT / "examples" / domain # Specific to domain tasks
    winarena_all_data  = load_jsondata(os.path.join(WINARENA_ROOT, "test_all.json"))
    tasks_list = winarena_all_data[domain]

    done_set = load_done_set() # The tasks have been done

    # Save Results Path
    saved_folder = WINARENA_ROOT / "test_results" / basic_config['planner_critic']['lmm']
    saved_folder.mkdir(parents=True, exist_ok=True)

    # Specify a specific task uid
    if task_uid is not None:
        tasks_list = [task_uid] if task_uid in tasks_list else []

    # Run Task(s)
    for task_id in tasks_list:
        if task_id in done_set:
            print(f"Skip: {task_id} ...")
            continue

        task_data = load_jsondata(os.path.join(tasks_file_root, f"{task_id}.json"))
        run_task(task_id, task_data, software_name)

        save_done(task_id)
        done_set.add(task_id)
