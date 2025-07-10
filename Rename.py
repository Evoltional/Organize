import os
import glob


def rename_mp4_files():
    # 获取当前目录所有MP4文件
    mp4_files = glob.glob('*.mp4')

    renamed_count = 0

    for old_name in mp4_files:
        # 检查文件名是否包含分隔符'@'
        if '@' in old_name:
            # 提取@符号前的部分作为新文件名
            new_name = old_name.split('@', 1)[0] + '.mp4'

            # 避免无意义重命名（如新老名字相同）
            if new_name != old_name:
                try:
                    os.rename(old_name, new_name)
                    print(f'重命名成功: "{old_name}" -> "{new_name}"')
                    renamed_count += 1
                except Exception as e:
                    print(f'错误: 无法重命名"{old_name}" - {str(e)}')

    print(f'\n操作完成! 共重命名 {renamed_count} 个文件')


if __name__ == "__main__":
    rename_mp4_files()