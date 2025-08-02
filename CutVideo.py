import os
import subprocess
import sys
import time


def time_to_seconds(minutes, seconds):
    """将分秒转换为秒数"""
    return minutes * 60 + seconds


def get_video_duration(input_file):
    """使用ffprobe获取视频时长（秒）"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        input_file
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        print(f"⚠️ 无法获取视频时长: {os.path.basename(input_file)}")
        return None


def trim_video(input_file, output_file, start_seconds, end_seconds):
    """使用ffmpeg裁剪视频"""
    # 确保结束时间不大于视频总时长
    duration = get_video_duration(input_file)
    if duration is None:
        return False

    # 计算实际结束时间
    actual_end = min(end_seconds, duration - 0.1)  # 避免超出范围

    if actual_end <= start_seconds:
        print(f"⚠️ 跳过：裁剪时间无效（总时长: {duration:.1f}秒）")
        return False

    # 计算裁剪段时长
    segment_duration = actual_end - start_seconds

    # 关键帧精确定位技术 - 解决音画不同步问题
    # 当起始时间接近0时使用精确编码模式
    if start_seconds < 0.5:
        print("🔧 使用精确编码模式保证音画同步")
        cmd = [
            'ffmpeg', '-y',
            '-i', input_file,
            '-ss', str(start_seconds),
            '-to', str(actual_end),
            '-c:v', 'libx264',  # 使用视频编码保证同步
            '-c:a', 'aac',  # 使用音频编码保证同步
            '-preset', 'fast',  # 平衡速度和质量
            '-crf', '23',  # 恒定质量模式
            '-avoid_negative_ts', 'make_zero',
            output_file
        ]
    else:
        # 常规快速裁剪模式
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_seconds),  # 关键帧定位
            '-i', input_file,
            '-to', str(segment_duration),
            '-c', 'copy',  # 直接复制流
            '-avoid_negative_ts', 'make_zero',
            '-noaccurate_seek',  # 优化关键帧查找
            output_file
        ]

    try:
        start_time = time.time()
        process = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process_time = time.time() - start_time

        # 检查输出文件是否存在
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            print("❌ 输出文件创建失败，请检查FFmpeg安装")
            return False

        print(f"✅ 成功处理 ({process_time:.1f}秒)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 裁剪失败: {e}")
        # 打印FFmpeg错误详情
        print("FFmpeg错误输出:")
        print(e.stderr.decode('utf-8') if e.stderr else "无错误详情")
        return False


def main():
    # 支持的文件格式
    valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg', '.ts']

    # 创建输出目录
    output_dir = "Cut"
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"📁 创建输出目录: {output_dir}")
        except OSError as e:
            print(f"❌ 无法创建输出目录: {e}")
            input("按回车退出...")
            return

    # 用户界面
    print("=" * 60)
    print("视频批量裁剪工具 (关键帧优化版)".center(60))
    print("=" * 60)
    print("说明:")
    print("- 请按格式输入时间（例如：片头2分30秒 → 输入 2 30）")
    print("- 处理后的视频将保存到 'Cut' 文件夹")
    print("- 支持格式: " + ", ".join(valid_extensions))
    print("- 自动处理音画同步问题")
    print("=" * 60)

    # 获取用户输入
    while True:
        try:
            input_str = input("▶ 片头时间（分 秒）: ").split()
            if len(input_str) != 2:
                raise ValueError("请输入两个数字（分 秒）")
            start_min, start_sec = map(int, input_str)

            input_str = input("⏹ 片尾时间（分 秒）: ").split()
            if len(input_str) != 2:
                raise ValueError("请输入两个数字（分 秒）")
            end_min, end_sec = map(int, input_str)

            if start_min < 0 or start_sec < 0 or end_min < 0 or end_sec < 0:
                print("❌ 时间不能为负数！请重新输入")
                continue

            break
        except ValueError as e:
            print(f"❌ 输入错误: {e}")

    # 转换时间
    start_cut = time_to_seconds(start_min, start_sec)
    end_cut = time_to_seconds(end_min, end_sec)

    # 收集当前目录视频文件
    video_files = [
        f for f in os.listdir('.')
        if os.path.isfile(f) and os.path.splitext(f)[1].lower() in valid_extensions
    ]

    if not video_files:
        print("\n🔍 未找到支持的视频文件！")
        input("按回车退出...")
        return

    print("\n找到以下视频文件:")
    for i, f in enumerate(video_files, 1):
        print(f"{i}. {f}")

    # 确认操作
    print(f"\n将裁剪: 片头 {start_min}分{start_sec}秒, 片尾 {end_min}分{end_sec}秒")
    print("注意：接近0秒的裁剪将自动使用精确模式保证音画同步")
    confirm = input("开始处理? (Y/N): ").strip().lower()
    if confirm != 'y':
        print("操作已取消")
        input("按回车退出...")
        return

    # 处理视频
    success_count = 0
    total_files = len(video_files)

    print("\n" + "=" * 60)
    print(f"开始处理 {total_files} 个视频...")
    print("=" * 60)

    for i, video in enumerate(video_files, 1):
        base, ext = os.path.splitext(video)
        output_file = os.path.join(output_dir, f"{base}_cut{ext}")

        print(f"\n[{i}/{total_files}] 处理: {video}")

        duration = get_video_duration(video)
        if duration is None:
            continue

        # 计算实际结束时间（视频总时长 - 片尾时长）
        actual_end = duration - end_cut

        if trim_video(video, output_file, start_cut, actual_end):
            success_count += 1

    # 结果统计
    print("\n" + "=" * 60)
    print(f"处理完成!".center(60))
    print("=" * 60)
    print(f"成功处理: {success_count}/{total_files} 个视频")
    print(f"输出目录: {os.path.abspath(output_dir)}")
    print("=" * 60)
    input("按回车退出...")


if __name__ == "__main__":
    # 检查FFmpeg是否可用
    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到FFmpeg，请先安装FFmpeg并添加到系统路径")
        input("按回车退出...")
        sys.exit(1)

    main()