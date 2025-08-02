import os
import subprocess
import sys


def split_video(input_file):
    # 获取文件名（不含扩展名）和扩展名
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    ext = os.path.splitext(input_file)[1]

    # 创建输出文件夹
    output_dir = base_name
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 构建FFmpeg命令
    output_pattern = os.path.join(output_dir, f"{base_name}_part%03d{ext}")
    cmd = [
        "ffmpeg",
        "-i", input_file,
        "-c", "copy",  # 复制流不重新编码
        "-map", "0",  # 包含所有流
        "-segment_time", "00:05:00",  # 5分钟分段
        "-f", "segment",  # 使用分段格式
        "-reset_timestamps", "1",  # 重置时间戳
        "-force_key_frames", "expr:gte(t,n_forced*300)",  # 强制每5分钟关键帧
        output_pattern
    ]

    # 执行命令
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.PIPE)
        print(f"成功分割: {input_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"分割失败 {input_file}: {e.stderr.decode()}")
        return False


def main():
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 查找所有MP4文件
    mp4_files = [f for f in os.listdir(script_dir)
                 if f.lower().endswith('.mp4') and os.path.isfile(f)]

    if not mp4_files:
        print("未找到MP4文件")
        return

    # 处理所有MP4文件
    for file in mp4_files:
        split_video(file)

    print("处理完成！按Enter退出...")
    sys.stdin.read(1)


if __name__ == "__main__":
    main()