import os
import shutil
import re


def extract_author(filename):
    """从文件名中提取作者名（方括号内的部分）"""
    match = re.search(r'\[([^\[\]]+)]', filename)
    return match.group(1) if match else None


def find_common_prefix(str_list):
    """查找字符串列表中最长共同前缀"""
    if not str_list:
        return ""
    prefix = str_list[0]
    for s in str_list[1:]:
        while not s.startswith(prefix) and prefix:
            prefix = prefix[:-1]
        if not prefix:
            break
    return prefix


def clean_folder_name(name):
    """清理文件夹名称，保留方括号内的作者名"""
    # 先尝试提取作者名
    author = extract_author(name)
    if author:
        return f"[{author}]"

    # 没有作者名时，移除版本号、集数等数字标识
    name = re.sub(r'\s*[0-9]+\s*$', '', name)

    # 再移除末尾的特殊字符和空格
    cleaned = re.sub(r'[ 　～~\-_.,;:!?()\[\]【】（）「」”“"\'*#@&$%^+=|\\<>/`]+$', '', name)

    # 如果清理后为空，则返回原始名称
    return cleaned.strip() if cleaned.strip() else name.strip()


def process_single_files(files):
    """处理单个文件，为每个文件创建独立文件夹"""
    moved_count = 0
    for file in files:
        # 获取文件名（不含扩展名）
        name_no_ext = os.path.splitext(file)[0]

        # 清理文件夹名
        folder_name = clean_folder_name(name_no_ext)

        # 避免文件夹名过长
        if len(folder_name) > 50:
            folder_name = folder_name[:47] + "..."

        try:
            # 创建文件夹
            os.makedirs(folder_name, exist_ok=True)

            # 移动文件
            shutil.move(file, os.path.join(folder_name, file))
            print(f"移动单个文件 '{file}' -> '{folder_name}/'")
            moved_count += 1
        except Exception as e:
            print(f"移动单个文件 '{file}' 失败: {e}")

    return moved_count


def main():
    # 获取当前目录下所有mp4文件
    mp4_files = [f for f in os.listdir()
                 if os.path.isfile(f) and f.lower().endswith('.mp4')]

    if not mp4_files:
        print("没有找到MP4文件")
        return

    # 按文件名排序
    mp4_files.sort()

    # 第一步：按作者分组
    author_groups = {}
    for file in mp4_files:
        author = extract_author(file)
        if author:
            group_key = f"[{author}]"
            if group_key not in author_groups:
                author_groups[group_key] = []
            author_groups[group_key].append(file)

    # 第二步：处理非作者分组的文件（使用共同前缀策略）
    non_author_files = [f for f in mp4_files if not extract_author(f)]
    prefix_groups = {}
    moved_set = set()  # 跟踪已移动的文件

    for file in non_author_files:
        name_no_ext = os.path.splitext(file)[0]

        # 寻找最佳匹配组
        best_match = None
        max_common = 0

        for key in list(prefix_groups.keys()):
            common = os.path.commonprefix([key, name_no_ext])
            # 要求共同部分至少2个字符
            if len(common) > max_common and len(common) >= 2:
                max_common = len(common)
                best_match = key

        # 找到匹配组则加入，否则创建新组
        if best_match:
            prefix_groups[best_match].append(file)
        else:
            prefix_groups[name_no_ext] = [file]

    # 合并所有分组
    all_groups = {**author_groups, **prefix_groups}

    # 创建文件夹并移动分组文件
    group_moved = 0
    folder_count = 0
    for key, files in list(all_groups.items()):
        # 作者分组直接使用作者名作为文件夹名
        if key in author_groups:
            folder_name = key
        else:
            # 计算组内所有文件名的共同前缀
            common_prefix = find_common_prefix([os.path.splitext(f)[0] for f in files])
            if not common_prefix:
                continue
            # 清理文件夹名
            folder_name = clean_folder_name(common_prefix)
            if not folder_name:
                continue

        # 避免文件夹名过长
        if len(folder_name) > 50:
            folder_name = folder_name[:47] + "..."

        # 创建文件夹
        try:
            os.makedirs(folder_name, exist_ok=True)
            folder_count += 1
        except OSError as e:
            print(f"创建文件夹 '{folder_name}' 失败: {e}")
            continue

        # 移动文件
        for file in files:
            try:
                shutil.move(file, os.path.join(folder_name, file))  # type: ignore
                group_moved += 1
                moved_set.add(file)
                print(f"移动分组文件 '{file}' -> '{folder_name}/'")
            except Exception as e:
                print(f"移动文件 '{file}' 失败: {e}")

    # 处理单个文件（未被分组的文件）
    single_files = [f for f in mp4_files if f not in moved_set]
    single_moved = process_single_files(single_files)

    print(f"\n处理完成! 共移动 {group_moved + single_moved} 个文件")
    print(f"- 创建 {folder_count} 个分组文件夹")
    print(f"- 创建 {len(single_files)} 个独立文件夹")
    print(f"- 移动 {group_moved} 个分组文件")
    print(f"- 移动 {single_moved} 个独立文件")


if __name__ == "__main__":
    main()