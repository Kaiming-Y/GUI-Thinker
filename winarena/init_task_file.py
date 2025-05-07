import os
import json
from pathlib import Path

# related_apps → software 全名映射表
SOFTWARE_MAP = {
    "chrome": "Google Chrome",
    "clock": "Clock",
    "file_explorer": "File Explorer",
    "libreoffice-calc": "Excel",
    "libreoffice_writer": "Word",
    "microsoft_paint": "Paint",
    "edge": "Microsoft Edge",
    "notepad": "Notepad",
    "settings": "Settings",
    "vlc": "VLC media player",
    "vscode": "VS Code",
    "windows_calc": "Calculator",
}

# 可执行文件路径映射
EXE_MAP = {
    "google-chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge":       r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "vlc":          r"C:\Program Files\VideoLAN\VLC\vlc.exe",
}

def process_config(original_config: list) -> list:
    """
    Stub: 后续在这里根据每个 entry['type'] 做不同处理，
    暂时先直接原样返回。
    """
    # TODO: 按 type 分发到各自的转换函数
    return original_config

def transform_and_write(json_path: Path, output_root: Path):
    """
    读取 json_path，重命名字段、保留指定字段，将结果写入：
      output_root /
        <software_folder> /
        <json_stem> /
          <json_name>
    并在该目录下创建一个 downloads/ 子目录备用。
    其中 software_folder = json_path.parent.name
    """
    data = json.loads(json_path.read_text(encoding='utf-8'))

    # 构造新的结构
    new_data = {
        "id": data.get("id"),
        "domain": data.get("snapshot"),
        "software": None,
        "user_query": data.get("instruction"),
    }
    # 填充 software
    for key in data.get("related_apps", []):
        if key in SOFTWARE_MAP:
            new_data["software"] = SOFTWARE_MAP[key]
            break
    if new_data["software"] is None and data.get("related_apps"):
        new_data["software"] = data["related_apps"][0]

    # 保留其他字段
    for fld in ("source", "_comments", "evaluator"):
        if fld in data:
            new_data[fld] = data[fld]

    # 处理 config
    new_data["config"] = process_config(data.get("config", []))

    # 自动取父文件夹名作为 software_folder
    software_folder = json_path.parent.name

    # 创建输出目录
    task_dir = output_root / software_folder / json_path.stem

    # 写入新的 JSON（文件名同原名）
    out_json_path = task_dir / json_path.name
    out_json_path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"Written: {out_json_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="从 examples 目录批量读取 JSON，重命名字段并按软件分类输出到 tasks")
    parser.add_argument(
        "examples_root",
        help=r"原始 JSON 根目录，例如 D:\data\winarena\examples")
    parser.add_argument(
        "tasks_root",
        help=r"输出目录，例如 D:\data\winarena\tasks")
    args = parser.parse_args()

    # example_dir = args.examples_root
    example_dir = "D:\\data\\winarena\\examples"
    # task_dir = args.tasks_root
    task_dir = "D:\\data\\winarena\\tasks"

    examples_root = Path(example_dir)
    tasks_root = Path(task_dir)

    # 遍历每个软件文件夹
    for software_folder in os.listdir(examples_root):
        src_folder = examples_root / software_folder
        if not src_folder.is_dir():
            continue

        # 遍历该软件下所有 JSON 文件
        for fn in os.listdir(src_folder):
            if not fn.lower().endswith(".json"):
                continue
            json_path = src_folder / fn
            transform_and_write(json_path, tasks_root)

if __name__ == "__main__":
    main()