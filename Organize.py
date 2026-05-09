import os
import sys
import re
import shutil
import unicodedata

# ------------------------------ 辅助函数 ------------------------------
def is_separator(c):
    """判断字符是否为分隔符（不属于Unicode字母类别）"""
    return not unicodedata.category(c).startswith('L')

def strip_trailing_episode_info(name):
    """
    去除末尾的集数、序号等冗余信息，例如：
    'Bloods ～淫落的血族 2～ 第1話'  ->  'Bloods ～淫落的血族'
    '風輪奸山 1'                      ->  '風輪奸山'
    '妹妹是辣妹真是可愛 2'            ->  '妹妹是辣妹真是可愛'
    """
    # 常见模式： 空格+数字+可选的波浪号  或  第X話/集/章/节/卷/回 等
    pattern_num_dash = re.compile(r'\s+\d+\s*[～~]?\s*$')
    pattern_episode = re.compile(r'\s*第\s*\d+\s*[話话集章节卷回]?\s*$')
    while True:
        new_name = pattern_num_dash.sub('', name).strip()
        new_name = pattern_episode.sub('', new_name).strip()
        if new_name == name:
            break
        name = new_name
    return name

def valid_common_prefix(stems):
    """
    返回 stems 的最长有效公共前缀。
    有效条件：对每个 stem，要么 stem 就是该前缀，
    要么前缀的最后一个字符是分隔符，或者前缀后的第一个字符是分隔符。
    """
    if not stems:
        return ''
    lcp = stems[0]
    for s in stems[1:]:
        while not s.startswith(lcp):
            lcp = lcp[:-1]
            if not lcp:
                return ''
    while lcp:
        ok = True
        for s in stems:
            if len(s) > len(lcp):
                next_char = s[len(lcp)]
                if not (is_separator(lcp[-1]) or is_separator(next_char)):
                    ok = False
                    break
        if ok:
            return lcp
        lcp = lcp[:-1]
    return ''

def sanitize_folder_name(name):
    """清理文件夹名：移除 Windows 非法字符，去除首尾空格与点"""
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    return name.strip('. ')

# ------------------------------ 主程序 ------------------------------
def main():
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"工作目录：{script_dir}")

    # 收集所有 mp4 文件（不区分大小写）
    all_files = [f for f in os.listdir('.')
                 if os.path.isfile(f) and f.lower().endswith('.mp4')]
    print(f"找到 {len(all_files)} 个 mp4 文件。")

    if not all_files:
        print("没有 mp4 文件，无需整理。")
        input("按 Enter 键退出...")
        return

    bracket_files = []   # (文件夹名, 文件名)
    normal_files = []    # 未带 [xxx] 前缀的文件名

    for f in all_files:
        # 如果以 [ 开头，提取第一个中括号内容作为文件夹名
        match = re.match(r'^\[([^\]]*)\]', f)
        if match:
            folder = match.group(1).strip()
            folder = sanitize_folder_name(folder)
            if folder:
                bracket_files.append((folder, f))
                continue
        normal_files.append(f)

    moved_count = 0

    # ---------- 处理 [作者名] 系列 ----------
    for folder, f in bracket_files:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, f)
        if os.path.exists(dest):
            name, ext = os.path.splitext(f)
            counter = 1
            while os.path.exists(os.path.join(folder, f"{name} ({counter}){ext}")):
                counter += 1
            new_f = f"{name} ({counter}){ext}"
            dest = os.path.join(folder, new_f)
            print(f"警告：{dest} 已存在，重命名为 {new_f}")
        shutil.move(f, dest)
        print(f"移动：{f}  ->  {folder}/")
        moved_count += 1

    # ---------- 处理普通文件：先尝试多文件分组 ----------
    if normal_files:
        stems_info = [(os.path.splitext(f)[0], f) for f in normal_files]
        stems_info.sort(key=lambda x: x[0])

        grouped_files = set()   # 记录已被分组的文件名
        groups = []             # (文件夹名, [文件名列表])

        i = 0
        while i < len(stems_info):
            group_stems = [stems_info[i][0]]
            group_files = [stems_info[i][1]]
            prefix = group_stems[0]
            j = i + 1
            while j < len(stems_info):
                candidate_stems = group_stems + [stems_info[j][0]]
                new_prefix = valid_common_prefix(candidate_stems)
                if new_prefix:
                    group_stems.append(stems_info[j][0])
                    group_files.append(stems_info[j][1])
                    prefix = new_prefix
                    j += 1
                else:
                    break
            # 至少两个文件才能成组
            if len(group_files) >= 2:
                # 对公共前缀再“瘦身”，去掉末尾很可能属于集数的部分
                clean_prefix = strip_trailing_episode_info(prefix)
                folder_name = sanitize_folder_name(clean_prefix)
                if not folder_name:
                    folder_name = "未分类"
                groups.append((folder_name, group_files))
                for gf in group_files:
                    grouped_files.add(gf)
                i = j
            else:
                i += 1

        # 移动分组文件
        for folder_name, files in groups:
            if not os.path.exists(folder_name):
                os.makedirs(folder_name, exist_ok=True)
            for f in files:
                dest = os.path.join(folder_name, f)
                if os.path.exists(dest):
                    name, ext = os.path.splitext(f)
                    counter = 1
                    while os.path.exists(os.path.join(folder_name, f"{name} ({counter}){ext}")):
                        counter += 1
                    new_f = f"{name} ({counter}){ext}"
                    dest = os.path.join(folder_name, new_f)
                    print(f"警告：{dest} 已存在，重命名为 {new_f}")
                shutil.move(f, dest)
                print(f"移动：{f}  ->  {folder_name}/")
                moved_count += 1

        # ---------- 处理剩余未分组的单个文件 ----------
        remaining_files = [f for f in normal_files if f not in grouped_files]
        # 按去除序号后的基础名称合并（例如多个剩余文件同属一个系列但没被分组逻辑识别）
        solo_groups = {}
        for f in remaining_files:
            stem = os.path.splitext(f)[0]
            base = strip_trailing_episode_info(stem)
            if not base:
                base = stem   # 极端情况，保留原名
            folder = sanitize_folder_name(base)
            if not folder:
                folder = "未分类"
            solo_groups.setdefault(folder, []).append(f)

        for folder_name, files in solo_groups.items():
            if not os.path.exists(folder_name):
                os.makedirs(folder_name, exist_ok=True)
            for f in files:
                dest = os.path.join(folder_name, f)
                if os.path.exists(dest):
                    name, ext = os.path.splitext(f)
                    counter = 1
                    while os.path.exists(os.path.join(folder_name, f"{name} ({counter}){ext}")):
                        counter += 1
                    new_f = f"{name} ({counter}){ext}"
                    dest = os.path.join(folder_name, new_f)
                    print(f"警告：{dest} 已存在，重命名为 {new_f}")
                shutil.move(f, dest)
                print(f"移动：{f}  ->  {folder_name}/")
                moved_count += 1

    print(f"\n整理完成！共移动 {moved_count} 个文件。")
    input("按 Enter 键退出...")

if __name__ == '__main__':
    main()