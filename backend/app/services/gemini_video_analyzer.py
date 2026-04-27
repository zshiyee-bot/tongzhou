"""Gemini 视频分析模块。

职责:
- 使用 Gemini API 分析视频内容
- 提取口播文案（语音转文字）
- 识别画面内容和关键信息
- 生成结构化的视频分析结果
- 支持官方 SDK 和第三方反代两种模式
"""

import os
import yaml
import time
import base64
from pathlib import Path
from typing import Optional


def ensure_config_exists():
    """确保配置文件存在，不存在则创建默认配置。"""
    config_path = Path(__file__).parent.parent.parent / "api_config.yaml"

    if not config_path.exists():
        default_config = {
            "active": "gemini",
            "apis": {
                "gemini": {
                    "name": "Google Gemini",
                    "api_key": "",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "model": "gemini-2.0-flash-exp",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "use_native_sdk": False
                },
                "custom": {
                    "name": "自定义 API",
                    "api_key": "",
                    "base_url": "",
                    "model": "",
                    "temperature": 0.7,
                    "max_tokens": 4096
                }
            }
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)

        print(f"[配置] 已创建默认配置文件: {config_path}")
        print("[配置] 请访问 http://localhost:1018/admin 配置API密钥")


class GeminiVideoAnalyzer:
    """Gemini 视频分析器，用于分析视频中的口播和画面内容。"""

    def __init__(self):
        """初始化 Gemini 分析器，加载 API 配置。"""
        ensure_config_exists()
        self.config = self._load_config()
        self.api_key = self.config.get("api_key")
        self.base_url = self.config.get("base_url")
        self.model_name = self.config.get("model", "gemini-2.0-flash-exp")
        self.use_native_sdk = self.config.get("use_native_sdk", False)

        # 延迟导入，避免没有安装 SDK 时启动失败
        self.genai = None
        self.model = None
        self.client = None

        if self.api_key and self.api_key != "your-gemini-api-key" and self.api_key != "":
            if self.use_native_sdk:
                self._init_native_sdk()
            else:
                self._init_openai_compatible()
        else:
            print("[Gemini] API密钥未配置，请访问 http://localhost:1018/admin 配置")

    def _load_config(self):
        """加载 API 配置文件。"""
        config_path = Path(__file__).parent.parent.parent / "api_config.yaml"

        if not config_path.exists():
            print(f"[Gemini] 配置文件不存在: {config_path}")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                active = config.get("active", "gemini")
                return config.get("apis", {}).get(active, {})
        except Exception as e:
            print(f"[Gemini] 加载配置失败: {e}")
            return {}

    def _init_native_sdk(self):
        """初始化官方 Google SDK。"""
        try:
            import google.generativeai as genai
            self.genai = genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            print(f"[Gemini] 初始化成功（官方SDK），使用模型: {self.model_name}")
        except ImportError:
            print("[Gemini] 未安装 google-generativeai，请运行: pip install google-generativeai")
        except Exception as e:
            print(f"[Gemini] 初始化失败: {e}")

    def _init_openai_compatible(self):
        """初始化 OpenAI 兼容客户端（第三方反代）。"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print(f"[Gemini] 初始化成功（第三方反代），使用模型: {self.model_name}")
        except ImportError:
            print("[Gemini] 未安装 openai，请运行: pip install openai")
        except Exception as e:
            print(f"[Gemini] 初始化失败: {e}")

    def is_available(self):
        """检查 Gemini 服务是否可用。"""
        return (self.model is not None) or (self.client is not None)

    def analyze_compressed_video(self, video_path: str) -> Optional[dict]:
        """分析压缩后的视频文件。"""
        if not self.is_available():
            print("[Gemini] 服务不可用，跳过分析")
            return None

        compressed_path = video_path.replace(".mp4", "_compressed.mp4")
        if not os.path.exists(compressed_path):
            compressed_path = video_path

        if self.use_native_sdk:
            return self._analyze_with_native_sdk(compressed_path)
        else:
            return self._analyze_with_openai_compatible(compressed_path)

    def _analyze_with_native_sdk(self, video_path: str) -> Optional[dict]:
        """使用官方 SDK 分析视频。"""
        print(f"[Gemini] 使用官方SDK分析视频: {os.path.basename(video_path)}")

        try:
            video_file = self.genai.upload_file(path=video_path)

            while video_file.state.name == "PROCESSING":
                print("[Gemini] 等待视频处理...")
                time.sleep(2)
                video_file = self.genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                print(f"[Gemini] 视频处理失败")
                return None

            prompt = self._build_analysis_prompt()
            response = self.model.generate_content([video_file, prompt])

            return self._parse_response(response.text)

        except Exception as e:
            print(f"[Gemini] 分析失败: {e}")
            return None

    def _analyze_with_openai_compatible(self, video_path: str) -> Optional[dict]:
        """使用 OpenAI 兼容接口分析视频。"""
        print(f"[Gemini] 使用第三方反代分析视频: {os.path.basename(video_path)}")

        try:
            # 检查视频文件大小
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
            print(f"[Gemini] 视频文件大小: {file_size:.2f} MB")

            with open(video_path, "rb") as video_file:
                video_data = base64.b64encode(video_file.read()).decode("utf-8")

            print(f"[Gemini] Base64 编码后大小: {len(video_data) / (1024 * 1024):.2f} MB")

            prompt = self._build_analysis_prompt()

            print(f"[Gemini] 开始调用 API: {self.base_url}")
            print(f"[Gemini] 使用模型: {self.model_name}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:video/mp4;base64,{video_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096
            )

            print(f"[Gemini] API 调用成功，开始解析响应")
            result_text = response.choices[0].message.content
            print(f"[Gemini] 响应内容长度: {len(result_text)} 字符")
            print(f"[Gemini] 响应内容预览: {result_text[:200]}...")

            parsed_result = self._parse_response(result_text)
            print(f"[Gemini] 解析结果: {parsed_result}")
            return parsed_result

        except Exception as e:
            print(f"[Gemini] 分析失败: {e}")
            print(f"[Gemini] 错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return None

    def _build_analysis_prompt(self) -> str:
        """构建视频分析提示词。"""
        return """请分析这个视频，提取以下信息：

1. **品类**：根据视频内容判断商品所属的抖音商品类目（一级类目），如：母婴、户外、美妆、食品、服饰等
2. **产品**：识别视频中展示的具体产品名称或类型，如：早教机、冲锋衣、口红、零食等
3. **黄金3秒文案**：视频开头最吸引人的3秒钟内容，用一句话概括
4. **口播文案**：提取视频中的语音内容，完整记录说话内容
5. **爆款分析**：分析视频为什么能成为爆款，包括内容策略、情感共鸣、传播点等
6. **画面分析**：描述视频的画面内容、拍摄手法、场景布置等

请按以下JSON格式返回：
{
  "category": "品类",
  "product": "产品名称",
  "golden_3s": "黄金3秒文案",
  "transcript": "口播文案",
  "viral_analysis": "爆款分析",
  "scenes": "画面分析"
}

注意：
- 如果视频中没有口播，transcript 字段返回空字符串
- 所有字段都必须返回，不能省略
- 返回纯JSON格式，不要包含其他文字"""

    def _parse_response(self, response_text: str) -> Optional[dict]:
        """解析 AI 返回的结果。"""
        try:
            import json
            import re

            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                print(f"[Gemini] 无法解析响应: {response_text[:200]}")
                return None

        except Exception as e:
            print(f"[Gemini] 解析失败: {e}")
            return None


# 全局单例
analyzer = GeminiVideoAnalyzer()
