import os
import re
import shutil
import glob
from collections import defaultdict

def clean_folder_name(name):
    # 替换 Windows 非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip()
    # 去除结尾的点（Windows不允许文件和目录名以点结尾）
    while name.endswith('.'):
        name = name[:-1]
    if not name:
        name = "未分类"
    return name

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mp4_files = glob.glob(os.path.join(script_dir, "*.mp4"))
    if not mp4_files:
        print("当前文件夹没有找到任何 mp4 文件。")
        input("按回车键退出...")
        return

    brackets = defaultdict(list)
    others = []

    # 分离方括号开头的文件
    for f in mp4_files:
        name_no_ext = os.path.splitext(os.path.basename(f))[0]
        m = re.match(r'^\[([^\]]+)\]', name_no_ext)
        if m:
            folder = m.group(1).strip()
            brackets[folder].append(f)
        else:
            others.append(f)

    # 对非方括号文件进行聚类
    def is_boundary(name, n):
        if n >= len(name):
            return True
        return not name[n].isalpha()

    n = len(others)
    if n > 0:
        names = [os.path.splitext(os.path.basename(p))[0] for p in others]
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        for i in range(n):
            for j in range(i + 1, n):
                ni, nj = names[i], names[j]
                lcp_len = 0
                min_len = min(len(ni), len(nj))
                while lcp_len < min_len and ni[lcp_len] == nj[lcp_len]:
                    lcp_len += 1
                if lcp_len == 0:
                    continue
                if is_boundary(ni, lcp_len) and is_boundary(nj, lcp_len):
                    union(i, j)

        groups = defaultdict(list)
        for i, p in enumerate(others):
            groups[find(i)].append(p)

        cluster_folders = defaultdict(list)
        for comp in groups.values():
            if len(comp) == 1:
                name = os.path.splitext(os.path.basename(comp[0]))[0]
                digit_match = re.search(r'\d', name)
                if digit_match:
                    prefix = name[:digit_match.start()].rstrip()
                    folder = prefix if prefix else name
                else:
                    folder = name.strip()
            else:
                comp_names = [os.path.splitext(os.path.basename(p))[0] for p in comp]
                lcp = comp_names[0]
                for nxt in comp_names[1:]:
                    i = 0
                    while i < min(len(lcp), len(nxt)) and lcp[i] == nxt[i]:
                        i += 1
                    lcp = lcp[:i]
                    if not lcp:
                        break
                lcp = lcp.rstrip()
                folder = lcp if lcp else "未分类"
            cluster_folders[folder].extend(comp)

        all_folders = defaultdict(list)
        for folder, files in brackets.items():
            all_folders[folder].extend(files)
        for folder, files in cluster_folders.items():
            all_folders[folder].extend(files)
    else:
        all_folders = brackets

    # 移动文件
    for folder, files in all_folders.items():
        safe_folder = clean_folder_name(folder)  # 关键修复
        target_dir = os.path.join(script_dir, safe_folder)
        os.makedirs(target_dir, exist_ok=True)

        for src in files:
            dst = os.path.join(target_dir, os.path.basename(src))
            try:
                shutil.move(src, dst)
                print(f"移动: {os.path.basename(src)} → {safe_folder}/")
            except Exception as e:
                print(f"失败: {os.path.basename(src)} 未能移动，错误: {e}")

    print("\n整理完成！")
    input("按回车键退出...")

if __name__ == "__main__":
    main()