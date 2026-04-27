"""智能链接提取工具。

职责:
- 从复杂的分享文本中提取真正的视频链接
- 支持多平台链接识别（抖音、B站、YouTube、小红书等）
- 自动过滤无关链接，优先返回视频平台链接
"""

import re
from typing import Optional, List
from urllib.parse import urlparse


# 各平台域名特征
PLATFORM_DOMAINS = {
    "douyin": [
        "douyin.com", "iesdouyin.com", "v.douyin.com",
        "www.douyin.com", "m.douyin.com"
    ],
    "bilibili": [
        "bilibili.com", "b23.tv", "www.bilibili.com",
        "m.bilibili.com", "space.bilibili.com"
    ],
    "youtube": [
        "youtube.com", "youtu.be", "www.youtube.com",
        "m.youtube.com", "youtube-nocookie.com"
    ],
    "xiaohongshu": [
        "xiaohongshu.com", "xhslink.com", "www.xiaohongshu.com"
    ],
    "kuaishou": [
        "kuaishou.com", "v.kuaishou.com", "www.kuaishou.com"
    ],
    "weibo": [
        "weibo.com", "weibo.cn", "m.weibo.cn", "video.weibo.com"
    ],
    "tiktok": [
        "tiktok.com", "www.tiktok.com", "vm.tiktok.com"
    ],
}


def extract_video_url(text: str) -> str:
    """从文本中智能提取视频链接。

    支持从复杂的分享文本中提取真正的视频链接，例如：
    - 抖音分享：包含多个链接，自动识别 v.douyin.com 或 www.douyin.com
    - B站分享：识别 b23.tv 短链接或 bilibili.com 长链接
    - 其他平台：自动识别并返回对应平台链接

    Args:
        text: 可能包含多个链接的分享文本

    Returns:
        提取出的视频链接

    Raises:
        ValueError: 未找到有效的视频链接时抛出

    Examples:
        >>> text = "9.28 12/14 ygo:/ l@C.Hv 今天是放假发工资的苦蛋 https://v.douyin.com/2myHobLqEAw/ 复制此链接"
        >>> extract_video_url(text)
        'https://v.douyin.com/2myHobLqEAw/'
    """
    # 提取所有 URL
    urls = extract_all_urls(text)

    if not urls:
        raise ValueError("未找到有效的视频链接")

    # 如果只有一个链接，直接返回
    if len(urls) == 1:
        return urls[0]

    # 多个链接时，按优先级选择
    return select_best_url(urls)


def extract_all_urls(text: str) -> List[str]:
    """从文本中提取所有 URL。

    Args:
        text: 输入文本

    Returns:
        URL 列表
    """
    # 匹配 http:// 或 https:// 开头的 URL
    url_pattern = re.compile(
        r'https?://[^\s一-鿿<>"\']+',
        re.IGNORECASE
    )

    matches = url_pattern.findall(text)

    # 清理 URL（去除末尾的标点符号）
    cleaned_urls = []
    for url in matches:
        # 去除末尾的标点符号
        url = url.rstrip('.,;!?。，；！？、）】》"\'')
        # 去除可能的引号
        url = url.strip('"\'')
        cleaned_urls.append(url)

    return cleaned_urls


def select_best_url(urls: List[str]) -> str:
    """从多个 URL 中选择最佳的视频链接。

    优先级规则：
    1. 短链接优先（v.douyin.com, b23.tv, youtu.be 等）
    2. 视频平台链接优先于其他链接
    3. 如果都是视频平台链接，选择第一个

    Args:
        urls: URL 列表

    Returns:
        最佳的视频链接
    """
    if not urls:
        raise ValueError("URL 列表为空")

    # 分类 URL
    short_urls = []  # 短链接
    platform_urls = []  # 平台链接
    other_urls = []  # 其他链接

    for url in urls:
        platform = identify_platform(url)

        if platform:
            # 判断是否为短链接
            if is_short_url(url, platform):
                short_urls.append(url)
            else:
                platform_urls.append(url)
        else:
            other_urls.append(url)

    # 优先返回短链接
    if short_urls:
        return short_urls[0]

    # 其次返回平台链接
    if platform_urls:
        return platform_urls[0]

    # 最后返回第一个链接
    return urls[0]


def identify_platform(url: str) -> Optional[str]:
    """识别 URL 所属的平台。

    Args:
        url: 待识别的 URL

    Returns:
        平台名称（douyin, bilibili, youtube 等），未识别返回 None
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        for platform, domains in PLATFORM_DOMAINS.items():
            for domain in domains:
                if domain in host:
                    return platform

        return None
    except Exception:
        return None


def is_short_url(url: str, platform: str) -> bool:
    """判断是否为短链接。

    Args:
        url: URL 字符串
        platform: 平台名称

    Returns:
        是否为短链接
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # 各平台的短链接域名
        short_domains = {
            "douyin": ["v.douyin.com"],
            "bilibili": ["b23.tv"],
            "youtube": ["youtu.be"],
            "xiaohongshu": ["xhslink.com"],
            "kuaishou": ["v.kuaishou.com"],
            "tiktok": ["vm.tiktok.com"],
        }

        platform_short_domains = short_domains.get(platform, [])
        return any(domain in host for domain in platform_short_domains)
    except Exception:
        return False


def is_video_url(url: str) -> bool:
    """判断是否为视频平台链接。

    Args:
        url: URL 字符串

    Returns:
        是否为视频平台链接
    """
    return identify_platform(url) is not None


# 测试代码
if __name__ == "__main__":
    import sys
    import io

    # 设置 UTF-8 编码
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 测试用例
    test_cases = [
        # 抖音分享（包含多个链接）
        """9.28 12/14 ygo:/ l@C.Hv 今天是放假发工资的苦蛋# AI创造浪潮计划 # 苦蛋 # 哈基米 # 打工人# 剪映  https://v.douyin.com/2myHobLqEAw/ 复制此链接，打开Dou音搜索，直接观看视频！""",

        # 抖音分享（多个视频链接）
        """高热度【智商测试】，看看你的智商有多高！你智商合格吗？ https://v.douyin.com/H-2XbMhoFv4/ 复制此链接，打开【抖音】，直接观看视频！""",

        # B站分享
        """【标题】https://b23.tv/abc123 复制链接打开哔哩哔哩""",

        # 单个链接
        "https://www.douyin.com/video/1234567890",

        # YouTube 短链接
        "Check this out: https://youtu.be/dQw4w9WgXcQ",
    ]

    print("=" * 60)
    print("智能链接提取测试")
    print("=" * 60)

    for i, text in enumerate(test_cases, 1):
        print(f"\n测试 {i}:")
        print(f"输入: {text[:80]}...")
        try:
            result = extract_video_url(text)
            platform = identify_platform(result)
            print(f"[成功] 提取成功: {result}")
            print(f"  平台: {platform}")
        except ValueError as e:
            print(f"[失败] 提取失败: {e}")
