"""深度调试这个特殊的抖音视频"""

import sys
import io
import json
import re
import requests
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def deep_debug_video(url: str):
    """深度调试视频解析过程"""

    print("=" * 80)
    print("深度调试抖音视频")
    print("=" * 80)

    # 步骤 1: 提取视频 ID
    print("\n[步骤 1] 提取视频 ID")
    video_id_match = re.search(r'/video/(\d+)', url)
    if video_id_match:
        video_id = video_id_match.group(1)
        print(f"✓ 视频 ID: {video_id}")
    else:
        print("✗ 无法提取视频 ID")
        return

    # 步骤 2: 访问视频页面
    print("\n[步骤 2] 访问视频页面")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.douyin.com/",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"✓ 状态码: {resp.status_code}")
        print(f"✓ 页面大小: {len(resp.text)} 字节")

        # 检查是否需要登录
        if "请先登录" in resp.text or "login" in resp.text.lower():
            print("⚠️  页面可能需要登录")

        # 检查是否有验证码
        if "验证" in resp.text or "captcha" in resp.text.lower():
            print("⚠️  页面可能需要验证码")

    except Exception as e:
        print(f"✗ 访问失败: {e}")
        return

    # 步骤 3: 提取 _ROUTER_DATA
    print("\n[步骤 3] 提取 _ROUTER_DATA")
    marker = "window._ROUTER_DATA = "
    start = resp.text.find(marker)

    if start < 0:
        print("✗ 未找到 _ROUTER_DATA")

        # 尝试查找其他可能的数据源
        print("\n[备选] 查找其他数据源")

        # 查找 RENDER_DATA
        if "RENDER_DATA" in resp.text:
            print("✓ 找到 RENDER_DATA")
            render_match = re.search(r'<script id="RENDER_DATA" type="application/json">(.+?)</script>', resp.text)
            if render_match:
                try:
                    import urllib.parse
                    render_data = urllib.parse.unquote(render_match.group(1))
                    data = json.loads(render_data)
                    print(f"✓ RENDER_DATA 解析成功")
                    print(f"  键: {list(data.keys())}")

                    # 保存数据
                    with open("render_data.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    print("  已保存到 render_data.json")

                except Exception as e:
                    print(f"✗ RENDER_DATA 解析失败: {e}")

        # 查找 SSR_RENDER_DATA
        if "SSR_RENDER_DATA" in resp.text:
            print("✓ 找到 SSR_RENDER_DATA")

        return

    # 解析 _ROUTER_DATA
    idx = start + len(marker)
    while idx < len(resp.text) and resp.text[idx].isspace():
        idx += 1

    if idx >= len(resp.text) or resp.text[idx] != "{":
        print("✗ _ROUTER_DATA 格式错误")
        return

    depth = 0
    in_str = False
    escaped = False
    for cursor in range(idx, len(resp.text)):
        ch = resp.text[cursor]
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
                    router_data = json.loads(resp.text[idx: cursor + 1])
                    print(f"✓ _ROUTER_DATA 解析成功")
                    print(f"  顶层键: {list(router_data.keys())}")

                    # 步骤 4: 查找视频信息
                    print("\n[步骤 4] 查找视频信息")
                    loader_data = router_data.get("loaderData", {})
                    print(f"  loaderData 键: {list(loader_data.keys())}")

                    video_found = False
                    for key, node in loader_data.items():
                        if not isinstance(node, dict):
                            continue

                        print(f"\n  检查节点: {key}")
                        print(f"    节点键: {list(node.keys())}")

                        # 检查 videoInfoRes
                        video_info_res = node.get("videoInfoRes", {})
                        if video_info_res:
                            print(f"    ✓ 找到 videoInfoRes")
                            print(f"      videoInfoRes 键: {list(video_info_res.keys())}")

                            item_list = video_info_res.get("item_list", [])
                            if item_list:
                                print(f"      ✓ 找到 item_list，长度: {len(item_list)}")

                                if len(item_list) > 0:
                                    item = item_list[0]
                                    video_found = True

                                    print(f"\n[步骤 5] 分析视频数据")
                                    print(f"  item 顶层键: {list(item.keys())}")

                                    # 基本信息
                                    print(f"\n  基本信息:")
                                    print(f"    aweme_id: {item.get('aweme_id')}")
                                    print(f"    desc: {item.get('desc', '')[:50]}")
                                    print(f"    aweme_type: {item.get('aweme_type')}")

                                    # 作者信息
                                    author = item.get("author", {})
                                    print(f"\n  作者信息:")
                                    print(f"    nickname: {author.get('nickname')}")
                                    print(f"    unique_id: {author.get('unique_id')}")

                                    # 视频信息
                                    video = item.get("video", {})
                                    print(f"\n  video 键: {list(video.keys())}")

                                    # play_addr
                                    play_addr = video.get("play_addr", {})
                                    print(f"\n  play_addr 键: {list(play_addr.keys())}")
                                    print(f"    uri: {play_addr.get('uri')}")
                                    url_list = play_addr.get("url_list", [])
                                    print(f"    url_list 数量: {len(url_list)}")
                                    if url_list:
                                        for i, u in enumerate(url_list, 1):
                                            print(f"      地址 {i}: {u}")

                                    # bit_rate
                                    bit_rate = video.get("bit_rate")
                                    print(f"\n  bit_rate: {bit_rate}")
                                    if bit_rate:
                                        print(f"    bit_rate 类型: {type(bit_rate)}")
                                        print(f"    bit_rate 长度: {len(bit_rate) if isinstance(bit_rate, list) else 'N/A'}")

                                    # download_addr
                                    download_addr = video.get("download_addr", {})
                                    if download_addr:
                                        print(f"\n  download_addr 键: {list(download_addr.keys())}")
                                        download_urls = download_addr.get("url_list", [])
                                        print(f"    download url_list 数量: {len(download_urls)}")
                                        if download_urls:
                                            for i, u in enumerate(download_urls, 1):
                                                print(f"      下载地址 {i}: {u}")

                                    # 保存完整数据
                                    with open("video_item_debug.json", "w", encoding="utf-8") as f:
                                        json.dump(item, f, ensure_ascii=False, indent=2)
                                    print(f"\n  ✓ 完整数据已保存到 video_item_debug.json")

                                    # 步骤 6: 测试播放地址
                                    print(f"\n[步骤 6] 测试播放地址")

                                    test_urls = []

                                    # 添加 play_addr 中的地址
                                    if url_list:
                                        for u in url_list:
                                            test_urls.append(("play_addr (原始)", u))
                                            # 无水印版本
                                            if "playwm" in u:
                                                test_urls.append(("play_addr (无水印)", u.replace("playwm", "play")))

                                    # 添加 download_addr 中的地址
                                    if download_urls:
                                        for u in download_urls:
                                            test_urls.append(("download_addr", u))

                                    # 测试所有地址
                                    for label, test_url in test_urls:
                                        print(f"\n  测试 {label}:")
                                        print(f"    URL: {test_url[:100]}...")
                                        try:
                                            test_resp = requests.head(
                                                test_url,
                                                timeout=10,
                                                allow_redirects=True,
                                                headers={"Referer": "https://www.douyin.com/"}
                                            )
                                            print(f"    ✓ 状态码: {test_resp.status_code}")
                                            print(f"      Content-Type: {test_resp.headers.get('Content-Type', 'N/A')}")
                                            print(f"      Content-Length: {test_resp.headers.get('Content-Length', 'N/A')}")

                                            if test_resp.status_code == 200:
                                                print(f"\n    ✅ 找到可用地址！")
                                                print(f"    完整URL: {test_url}")

                                        except Exception as e:
                                            print(f"    ✗ 失败: {str(e)[:100]}")

                                    break

                    if not video_found:
                        print("\n✗ 未找到视频信息")
                        print("  可能原因:")
                        print("  1. 视频需要登录才能查看")
                        print("  2. 视频已被删除或下架")
                        print("  3. 地域限制")
                        print("  4. 数据结构发生变化")

                except Exception as e:
                    print(f"✗ JSON 解析失败: {e}")
                    import traceback
                    traceback.print_exc()
                break


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python deep_debug.py <视频URL>")
        sys.exit(1)

    deep_debug_video(sys.argv[1])
