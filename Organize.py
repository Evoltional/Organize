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

def move_file_safe(src, dst_dir):
    """
    将文件 src 移动到目录 dst_dir 中，若目标已存在则自动添加编号。
    返回实际使用的目标路径（仅用于日志）。
    """
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
    name, ext = os.path.splitext(src)
    dest = os.path.join(dst_dir, src)
    if os.path.exists(dest):
        counter = 1
        while os.path.exists(os.path.join(dst_dir, f"{name} ({counter}){ext}")):
            counter += 1
        new_name = f"{name} ({counter}){ext}"
        dest = os.path.join(dst_dir, new_name)
        print(f"警告：{dest} 已存在，重命名为 {new_name}")
    shutil.move(src, dest)
    return dest

# ------------------------------ 主程序 ------------------------------
def main():
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"工作目录：{script_dir}")

    # 收集当前目录下的所有文件（不包含子目录）
    all_files = [f for f in os.listdir('.') if os.path.isfile(f)]
    print(f"找到 {len(all_files)} 个文件。")

    if not all_files:
        print("没有文件，无需整理。")
        input("按 Enter 键退出...")
        return

    # ========== 第一步：提取带 [xxx] 前缀的文件（不区分类型） ==========
    bracket_files = []   # (文件夹名, 文件名)
    normal_files = []

    for f in all_files:
        match = re.match(r'^\[([^\]]*)\]', f)
        if match:
            folder = match.group(1).strip()
            folder = sanitize_folder_name(folder)
            if folder:
                bracket_files.append((folder, f))
                continue
        normal_files.append(f)

    moved_count = 0

    # ---------- 移动所有带 [作者名] 的文件 ----------
    for folder, f in bracket_files:
        dest = move_file_safe(f, folder)
        print(f"移动：{f}  ->  {folder}/")
        moved_count += 1

    # ========== 第二步：将剩余文件按类型分离 ==========
    # 视频扩展名（仅处理 .mp4，如需其他格式可在此扩展）
    VIDEO_EXTS = {'.mp4'}
    # 压缩文件扩展名（包含常见分卷）
    COMPRESS_EXTS = {
        '.zip', '.rar', '.7z'
    }
    # 添加 .z01 ~ .z99
    COMPRESS_EXTS.update({'.z{:02d}'.format(i) for i in range(1, 100)})
    # 可选：RAR 分卷
    COMPRESS_EXTS.update({'.part{:d}.rar'.format(i) for i in range(1, 100)})

    video_files = []
    compress_files = []
    other_files = []  # 目前暂不处理

    for f in normal_files:
        _, ext = os.path.splitext(f)
        ext_lower = ext.lower()
        if ext_lower in VIDEO_EXTS:
            video_files.append(f)
        elif ext_lower in COMPRESS_EXTS:
            compress_files.append(f)
        else:
            other_files.append(f)

    # 可选：提示未处理的文件
    if other_files:
        print(f"跳过 {len(other_files)} 个非视频/非压缩文件：{other_files}")

    # ========== 第三步：处理视频文件（原有逻辑） ==========
    if video_files:
        stems_info = [(os.path.splitext(f)[0], f) for f in video_files]
        stems_info.sort(key=lambda x: x[0])

        grouped_files = set()   # 已被分组的文件名
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

        # 移动分组视频文件
        for folder_name, files in groups:
            for f in files:
                move_file_safe(f, folder_name)
                print(f"移动：{f}  ->  {folder_name}/")
                moved_count += 1

        # 处理剩余未分组的单个视频文件（按去除序号后的基础名合并）
        remaining_video = [f for f in video_files if f not in grouped_files]
        solo_groups = {}
        for f in remaining_video:
            stem = os.path.splitext(f)[0]
            base = strip_trailing_episode_info(stem)
            if not base:
                base = stem
            folder = sanitize_folder_name(base)
            if not folder:
                folder = "未分类"
            solo_groups.setdefault(folder, []).append(f)

        for folder_name, files in solo_groups.items():
            for f in files:
                move_file_safe(f, folder_name)
                print(f"移动：{f}  ->  {folder_name}/")
                moved_count += 1

    # ========== 第四步：处理压缩文件（新规则） ==========
    if compress_files:
        # 按基本文件名（去除扩展名）分组
        stem_groups = {}
        for f in compress_files:
            stem = os.path.splitext(f)[0]
            # 针对多段扩展名（如 .part1.rar）的特殊处理：再次去除可能的前导数字扩展
            # 例如 "archive.part1" → stem="archive.part1"，再用一次 splitext 得到 "archive"
            # 但题目要求“完全相同文件名”，我们保留原始 stem 即可。若需合并 .part1.rar 和 .rar，可在此扩展。
            stem_groups.setdefault(stem, []).append(f)

        for stem, files in stem_groups.items():
            folder_name = sanitize_folder_name(stem)
            if not folder_name:
                folder_name = "未分类"
            for f in files:
                move_file_safe(f, folder_name)
                print(f"移动：{f}  ->  {folder_name}/")
                moved_count += 1

    print(f"\n整理完成！共移动 {moved_count} 个文件。")
    input("按 Enter 键退出...")

if __name__ == '__main__':
    main()