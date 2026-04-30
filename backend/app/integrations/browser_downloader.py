"""
浏览器下载插件 - 用于处理无法通过常规方法解析的特殊视频

这个模块作为fallback机制，当常规解析方法失败时自动启用。
使用 Playwright 模拟真实浏览器访问，适用于：
- JavaScript 渲染的新版页面
- 加密混淆的视频地址
- 需要浏览器环境才能获取的视频

部署说明：
- Chromium 浏览器会在首次使用时自动安装
- 如需手动安装：playwright install chromium
"""

import sys
import io
import os
import subprocess

# 修复Windows控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import requests
from typing import Optional
import time


def ensure_chromium_installed():
    """确保 Chromium 浏览器已安装，如果没有则自动安装"""
    try:
        # 检查 Chromium 是否已安装
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True  # 已安装
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    print("[浏览器下载器] 检测到 Chromium 未安装，正在自动安装...", flush=True)
                    print("[浏览器下载器] 这可能需要几分钟时间，请稍候...", flush=True)

                    # 自动安装 Chromium
                    result = subprocess.run(
                        [sys.executable, "-m", "playwright", "install", "chromium"],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )

                    if result.returncode == 0:
                        print("[浏览器下载器] ✓ Chromium 安装成功", flush=True)
                        return True
                    else:
                        print(f"[浏览器下载器] ✗ Chromium 安装失败: {result.stderr}", flush=True)
                        return False
                else:
                    raise
    except Exception as e:
        print(f"[浏览器下载器] ✗ 检查 Chromium 安装状态失败: {e}", flush=True)
        return False


class BrowserDownloader:
    """浏览器下载器 - 使用 Playwright 获取和下载视频"""

    def __init__(self, headless: bool = True, timeout: int = 60000):
        """
        初始化浏览器下载器

        Args:
            headless: 是否使用无头模式（服务器部署必须为True）
            timeout: 页面加载超时时间（毫秒，默认60秒）
        """
        self.headless = headless
        self.timeout = timeout

    def download(self, url: str, output_path: str) -> bool:
        """
        使用浏览器下载视频

        Args:
            url: 视频页面URL
            output_path: 输出文件路径

        Returns:
            bool: 下载是否成功
        """
        try:
            # 确保 Chromium 已安装
            if not ensure_chromium_installed():
                print(f"[浏览器下载器] ✗ Chromium 未安装且自动安装失败", flush=True)
                return False

            print(f"[浏览器下载器] 启动浏览器...", flush=True)

            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # 访问页面（使用更宽松的加载策略）
                print(f"[浏览器下载器] 访问页面: {url}", flush=True)
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                # 等待视频元素加载（增加超时时间）
                print(f"[浏览器下载器] 等待视频加载...", flush=True)
                page.wait_for_selector("video", timeout=20000)

                # 额外等待确保视频src加载完成
                time.sleep(2)

                # 提取视频地址
                video_url = page.evaluate("""
                    () => {
                        const video = document.querySelector('video');
                        if (video) {
                            return video.src || video.currentSrc;
                        }
                        return null;
                    }
                """)

                browser.close()

                if not video_url:
                    print(f"[浏览器下载器] X 未找到视频地址", flush=True)
                    return False

                print(f"[浏览器下载器] OK 找到视频地址: {video_url[:100]}...", flush=True)

                # 下载视频
                return self._download_video(video_url, output_path)

        except Exception as e:
            print(f"[浏览器下载器] X 失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def _download_video(self, video_url: str, output_path: str) -> bool:
        """
        下载视频文件

        Args:
            video_url: 视频直链
            output_path: 输出文件路径

        Returns:
            bool: 下载是否成功
        """
        try:
            print(f"[浏览器下载器] 开始下载...", flush=True)

            headers = {
                "Referer": "https://www.douyin.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            resp = requests.get(video_url, stream=True, headers=headers, timeout=120)
            resp.raise_for_status()

            # 写入文件
            downloaded_size = 0
            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

            print(f"[浏览器下载器] OK 下载完成: {output_path} ({downloaded_size / 1024 / 1024:.2f} MB)", flush=True)
            return True

        except Exception as e:
            print(f"[浏览器下载器] X 下载失败: {e}", flush=True)
            return False


# 单例模式 - 避免重复创建浏览器实例
_downloader_instance: Optional[BrowserDownloader] = None


def get_browser_downloader() -> BrowserDownloader:
    """获取浏览器下载器单例"""
    global _downloader_instance
    if _downloader_instance is None:
        _downloader_instance = BrowserDownloader(headless=True)
    return _downloader_instance


def download_with_browser(url: str, output_path: str) -> bool:
    """
    便捷函数：使用浏览器下载视频

    Args:
        url: 视频页面URL
        output_path: 输出文件路径

    Returns:
        bool: 下载是否成功

    Example:
        >>> success = download_with_browser(
        ...     "https://www.douyin.com/video/7460705823212326163",
        ...     "/path/to/output.mp4"
        ... )
    """
    downloader = get_browser_downloader()
    return downloader.download(url, output_path)


# 用于命令行测试
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python browser_downloader.py <视频URL> <输出文件>")
        print("示例: python browser_downloader.py https://www.douyin.com/video/7460705823212326163 output.mp4")
        sys.exit(1)

    video_url = sys.argv[1]
    output_file = sys.argv[2]

    print("=" * 80)
    print("浏览器下载器测试")
    print("=" * 80)

    success = download_with_browser(video_url, output_file)

    if success:
        print("\n✅ 下载成功！")
        sys.exit(0)
    else:
        print("\n❌ 下载失败")
        sys.exit(1)
