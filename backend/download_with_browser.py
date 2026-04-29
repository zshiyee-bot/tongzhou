"""使用 Playwright 下载抖音视频（支持新版页面）"""

from playwright.sync_api import sync_playwright
import time

def download_douyin_with_browser(url: str, output_path: str):
    """使用浏览器下载抖音视频"""

    print(f"[浏览器] 启动浏览器...")

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        # 访问页面
        print(f"[浏览器] 访问页面: {url}")
        page.goto(url, wait_until="networkidle")

        # 等待视频加载
        print(f"[浏览器] 等待视频加载...")
        page.wait_for_selector("video", timeout=10000)

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

        if video_url:
            print(f"[浏览器] ✓ 找到视频地址: {video_url[:100]}...")

            # 下载视频
            import requests
            print(f"[浏览器] 开始下载...")
            resp = requests.get(video_url, stream=True, headers={
                "Referer": "https://www.douyin.com/",
                "User-Agent": "Mozilla/5.0"
            })

            with open(output_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"[浏览器] ✓ 下载完成: {output_path}")
            browser.close()
            return True
        else:
            print(f"[浏览器] ✗ 未找到视频地址")
            browser.close()
            return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("用法: python download_with_browser.py <视频URL> <输出文件>")
        sys.exit(1)

    url = sys.argv[1]
    output = sys.argv[2]

    success = download_douyin_with_browser(url, output)
    if success:
        print("\n✅ 下载成功！")
    else:
        print("\n❌ 下载失败")
