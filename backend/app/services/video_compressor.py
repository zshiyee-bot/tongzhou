"""视频压缩模块。

职责:
- 使用 ffmpeg 压缩视频文件
- 支持多种压缩质量级别
- 自动管理压缩后的文件
- 建立原视频和压缩视频的映射关系
"""

import os
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Optional


class VideoCompressor:
    """视频压缩器，使用 ffmpeg 压缩视频文件。"""

    def __init__(self, compressed_dir: Optional[str] = None):
        """初始化视频压缩器。

        Args:
            compressed_dir: 压缩视频存放目录，默认为 backend/compressed
        """
        if compressed_dir is None:
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            compressed_dir = os.path.join(backend_dir, "compressed")

        self.compressed_dir = Path(compressed_dir)
        self.compressed_dir.mkdir(parents=True, exist_ok=True)

        # 映射文件：记录原视频和压缩视频的对应关系
        self.mapping_file = self.compressed_dir / "video_mapping.json"
        self.mapping = self._load_mapping()

        # 尝试激活 static_ffmpeg
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except Exception:
            pass

        # 检查 ffmpeg 是否可用
        self.has_ffmpeg = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """检查 ffmpeg 是否可用。

        Returns:
            True 表示 ffmpeg 可用，False 表示不可用。
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # 尝试使用 static_ffmpeg
            try:
                import static_ffmpeg
                static_ffmpeg.add_paths()
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                )
                return result.returncode == 0
            except Exception:
                return False

    def _load_mapping(self) -> dict:
        """加载视频映射关系。

        Returns:
            映射字典，key 为原视频路径的 hash，value 为压缩视频信息。
        """
        if self.mapping_file.exists():
            try:
                with open(self.mapping_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_mapping(self):
        """保存视频映射关系到文件。"""
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[压缩] 保存映射文件失败: {e}")

    @staticmethod
    def _get_file_hash(filepath: str) -> str:
        """计算文件路径的 hash 值，用作映射的 key。

        Args:
            filepath: 文件路径。

        Returns:
            文件路径的 MD5 hash 值。
        """
        return hashlib.md5(filepath.encode()).hexdigest()

    def _get_video_info(self, input_path: str) -> Optional[dict]:
        """获取视频的详细信息。"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                input_path
            ]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if result.returncode == 0:
                import json
                return json.loads(result.stdout.decode("utf-8"))
        except Exception as e:
            print(f"[压缩] 获取视频信息失败: {e}")
        return None

    def compress_video(
        self,
        input_path: str,
        quality: str = "medium",
        max_width: int = 1280,
    ) -> Optional[dict]:
        """压缩视频文件。

        Args:
            input_path: 原视频文件路径。
            quality: 压缩质量，可选 "low", "medium", "high"。
            max_width: 最大宽度，默认 1280px。

        Returns:
            压缩结果字典，包含 compressed_path、original_size、compressed_size 等信息。
            如果压缩失败，返回 None。
        """
        if not self.has_ffmpeg:
            print("[压缩] ffmpeg 不可用，跳过压缩")
            return None

        if not os.path.exists(input_path):
            print(f"[压缩] 文件不存在: {input_path}")
            return None

        # 检查是否已经压缩过
        file_hash = self._get_file_hash(input_path)
        if file_hash in self.mapping:
            compressed_path = self.mapping[file_hash]["compressed_path"]
            if os.path.exists(compressed_path):
                print(f"[压缩] 视频已压缩过，跳过: {os.path.basename(input_path)}")
                return self.mapping[file_hash]

        # 获取原视频信息
        video_info = self._get_video_info(input_path)
        if video_info:
            # 获取视频流信息
            video_stream = next((s for s in video_info.get("streams", []) if s.get("codec_type") == "video"), None)
            if video_stream:
                original_bitrate = int(video_info.get("format", {}).get("bit_rate", 0)) // 1000  # kbps
                original_width = video_stream.get("width", 0)
                print(f"[压缩] 原视频信息: {original_width}p, 码率 {original_bitrate}kbps")

        # 生成压缩后的文件名
        input_file = Path(input_path)
        compressed_filename = f"{input_file.stem}_compressed{input_file.suffix}"
        compressed_path = self.compressed_dir / compressed_filename

        # 极致压缩参数（专为 Gemini AI 分析优化）
        # 使用固定码率而不是 CRF，确保文件变小
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", "scale='min(480,iw)':-2,fps=10",  # 480p + 10fps
            "-c:v", "libx264",
            "-b:v", "300k",  # 固定视频码率 300kbps
            "-maxrate", "400k",  # 最大码率
            "-bufsize", "800k",  # 缓冲区大小
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-b:a", "32k",  # 极低音频码率
            "-ac", "1",  # 单声道
            "-ar", "22050",  # 降低采样率
            "-movflags", "+faststart",
            "-y",
            str(compressed_path),
        ]

        try:
            print(f"[压缩] 开始压缩: {os.path.basename(input_path)} (质量: {quality})")

            # 执行压缩
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,  # 10 分钟超时
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode("utf-8", errors="ignore")
                print(f"[压缩] 压缩失败: {error_msg[:200]}")
                return None

            # 获取文件大小
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(compressed_path)
            compression_ratio = (1 - compressed_size / original_size) * 100

            # 保存映射关系
            result_info = {
                "original_path": input_path,
                "compressed_path": str(compressed_path),
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": round(compression_ratio, 2),
                "quality": quality,
                "max_width": max_width,
            }

            self.mapping[file_hash] = result_info
            self._save_mapping()

            print(
                f"[压缩] 压缩完成: {os.path.basename(input_path)} "
                f"({self._format_size(original_size)} → {self._format_size(compressed_size)}, "
                f"压缩率 {compression_ratio:.1f}%)"
            )

            return result_info

        except subprocess.TimeoutExpired:
            print(f"[压缩] 压缩超时: {os.path.basename(input_path)}")
            return None
        except Exception as e:
            print(f"[压缩] 压缩出错: {e}")
            return None

    def get_compressed_video(self, original_path: str) -> Optional[str]:
        """获取原视频对应的压缩视频路径。

        Args:
            original_path: 原视频文件路径。

        Returns:
            压缩视频路径，如果不存在则返回 None。
        """
        file_hash = self._get_file_hash(original_path)
        if file_hash in self.mapping:
            compressed_path = self.mapping[file_hash]["compressed_path"]
            if os.path.exists(compressed_path):
                return compressed_path
        return None

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小。

        Args:
            size_bytes: 文件大小（字节）。

        Returns:
            格式化后的字符串，如 "1.5MB"。
        """
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f}GB"


# 全局压缩器实例
compressor = VideoCompressor()
