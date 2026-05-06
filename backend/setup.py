#!/usr/bin/env python
"""
一键部署脚本 - 安装所有依赖和浏览器

使用方法：
    python setup.py

功能：
1. 安装 Python 依赖包（requirements.txt）
2. 下载 static-ffmpeg（视频压缩）
3. 安装 Playwright Chromium（浏览器下载插件）
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """运行命令并显示进度"""
    print(f"\n{'='*60}")
    print(f"📦 {description}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=False
        )
        print(f"✅ {description} - 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - 失败: {e}")
        return False


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║                  视频分析系统 - 一键部署                    ║
║                                                            ║
║  这个脚本会自动安装：                                        ║
║  1. Python 依赖包                                          ║
║  2. FFmpeg（视频压缩）                                      ║
║  3. Playwright Chromium（浏览器下载插件）                   ║
║                                                            ║
║  预计耗时：5-10分钟（取决于网络速度）                        ║
╚════════════════════════════════════════════════════════════╝
    """)

    input("按 Enter 键开始安装...")

    # 1. 安装 Python 依赖
    success = run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "安装 Python 依赖包"
    )
    if not success:
        print("\n⚠️  依赖安装失败，请检查网络连接或 requirements.txt 文件")
        return False

    # 2. 下载 FFmpeg（通过 static-ffmpeg 包自动下载）
    print(f"\n{'='*60}")
    print("📦 FFmpeg 会在首次使用时自动下载")
    print(f"{'='*60}")

    # 3. 安装 Playwright Chromium
    success = run_command(
        f"{sys.executable} -m playwright install chromium",
        "安装 Playwright Chromium 浏览器（约150MB）"
    )
    if not success:
        print("\n⚠️  Chromium 安装失败，但不影响基本功能")
        print("   浏览器下载插件会在首次使用时自动安装")

    print(f"\n{'='*60}")
    print("🎉 部署完成！")
    print(f"{'='*60}")
    print("\n启动服务：")
    print("  # 开发环境（带热重载）")
    print("  python -m uvicorn app.main:app --host 0.0.0.0 --port 1018 --reload")
    print("\n  # 生产环境（推荐使用 gunicorn）")
    print("  pip install gunicorn")
    print("  gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:1018")
    print("\n访问地址：")
    print("  前端：http://localhost:1018")
    print("  管理后台：http://localhost:1018/admin")
    print()

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  安装已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 安装失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
