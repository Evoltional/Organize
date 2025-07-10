import os
import sys
import subprocess


def main():
    # 步骤1：获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 步骤2：获取所有视频文件（按文件名排序）
    video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.mpeg', '.mpg', '.m4v']
    video_files = sorted([
        f for f in os.listdir(current_dir)
        if os.path.isfile(os.path.join(current_dir, f)) and
           os.path.splitext(f)[1].lower() in video_exts
    ])

    if not video_files:
        input("未找到视频文件! 按Enter退出...")
        return

    # 步骤3：生成FFmpeg文件列表
    list_file = os.path.join(current_dir, "filelist.txt")
    try:
        with open(list_file, 'w', encoding='utf-8') as f:
            for video in video_files:
                # 处理特殊字符（转义单引号）
                video = video.replace("'", "'\\''")
                f.write(f"file '{video}'\n")
    except Exception as e:
        input(f"创建文件列表失败: {e}\n按Enter退出...")
        return

    # 步骤4：调用FFmpeg拼接视频
    output_file = os.path.join(current_dir, "output.mp4")
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_file,
        '-c', 'copy',  # 直接流复制（不重新编码）
        '-y',  # 覆盖输出文件
        output_file
    ]

    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        input(f"拼接失败:\n{error_msg}\n按Enter退出...")
    except FileNotFoundError:
        input("未找到FFmpeg! 请安装并添加到系统PATH\n按Enter退出...")
    finally:
        # 清理临时文件
        if os.path.exists(list_file):
            os.remove(list_file)

    input("\n操作完成! 输出文件: output.mp4\n按Enter退出...")


if __name__ == "__main__":
    main()