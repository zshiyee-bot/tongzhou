import os
from contextlib import asynccontextmanager

from app.repositories.db import init_db as _init_db
from app.repositories.migrations import run_migrations


def cleanup_old_videos(download_dir: str, max_files: int = 100):
    """清理旧视频文件，只保留最新的 max_files 个文件。

    Args:
        download_dir: 下载目录路径
        max_files: 最多保留的文件数量，默认 100
    """
    if not os.path.exists(download_dir):
        return

    try:
        # 获取所有视频文件
        files = []
        for file_name in os.listdir(download_dir):
            file_path = os.path.join(download_dir, file_name)
            if os.path.isfile(file_path):
                # 获取文件的修改时间
                mtime = os.path.getmtime(file_path)
                files.append((file_path, mtime))

        # 如果文件数量超过限制
        if len(files) > max_files:
            # 按修改时间排序（旧的在前）
            files.sort(key=lambda x: x[1])

            # 删除最旧的文件
            files_to_delete = files[:len(files) - max_files]
            deleted_count = 0

            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError:
                    pass

            if deleted_count > 0:
                print(f"[清理] 已删除 {deleted_count} 个旧视频文件，保留最新的 {max_files} 个")

    except Exception as e:
        print(f"[清理] 清理视频文件时出错: {e}")


@asynccontextmanager
async def lifespan(app):
    # 初始化数据库表结构
    _init_db()

    # 执行数据库迁移
    run_migrations()

    # 启动时清理旧视频，保留最新的 100 个
    download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "downloads")
    download_dir = os.path.abspath(download_dir)
    cleanup_old_videos(download_dir, max_files=100)

    # 清理压缩视频，保留最新的 1000 个
    compressed_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "compressed")
    compressed_dir = os.path.abspath(compressed_dir)
    cleanup_old_videos(compressed_dir, max_files=1000)

    yield

    # 关闭时也清理一次，确保不超过限制
    cleanup_old_videos(download_dir, max_files=100)
    cleanup_old_videos(compressed_dir, max_files=1000)