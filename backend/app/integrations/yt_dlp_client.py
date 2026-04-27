"""yt-dlp 通用视频下载封装模块。

职责:
- 通过 yt-dlp 解析视频元信息（标题、格式列表、字幕等）
- 下载视频到服务器临时目录
- 获取视频直链 URL

边界:
- 抖音平台视频由 douyin 模块单独处理，本模块不涉及
- ffmpeg 路径自动检测，缺失时降级为 best 格式下载（无音画合并）
- 下载文件存放于临时目录，由应用生命周期管理清理
"""

import os
import re
import shutil
import yt_dlp
from typing import Optional


def _find_ffmpeg_path() -> Optional[str]:
    """查找 ffmpeg 可执行文件路径。

    优先使用系统 PATH 中的 ffmpeg，其次尝试 static_ffmpeg 包。

    Returns:
        ffmpeg 所在目录的路径，未找到时返回 None。
    """
    if shutil.which("ffmpeg"):
        return os.path.dirname(shutil.which("ffmpeg"))
    try:
        import static_ffmpeg
        paths = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
        return os.path.dirname(paths[0])
    except Exception:
        return None


class VideoDownloader:
    """yt-dlp 封装层，提供视频解析、下载、直链获取能力。"""

    DOWNLOAD_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "downloads"
    )

    def __init__(self):
        """初始化下载器，创建临时目录并检测 ffmpeg 可用性。"""
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        self.ffmpeg_path = _find_ffmpeg_path()
        self.has_ffmpeg = self.ffmpeg_path is not None

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """移除文件名中的非法字符，防止路径注入。

        Args:
            name: 原始文件名。

        Returns:
            替换非法字符后的安全文件名。
        """
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    @staticmethod
    def _format_filesize(size: Optional[int]) -> str:
        """将字节数格式化为人类可读的大小标签。

        Args:
            size: 文件大小（字节），为 None 或 0 时返回"未知大小"。

        Returns:
            格式化后的字符串，如 "1.5MB"、"2.00GB"。
        """
        if not size:
            return "未知大小"
        if size < 1024 * 1024:
            return f"{size / 1024:.0f}KB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.2f}GB"

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        """将秒数格式化为时长字符串。

        Args:
            seconds: 时长秒数，为 None 或 0 时返回 "00:00"。

        Returns:
            格式化后的时长，如 "1:30:05" 或 "05:30"。
        """
        if not seconds:
            return "00:00"
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def parse_video(self, url: str) -> dict:
        """解析视频元信息，不下载文件。

        Args:
            url: 视频页面 URL（支持从复杂分享文本中自动提取链接）。

        Returns:
            视频元信息字典，包含 id、title、thumbnail、duration、formats 等字段。

        Raises:
            ValueError: yt-dlp 无法解析该链接时抛出。
        """
        # 智能提取视频链接（支持从复杂的分享文本中提取）
        try:
            from app.utils.url_extractor import extract_video_url
            url = extract_video_url(url)
        except (ImportError, ValueError):
            # 如果提取失败，使用原始 URL
            pass

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
            # 添加更强的反爬虫绕过
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            },
            # 添加 extractor 参数
            "extractor_args": {
                "bilibili": {
                    "api_host": "api.bilibili.com",
                }
            },
        }

        # 检查 B站专用 cookies 文件
        cookies_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "bilibili_cookies.txt")
        if os.path.exists(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("无法解析该链接")

        formats = self._extract_formats(info)
        platform = info.get("extractor", info.get("extractor_key", "Unknown"))

        return {
            "id": info.get("id", ""),
            "title": info.get("title", "未知标题"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "duration_string": self._format_duration(info.get("duration")),
            "uploader": info.get("uploader", info.get("channel", "未知")),
            "platform": platform,
            "view_count": info.get("view_count"),
            "upload_date": info.get("upload_date", ""),
            "description": (info.get("description") or "")[:200],
            "formats": formats,
            "subtitles": list(info.get("subtitles", {}).keys()),
            "automatic_captions": list(info.get("automatic_captions", {}).keys())[:5],
        }

    def _extract_formats(self, info: dict) -> list:
        """从 yt-dlp info 中提取并整理可用格式列表。

        过滤纯音频格式，按分辨率降序排列，最多返回 15 条。
        当所有格式都不含音频时，自动插入一条合并音视频的推荐格式。

        Args:
            info: yt-dlp extract_info 返回的原始信息字典。

        Returns:
            格式信息字典列表，每个包含 format_id、resolution、label 等字段。
        """
        raw_formats = info.get("formats", [])
        if not raw_formats:
            return []

        seen = set()
        results = []

        for f in raw_formats:
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            ext = f.get("ext", "mp4")

            has_video = vcodec and vcodec != "none"
            has_audio = acodec and acodec != "none"

            if not has_video:
                continue

            resolution = f"{f.get('width', '?')}x{height}" if height else "未知"
            filesize = f.get("filesize") or f.get("filesize_approx")
            size_label = self._format_filesize(filesize)

            if has_audio:
                label = f"{height}p {ext.upper()} ({size_label})"
                key = (height, ext, "av")
            else:
                label = f"{height}p {ext.upper()} (仅视频, {size_label})"
                key = (height, ext, "v")

            if key in seen:
                continue
            seen.add(key)

            results.append({
                "format_id": f.get("format_id", ""),
                "ext": ext,
                "resolution": resolution,
                "height": height or 0,
                "filesize": filesize,
                "filesize_approx": filesize,
                "vcodec": vcodec,
                "acodec": acodec if has_audio else None,
                "has_audio": has_audio,
                "label": label,
            })

        results.sort(key=lambda x: x["height"], reverse=True)

        if not any(r["has_audio"] for r in results) and results:
            best_video = results[0]
            merged = {
                **best_video,
                "format_id": f"bestvideo+bestaudio/best",
                "label": f"{best_video['height']}p 最佳 (视频+音频合并)",
                "has_audio": True,
                "acodec": "merged",
            }
            results.insert(0, merged)

        return results[:15]

    def download_video(self, url: str, format_id: str) -> dict:
        """下载视频到服务器临时目录，返回文件路径和元数据。

        当 ffmpeg 不可用且格式选择器含"+"时，降级为 best 格式。

        Args:
            url: 视频页面 URL。
            format_id: yt-dlp 格式选择器，如 "bestvideo+bestaudio/best"。

        Returns:
            包含 filepath、filename、title、ext 的字典。

        Raises:
            ValueError: 下载失败时抛出。
        """
        if not self.has_ffmpeg and "+" in format_id:
            format_id = "best"

        ydl_opts = {
            "format": format_id,
            "outtmpl": os.path.join(self.DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            # 添加请求头绕过反爬虫
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.bilibili.com/",
            },
        }

        if self.has_ffmpeg:
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path
            ydl_opts["merge_output_format"] = "mp4"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            raise ValueError("下载失败")

        title = self._sanitize_filename(info.get("title", "video"))
        ext = info.get("ext", "mp4")
        filename = f"{title}.{ext}"
        filepath = os.path.join(self.DOWNLOAD_DIR, filename)

        if not os.path.exists(filepath):
            prepared = ydl.prepare_filename(info)
            if os.path.exists(prepared):
                filepath = prepared
                filename = os.path.basename(prepared)
            else:
                for f in os.listdir(self.DOWNLOAD_DIR):
                    if title in f:
                        filepath = os.path.join(self.DOWNLOAD_DIR, f)
                        filename = f
                        break

        return {
            "filepath": filepath,
            "filename": filename,
            "title": info.get("title", "video"),
            "ext": ext,
        }

    def get_direct_url(self, url: str, format_id: str) -> dict:
        """获取视频直链 URL，不下载文件。

        部分平台的视频格式不支持直链获取。

        Args:
            url: 视频页面 URL。
            format_id: yt-dlp 格式选择器。

        Returns:
            包含 direct_url、ext、filesize、title 的字典。

        Raises:
            ValueError: 无法获取直链时抛出。
        """
        ydl_opts = {
            "format": format_id,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("无法获取直链")

        direct_url = info.get("url")
        if not direct_url:
            requested = info.get("requested_formats")
            if requested and len(requested) > 0:
                direct_url = requested[0].get("url")

        if not direct_url:
            raise ValueError("该视频不支持直链下载，请使用服务端下载模式")

        return {
            "direct_url": direct_url,
            "ext": info.get("ext", "mp4"),
            "filesize": info.get("filesize") or info.get("filesize_approx"),
            "title": info.get("title", "video"),
        }


downloader = VideoDownloader()