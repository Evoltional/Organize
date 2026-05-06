import os
import re
import shutil
from pathlib import Path
from collections import defaultdict

def main():
    # 工作目录：脚本所在的文件夹
    base_dir = Path(__file__).resolve().parent
    mp4_files = list(base_dir.glob("*.mp4"))
    if not mp4_files:
        print("没有找到任何 .mp4 文件，无事可做。")
        input("按回车键退出...")
        return

    # 分为“有方括号”和“无方括号”两类
    bracket_files = []
    normal_files = []
    for f in mp4_files:
        if f.stem.startswith('['):
            bracket_files.append(f)
        else:
            normal_files.append(f)

    # ---------- 处理带方括号的文件 ----------
    for f in bracket_files:
        match = re.match(r'^\[([^\]]+)\]', f.stem)
        if match:
            folder_name = match.group(1).strip()
        else:
            # 理论上不会走到这里，但以防万一
            folder_name = f.stem
        target_dir = base_dir / folder_name
        target_dir.mkdir(exist_ok=True)
        dest = target_dir / f.name
        if dest.exists():
            print(f"跳过（目标已存在）：{f.name} -> {target_dir}")
        else:
            shutil.move(str(f), str(dest))
            print(f"移动：{f.name} -> {target_dir}")

    # ---------- 处理没有方括号的文件 ----------
    if not normal_files:
        print("整理完成！")
        input("按回车键退出...")
        return

    # 为每个文件生成一个“候选系列名”
    file_candidates = []  # [(Path, candidate_str)]
    for f in normal_files:
        stem = f.stem
        # 模式1：末尾是 "分隔符 + 数字"  → 系列名是分隔符之前的部分
        # 模式2：末尾是 "第x话/話"        → 系列名是“第”之前的部分
        # 以上都不满足 → 用整个 stem 作为候选
        m1 = re.match(r'^(.+?)[\s\-_]+(\d+)$', stem)
        m2 = re.match(r'^(.+?)[\s\-_]*第(\d+)[話话]$', stem)
        if m1:
            cand = m1.group(1)
        elif m2:
            cand = m2.group(1)
        else:
            cand = stem
        file_candidates.append((f, cand))

    # 按候选系列名分组
    groups = defaultdict(list)
    for f, cand in file_candidates:
        groups[cand].append(f)

    # 合并可能属于同一系列的组（共享前缀且边界合理）
    # 先收集所有不同的候选系列名，按长度升序
    unique_candidates = sorted(groups.keys(), key=lambda x: len(x))
    merged = {}  # 最终确定的系列名 -> 文件列表
    used = set()

    for short in unique_candidates:
        if short in used:
            continue
        # 选择比 short 长且以 short 开头、且边界合理的候选
        same_series = [short]
        for long in unique_candidates:
            if long in used or long == short:
                continue
            if long.startswith(short):
                # short 必须是“完整的词”：长候选在 short 之后的首字符必须是分隔符或数字
                next_char = long[len(short)]
                if next_char.isdigit() or not next_char.isalnum():
                    same_series.append(long)
                    used.add(long)
        used.add(short)
        merged[short] = []
        for s in same_series:
            merged[short].extend(groups[s])

    # 开始移动文件
    for folder_name, file_list in merged.items():
        target_dir = base_dir / folder_name
        target_dir.mkdir(exist_ok=True)
        for f in file_list:
            dest = target_dir / f.name
            if dest.exists():
                print(f"跳过（目标已存在）：{f.name} -> {target_dir}")
            else:
                shutil.move(str(f), str(dest))
                print(f"移动：{f.name} -> {target_dir}")

    print("整理完成！")
    input("按回车键退出...")
    pause(20)

if __name__ == "__main__":
    main()