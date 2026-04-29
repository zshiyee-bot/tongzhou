"""抖音视频解析与下载模块。

职责:
- 判断链接是否属于抖音平台
- 解析抖音短视频的元信息（标题、作者、播放地址等）
- 下载无水印视频到本地
- 处理抖音 WAF 反爬验证

边界:
- 仅处理抖音域名下的链接，其他平台由 downloader 模块负责
- 基于公开 API 与分享页解析，无需 Cookie 和登录
- 解析流程：短链接重定向 → 提取 video_id → 公开 API / 分享页 → 无水印播放地址
"""

import base64
import json
import hashlib
import os
import re
import time
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests

logger = logging.getLogger("douyin")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.douyin.com/",
}

MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
        "Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}

_URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


def is_douyin_url(url: str) -> bool:
    """判断是否为抖音链接（支持从分享文本中自动提取）"""
    douyin_domains = [
        "douyin.com", "iesdouyin.com", "v.douyin.com",
        "www.douyin.com", "m.douyin.com",
    ]

    # 先尝试智能提取链接
    try:
        from app.utils.url_extractor import extract_video_url, identify_platform
        extracted_url = extract_video_url(url)
        platform = identify_platform(extracted_url)
        return platform == "douyin"
    except (ImportError, ValueError, Exception):
        # 如果提取失败，使用原有逻辑
        pass

    # 原有逻辑：直接检查 URL
    try:
        host = urlparse(url).netloc.lower()
        return any(d in host for d in douyin_domains)
    except Exception:
        return False


class DouyinParser:
    """抖音视频解析器，无需 Cookie。

    支持短链接重定向解析、公开 API 数据获取、分享页 HTML 解析、
    WAF 反爬验证自动处理。
    """

    API_URL = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/"

    def __init__(self, download_dir: Optional[str] = None):
        """初始化解析器。

        Args:
            download_dir: 下载文件存放目录路径，默认为 backend/downloads。
        """
        if download_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            download_dir = os.path.join(backend_dir, "downloads")
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.timeout = (10, 30)
        self.max_retries = 3

    def parse(self, url: str) -> dict:
        """解析抖音视频信息，返回与 yt-dlp 兼容的统一格式。

        Args:
            url: 抖音分享链接（支持短链接和长链接）。

        Returns:
            视频元信息字典，包含 id、title、formats、thumbnail 等字段。

        Raises:
            ValueError: 链接无效、解析失败或提取不到视频 ID 时抛出。
        """
        share_url = self._extract_url(url)
        resolved_url = self._resolve_redirect(share_url)
        video_id = self._extract_video_id(resolved_url)
        item_info = self._fetch_item_info(video_id, resolved_url)
        return self._build_result(item_info, video_id)

    def download(self, url: str, mode: str = "video") -> dict:
        """下载抖音视频到本地，返回文件路径。

        优先下载无水印版本，失败后自动尝试有水印版本作为兜底。

        Args:
            url: 抖音分享链接。
            mode: 下载模式，"video" 下载视频，"audio" 下载音频。

        Returns:
            包含 filepath、filename、title、ext 的字典。

        Raises:
            ValueError: 链接无效、解析失败或文件下载失败时抛出。
        """
        share_url = self._extract_url(url)
        resolved_url = self._resolve_redirect(share_url)
        video_id = self._extract_video_id(resolved_url)

        item_info = self._fetch_item_info(video_id, resolved_url)
        media_url = self._get_media_url(item_info, mode)

        title = item_info.get("desc") or f"douyin_{video_id}"
        safe_title = re.sub(r'[\\/*?:"<>|\n\r\t#@]', "_", title).strip("_. ")[:60]
        safe_title = re.sub(r'_+', '_', safe_title)
        if not safe_title:
            safe_title = f"douyin_{video_id}"

        ext = ".mp4" if mode == "video" else ".mp3"
        filename = f"{safe_title}{ext}"
        filepath = self.download_dir / filename

        # 先尝试无水印版本
        try:
            logger.info("[抖音下载] 尝试下载无水印版本...")
            self._download_file(media_url, filepath)
            logger.info("[抖音下载] 无水印版本下载成功")
        except Exception as e:
            # 无水印失败，尝试有水印版本作为兜底
            logger.warning(f"[抖音下载] 无水印版本失败: {e}")
            logger.info("[抖音下载] 尝试下载有水印版本作为兜底...")

            # 获取有水印地址（原始地址，不替换 playwm）
            play_urls = (
                item_info.get("video", {})
                .get("play_addr", {})
                .get("url_list", [])
            )
            if play_urls:
                watermark_url = play_urls[0]  # 原始地址（有水印）
                try:
                    self._download_file(watermark_url, filepath)
                    logger.info("[抖音下载] 有水印版本下载成功（兜底方案）")
                except Exception as e2:
                    # 有水印也失败，抛出错误
                    raise ValueError(f"无水印和有水印版本均下载失败。无水印错误: {e}，有水印错误: {e2}")
            else:
                # 没有播放地址，抛出原始错误
                raise

        return {
            "filepath": str(filepath),
            "filename": filename,
            "title": title,
            "ext": ext.lstrip("."),
        }

    def _extract_url(self, text: str) -> str:
        """从文本中提取第一个有效 URL。

        使用智能链接提取工具，支持从复杂的分享文本中提取真正的视频链接。

        Args:
            text: 可能包含 URL 的输入文本。

        Returns:
            清理后的 URL 字符串。

        Raises:
            ValueError: 未找到有效 URL 时抛出。
        """
        # 使用智能链接提取工具
        try:
            from app.utils.url_extractor import extract_video_url
            return extract_video_url(text)
        except (ImportError, ValueError, Exception):
            # 如果提取失败，回退到原有逻辑
            match = _URL_PATTERN.search(text)
            if not match:
                raise ValueError("未找到有效的抖音链接")
            candidate = match.group(0).strip().strip('"').strip("'")
            return candidate.rstrip(").,;!?")

    def _resolve_redirect(self, share_url: str) -> str:
        """解析短链接重定向，获取最终落地页 URL。

        支持指数退避重试，最多重试 max_retries 次。
        对于精选页链接（jingxuan），直接构造视频详情页 URL。

        Args:
            share_url: 抖音短链接。

        Returns:
            重定向后的完整 URL。

        Raises:
            ValueError: 所有重试均失败时抛出。
        """
        # 处理精选页链接：提取 modal_id 并构造标准视频 URL
        if "jingxuan" in share_url and "modal_id=" in share_url:
            parsed = urlparse(share_url)
            query = parse_qs(parsed.query)
            modal_id = query.get("modal_id", [None])[0]
            if modal_id:
                # 构造标准的视频详情页 URL
                return f"https://www.douyin.com/video/{modal_id}"

        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(
                    share_url, timeout=self.timeout,
                    allow_redirects=True, headers=DEFAULT_HEADERS,
                )
                resp.raise_for_status()
                return resp.url
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise ValueError(f"链接解析失败: {e}")
                time.sleep(1 * (2 ** attempt))
        raise ValueError("链接解析失败")

    def _extract_video_id(self, url: str) -> str:
        """从 URL 中提取视频 ID，支持多种参数名和路径格式。

        按优先级尝试查询参数（modal_id > item_ids > group_id > aweme_id），
        其次尝试路径匹配，最后回退到 URL 中的长数字串。

        Args:
            url: 已重定向的完整 URL。

        Returns:
            视频 ID 字符串（8-24 位数字）。

        Raises:
            ValueError: 所有方式均无法提取到有效 ID 时抛出。
        """
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        for key in ("modal_id", "item_ids", "group_id", "aweme_id"):
            values = query.get(key)
            if values:
                match = re.search(r"(\d{8,24})", values[0])
                if match:
                    return match.group(1)

        for pattern in (r"/video/(\d{8,24})", r"/note/(\d{8,24})", r"/(\d{8,24})(?:/|$)"):
            match = re.search(pattern, parsed.path)
            if match:
                return match.group(1)

        fallback = re.search(r"(\d{15,24})", url)
        if fallback:
            return fallback.group(1)

        raise ValueError("无法从链接中提取视频ID")

    def _fetch_item_info(self, video_id: str, resolved_url: str) -> dict:
        """获取视频元数据，优先公开 API，失败则解析分享页。

        Args:
            video_id: 视频 ID。
            resolved_url: 已重定向的完整 URL，分享页解析时使用。

        Returns:
            视频元数据字典，结构与 API 返回的 item 一致。

        Raises:
            ValueError: API 和分享页均无法获取数据时抛出。
        """
        try:
            return self._fetch_via_api(video_id)
        except Exception as e:
            logger.warning("公开API获取失败(%s)，尝试分享页解析", e)
            return self._fetch_via_share_page(video_id, resolved_url)

    def _fetch_via_api(self, video_id: str) -> dict:
        """通过公开 API 获取视频元数据。

        Args:
            video_id: 视频 ID。

        Returns:
            API 返回的第一个 item 数据字典。

        Raises:
            ValueError: API 返回空数据或请求失败时抛出。
        """
        params = {"item_ids": video_id}
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(
                    self.API_URL, params=params, timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("item_list") or []
                if items:
                    return items[0]
                raise ValueError("API 返回空数据")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1 * (2 ** attempt))
        raise ValueError("API 请求失败")

    def _fetch_via_share_page(self, video_id: str, resolved_url: str) -> dict:
        """从分享页面 HTML 中解析视频信息（公开 API 失败时的降级方案）。

        解析页面中的 window._ROUTER_DATA JSON 数据，若遇到 WAF 验证则自动处理。

        Args:
            video_id: 视频 ID，用于构建备用分享页 URL。
            resolved_url: 已重定向的 URL。

        Returns:
            视频元数据字典。

        Raises:
            ValueError: 无法从分享页提取数据时抛出。
        """
        parsed = urlparse(resolved_url)
        if "iesdouyin.com" in (parsed.netloc or ""):
            share_url = resolved_url
        else:
            share_url = f"https://www.iesdouyin.com/share/video/{video_id}/"

        resp = self.session.get(share_url, headers=MOBILE_HEADERS, timeout=self.timeout)
        resp.raise_for_status()
        html = resp.text or ""

        if "Please wait..." in html and "wci=" in html and "cs=" in html:
            html = self._solve_waf_and_retry(html, share_url)

        router_data = self._extract_router_data(html)
        if not router_data:
            raise ValueError("无法从分享页提取数据")

        loader_data = router_data.get("loaderData", {})
        for node in loader_data.values():
            if not isinstance(node, dict):
                continue
            video_info_res = node.get("videoInfoRes", {})
            if not isinstance(video_info_res, dict):
                continue
            item_list = video_info_res.get("item_list", [])
            if item_list and isinstance(item_list[0], dict):
                return item_list[0]

        raise ValueError("分享页中未找到视频信息")

    def _solve_waf_and_retry(self, html: str, page_url: str) -> str:
        """解决抖音 WAF 反爬验证（SHA-256 挑战-响应）。

        解析挑战参数，暴力枚举 0~1000000 找到满足条件的 nonce，
        设置 Cookie 后重新请求页面。

        Args:
            html: 包含 WAF 挑战的页面 HTML。
            page_url: 当前页面 URL，用于设置 Cookie 域名。

        Returns:
            重新请求后的页面 HTML，或原始 HTML（挑战无法解决时）。
        """
        match = re.search(r'wci="([^"]+)"\s*,\s*cs="([^"]+)"', html)
        if not match:
            return html

        cookie_name, challenge_blob = match.groups()
        try:
            decoded = self._decode_b64(challenge_blob).decode("utf-8")
            challenge_data = json.loads(decoded)
            prefix = self._decode_b64(challenge_data["v"]["a"])
            expected = self._decode_b64(challenge_data["v"]["c"]).hex()
        except (KeyError, ValueError):
            return html

        for candidate in range(1_000_001):
            digest = hashlib.sha256(prefix + str(candidate).encode()).hexdigest()
            if digest == expected:
                challenge_data["d"] = base64.b64encode(
                    str(candidate).encode()
                ).decode()
                cookie_val = base64.b64encode(
                    json.dumps(challenge_data, separators=(",", ":")).encode()
                ).decode()
                domain = urlparse(page_url).hostname or "www.iesdouyin.com"
                self.session.cookies.set(cookie_name, cookie_val, domain=domain, path="/")
                resp = self.session.get(page_url, headers=MOBILE_HEADERS, timeout=self.timeout)
                return resp.text or ""

        return html

    @staticmethod
    def _decode_b64(value: str) -> bytes:
        """解码 URL 安全的 Base64 字符串。

        Args:
            value: Base64 编码的字符串（可能使用 - 和 _ 代替 + 和 /）。

        Returns:
            解码后的字节数据。
        """
        normalized = value.replace("-", "+").replace("_", "/")
        normalized += "=" * (-len(normalized) % 4)
        return base64.b64decode(normalized)

    def _extract_router_data(self, html: str) -> dict:
        """从 HTML 中提取 window._ROUTER_DATA JSON 数据。

        通过括号深度匹配定位 JSON 边界，避免正则匹配嵌套结构的不确定性。

        Args:
            html: 页面 HTML 字符串。

        Returns:
            解析后的字典，提取失败时返回空字典。
        """
        marker = "window._ROUTER_DATA = "
        start = html.find(marker)
        if start < 0:
            return {}

        idx = start + len(marker)
        while idx < len(html) and html[idx].isspace():
            idx += 1
        if idx >= len(html) or html[idx] != "{":
            return {}

        depth = 0
        in_str = False
        escaped = False
        for cursor in range(idx, len(html)):
            ch = html[cursor]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[idx: cursor + 1])
                    except ValueError:
                        return {}
        return {}

    def _get_media_url(self, item_info: dict, mode: str = "video") -> str:
        """提取播放地址（默认无水印）。

        视频模式将 playwm 替换为 play 以获取无水印版本；
        音频模式提取背景音乐播放地址。

        Args:
            item_info: 视频元数据字典。
            mode: "video" 提取视频地址，"audio" 提取音频地址。

        Returns:
            媒体文件的直接下载 URL。

        Raises:
            ValueError: 未找到对应模式的播放地址或不支持的模式时抛出。
        """
        if mode == "video":
            play_urls = (
                item_info.get("video", {})
                .get("play_addr", {})
                .get("url_list", [])
            )
            if not play_urls:
                raise ValueError("未找到视频播放地址")
            return play_urls[0].replace("playwm", "play")

        if mode == "audio":
            music = item_info.get("music", {})
            audio_urls = music.get("play_url", {}).get("url_list", [])
            if not audio_urls:
                raise ValueError("未找到音频地址")
            return audio_urls[0]

        raise ValueError(f"不支持的模式: {mode}")

    def _build_result(self, item_info: dict, video_id: str) -> dict:
        """构建与 yt-dlp 解析结果兼容的统一格式。

        Args:
            item_info: 视频元数据字典。
            video_id: 视频 ID。

        Returns:
            标准化的视频信息字典，包含 id、title、formats、thumbnail 等字段。
        """
        # 调试：打印所有可用字段
        print(f"[抖音] item_info 所有字段: {list(item_info.keys())}")
        print(f"[抖音] 时间相关字段: create_time={item_info.get('create_time')}, createTime={item_info.get('createTime')}")

        title = item_info.get("desc") or f"抖音视频_{video_id}"
        author = item_info.get("author", {})
        stats = item_info.get("statistics", {})

        # 调试：打印 statistics 的所有字段
        print(f"[抖音] statistics 字段: {stats}")

        video_info = item_info.get("video", {})
        play_urls = video_info.get("play_addr", {}).get("url_list", [])
        cover_urls = video_info.get("cover", {}).get("url_list", [])
        duration = video_info.get("duration", 0)
        duration_sec = duration // 1000 if duration > 1000 else duration

        # 提取创建时间（尝试多个可能的字段名）
        create_time = item_info.get("create_time") or item_info.get("createTime") or item_info.get("create_at") or 0
        upload_date = ""
        if create_time:
            try:
                from datetime import datetime
                dt = datetime.fromtimestamp(int(create_time))
                upload_date = dt.strftime("%Y%m%d")
                print(f"[抖音] 成功提取时间: {upload_date}")
            except Exception as e:
                print(f"[抖音] 时间转换失败: {e}")

        formats = []
        if play_urls:
            clean_url = play_urls[0].replace("playwm", "play")
            width = video_info.get("width", 0)
            height = video_info.get("height", 0)
            formats.append({
                "format_id": "douyin_nowm",
                "ext": "mp4",
                "resolution": f"{width}x{height}" if width and height else "原始",
                "height": height or 720,
                "filesize": None,
                "filesize_approx": None,
                "vcodec": "h264",
                "acodec": "aac",
                "has_audio": True,
                "label": f"无水印 MP4 ({height}p)" if height else "无水印 MP4 (原始画质)",
                "_direct_url": clean_url,
            })

        return {
            "id": video_id,
            "title": title,
            "thumbnail": cover_urls[0] if cover_urls else "",
            "duration": duration_sec,
            "duration_string": self._fmt_duration(duration_sec),
            "uploader": author.get("nickname", "抖音用户"),
            "platform": "抖音",
            "view_count": stats.get("play_count", 0) or 0,  # 播放量/曝光量
            "like_count": stats.get("digg_count", 0),  # 点赞数
            "comment_count": stats.get("comment_count", 0),  # 评论数
            "share_count": stats.get("share_count", 0),  # 分享数
            "collect_count": stats.get("collect_count", 0),  # 收藏数
            "upload_date": upload_date,
            "description": title[:200],
            "formats": formats,
            "subtitles": [],
            "automatic_captions": [],
        }

    @staticmethod
    def _fmt_duration(seconds: Optional[int]) -> str:
        """将秒数格式化为时长字符串。

        Args:
            seconds: 时长秒数，为 None 或 0 时返回 "00:00"。

        Returns:
            格式化后的时长，如 "1:30:05" 或 "05:30"。
        """
        if not seconds:
            return "00:00"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    def _download_file(self, url: str, filepath: Path, chunk_size: int = 64 * 1024):
        """下载文件到本地，支持断点重试和临时文件写入。

        下载完成后原子性地将 .part 文件重命名为目标文件名。

        Args:
            url: 文件下载 URL。
            filepath: 目标文件路径。
            chunk_size: 下载块大小（字节），默认 64KB。

        Raises:
            ValueError: 所有重试均失败时抛出。
        """
        # 为视频下载添加额外的请求头
        download_headers = {
            "User-Agent": DEFAULT_HEADERS["User-Agent"],
            "Referer": "https://www.douyin.com/",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Range": "bytes=0-",
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(
                    url, stream=True, timeout=self.timeout, allow_redirects=True,
                    headers=download_headers,
                )
                resp.raise_for_status()

                temp_path = filepath.with_suffix(filepath.suffix + ".part")
                with temp_path.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                temp_path.replace(filepath)
                return
            except Exception as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    # 所有重试都失败，抛出错误并附带提示
                    error_msg = f"抖音视频下载失败: {e}"
                    if "404" in str(e) or "Not Found" in str(e):
                        error_msg += "\n\n提示：此视频可能使用了特殊保护机制，建议：\n1. 重新复制最新的分享链接\n2. 确认视频在抖音App中可以正常播放\n3. 某些商业推广视频可能无法下载"
                    raise ValueError(error_msg)
                time.sleep(1 * (2 ** attempt))


douyin_parser = DouyinParser(download_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "downloads"))