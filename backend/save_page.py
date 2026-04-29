"""保存页面内容并分析"""

import sys
import requests

url = sys.argv[1]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

resp = requests.get(url, headers=headers, timeout=10)

# 保存页面
with open("video_page.html", "w", encoding="utf-8") as f:
    f.write(resp.text)

print(f"页面已保存到 video_page.html")
print(f"页面大小: {len(resp.text)} 字节")

# 查找所有 script 标签
import re
scripts = re.findall(r'<script[^>]*>(.*?)</script>', resp.text, re.DOTALL)
print(f"\n找到 {len(scripts)} 个 script 标签")

# 查找包含 JSON 数据的 script
for i, script in enumerate(scripts):
    if len(script) > 100 and ('{' in script or '[' in script):
        print(f"\nScript {i+1} (前200字符):")
        print(script[:200])

        # 检查是否包含视频相关的关键词
        if any(keyword in script for keyword in ['video', 'aweme', 'play', 'download']):
            print("  ⚠️  可能包含视频数据")
            with open(f"script_{i+1}.txt", "w", encoding="utf-8") as f:
                f.write(script)
            print(f"  已保存到 script_{i+1}.txt")
