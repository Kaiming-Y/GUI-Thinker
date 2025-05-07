import os
import json
from collections import Counter, defaultdict

def scan_config_types(root_dir):
    """
    遍历 root_dir 下所有子文件夹中的 .json 文件，
    统计每个 JSON 文件中 "config" 字段列表里各 type 的出现次数，
    并为每种 type 保存一个示例条目（包含 parameters）。
    """
    counts = Counter()
    examples = {}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if not fname.lower().endswith('.json'):
                continue
            path = os.path.join(dirpath, fname)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception as e:
                print(f"跳过无法解析的文件：{path}，错误：{e}")
                continue

            cfg_list = data.get('config')
            if not isinstance(cfg_list, list):
                continue

            for entry in cfg_list:
                t = entry.get('type')
                if not t:
                    continue
                counts[t] += 1
                # 只保留每种 type 的第一个示例
                if t not in examples:
                    examples[t] = entry

    return counts, examples

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="统计 JSON 文件中 config.type 的分布，并将结果写入 TXT 文件")
    parser.add_argument('root_dir', help="要扫描的根目录路径")
    parser.add_argument(
        '-o', '--output',
        default='config_type_stats.txt',
        help="输出结果的 TXT 文件路径（默认：config_type_stats.txt）")
    args = parser.parse_args()

    counts, examples = scan_config_types(args.root_dir)

    # 准备要写入的内容
    lines = []
    lines.append("=== config.type 统计结果 ===\n")
    for t, cnt in counts.most_common():
        lines.append(f"{t}: {cnt} 次\n")

    lines.append("\n=== 每种 type 的示例条目 ===\n")
    for t, example in examples.items():
        lines.append(f"\n-- {t} --\n")
        # 将示例 JSON 格式化成多行文本
        example_str = json.dumps(example, ensure_ascii=False, indent=2)
        lines.append(example_str + "\n")

    # 写入文件
    with open(args.output, 'w', encoding='utf-8') as fout:
        fout.writelines(lines)

    print(f"统计完成，结果已写入：{args.output}")



def main():
    # import argparse
    # parser = argparse.ArgumentParser(
    #     description="统计 JSON 文件中 config.type 的分布，并将结果写入 TXT 文件")
    # parser.add_argument('root_dir', help="要扫描的根目录路径")
    # parser.add_argument(
    #     '-o', '--output',
    #     default='config_type_stats.txt',
    #     help="输出结果的 TXT 文件路径（默认：config_type_stats.txt）")
    # args = parser.parse_args()

    # root_dir = args.root_dir
    root_dir = r"D:/data/winarena/examples"
    # output_dir = args.output
    output_file = r"D:/data/winarena/config_type_stats.txt"

    counts, examples = scan_config_types(root_dir)

    # 准备要写入的内容
    lines = []
    lines.append("=== config.type 统计结果 ===\n")
    for t, cnt in counts.most_common():
        lines.append(f"{t}: {cnt} 次\n")

    lines.append("\n=== 每种 type 的示例条目 ===\n")
    for t, example in examples.items():
        lines.append(f"\n-- {t} --\n")
        # 将示例 JSON 格式化成多行文本
        example_str = json.dumps(example, ensure_ascii=False, indent=2)
        lines.append(example_str + "\n")

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as fout:
        fout.writelines(lines)

    print(f"统计完成，结果已写入：{output_file}")

if __name__ == '__main__':
    main()
