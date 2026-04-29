"""工作表预设管理 API。"""

import os
import json
import io
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from PIL import Image

from app.repositories.db import get_db


router = APIRouter()


def compress_image(image_data: bytes, max_size: tuple = (1920, 1920), quality: int = 85) -> bytes:
    """压缩图片到合适大小。

    Args:
        image_data: 原始图片数据
        max_size: 最大尺寸 (width, height)
        quality: JPEG 质量 (1-100)

    Returns:
        压缩后的图片数据
    """
    try:
        # 打开图片
        img = Image.open(io.BytesIO(image_data))

        # 转换 RGBA 到 RGB（如果需要）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background

        # 保持宽高比缩放
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 保存为 JPEG
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)

        compressed_data = output.getvalue()

        # 计算压缩比
        original_size = len(image_data) / 1024  # KB
        compressed_size = len(compressed_data) / 1024  # KB
        print(f"[图片压缩] 原始: {original_size:.2f}KB -> 压缩后: {compressed_size:.2f}KB (压缩率: {(1 - compressed_size/original_size)*100:.1f}%)")

        return compressed_data
    except Exception as e:
        print(f"[图片压缩] 压缩失败: {e}，使用原图")
        return image_data


class PresetResponse(BaseModel):
    """预设响应模型。"""
    sheet_id: str
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_paths: Optional[List[str]] = None


@router.get("/api/sheets/{sheet_id}/preset", response_model=PresetResponse)
async def get_preset(sheet_id: str):
    """获取工作表的预设配置。"""
    with get_db() as conn:
        preset = conn.execute(
            "SELECT * FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        if preset:
            # 解析 JSON 数组
            image_paths = None
            if preset["product_image_paths"]:
                try:
                    image_paths = json.loads(preset["product_image_paths"])
                except:
                    image_paths = []

            return {
                "sheet_id": preset["sheet_id"],
                "product_name": preset["product_name"],
                "product_description": preset["product_description"],
                "product_image_paths": image_paths
            }
        else:
            # 返回空预设
            return {
                "sheet_id": sheet_id,
                "product_name": None,
                "product_description": None,
                "product_image_paths": None
            }


@router.post("/api/sheets/{sheet_id}/preset")
async def save_preset(
    sheet_id: str,
    product_name: str = Form(...),
    product_description: str = Form(...),
    product_images: List[UploadFile] = File(None)
):
    """保存工作表的预设配置（支持多图，追加模式）。"""

    # 处理图片上传
    image_paths = []
    if product_images:
        # 创建预设图片目录
        preset_images_dir = Path(__file__).parent.parent.parent.parent / "preset_images"
        preset_images_dir.mkdir(parents=True, exist_ok=True)

        # 获取已有的图片路径
        with get_db() as conn:
            existing = conn.execute(
                "SELECT product_image_paths FROM sheet_presets WHERE sheet_id = ?",
                (sheet_id,)
            ).fetchone()

            if existing and existing["product_image_paths"]:
                try:
                    image_paths = json.loads(existing["product_image_paths"])
                except:
                    image_paths = []

        # 验证文件类型和大小
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        max_file_size = 10 * 1024 * 1024  # 10MB

        # 计算新图片的起始索引
        start_idx = len(image_paths)

        for idx, product_image in enumerate(product_images):
            if not product_image.filename:
                continue

            # 检查是否超过5张限制
            if start_idx + idx >= 5:
                print(f"[预设] 已达到5张图片上限，跳过后续图片")
                break

            # 验证文件扩展名
            file_extension = os.path.splitext(product_image.filename)[1].lower()
            if file_extension not in allowed_extensions:
                raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_extension}，仅支持 jpg, jpeg, png, gif, webp")

            # 读取文件内容
            file_content = await product_image.read()

            # 验证文件大小
            if len(file_content) > max_file_size:
                raise HTTPException(status_code=400, detail=f"文件 {product_image.filename} 过大，最大支持 10MB")

            # 压缩图片
            compressed_content = compress_image(file_content)

            # 生成文件名（使用实际索引，统一使用 .jpg）
            actual_idx = start_idx + idx
            image_filename = f"{sheet_id}_{actual_idx}.jpg"
            image_path = preset_images_dir / image_filename

            # 保存压缩后的图片
            with open(image_path, "wb") as f:
                f.write(compressed_content)

            # 存储相对路径（使用正斜杠）
            relative_path = str(image_path.relative_to(Path(__file__).parent.parent.parent.parent)).replace('\\', '/')
            image_paths.append(relative_path)

    # 保存到数据库
    with get_db() as conn:
        # 检查是否已存在
        existing = conn.execute(
            "SELECT id FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        # 转换为 JSON 字符串
        image_paths_json = json.dumps(image_paths) if image_paths else None

        if existing:
            # 更新
            conn.execute(
                """UPDATE sheet_presets
                   SET product_name = ?, product_description = ?, product_image_paths = ?, updated_at = datetime('now')
                   WHERE sheet_id = ?""",
                (product_name, product_description, image_paths_json, sheet_id)
            )
        else:
            # 插入
            conn.execute(
                """INSERT INTO sheet_presets (sheet_id, product_name, product_description, product_image_paths)
                   VALUES (?, ?, ?, ?)""",
                (sheet_id, product_name, product_description, image_paths_json)
            )

    return {"success": True, "message": "预设已保存"}


@router.delete("/api/sheets/{sheet_id}/preset/image/{image_index}")
async def delete_preset_image(sheet_id: str, image_index: int):
    """删除预设中的单张图片。"""
    with get_db() as conn:
        preset = conn.execute(
            "SELECT product_image_paths FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        if not preset or not preset["product_image_paths"]:
            raise HTTPException(status_code=404, detail="预设不存在或没有图片")

        try:
            image_paths = json.loads(preset["product_image_paths"])

            if image_index < 0 or image_index >= len(image_paths):
                raise HTTPException(status_code=400, detail="图片索引无效")

            # 删除文件
            image_path = Path(__file__).parent.parent.parent.parent / image_paths[image_index]
            if image_path.exists():
                image_path.unlink()

            # 从列表中移除
            image_paths.pop(image_index)

            # 更新数据库
            image_paths_json = json.dumps(image_paths) if image_paths else None
            conn.execute(
                """UPDATE sheet_presets
                   SET product_image_paths = ?, updated_at = datetime('now')
                   WHERE sheet_id = ?""",
                (image_paths_json, sheet_id)
            )

            return {"success": True, "message": "图片已删除"}
        except Exception as e:
            print(f"[预设] 删除图片失败: {e}")
            raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/api/sheets/{sheet_id}/preset")
async def delete_preset(sheet_id: str):
    """删除工作表的预设配置。"""
    with get_db() as conn:
        # 获取图片路径
        preset = conn.execute(
            "SELECT product_image_paths FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        # 删除图片文件
        if preset and preset["product_image_paths"]:
            try:
                image_paths = json.loads(preset["product_image_paths"])
                for image_path in image_paths:
                    file_path = Path(__file__).parent.parent.parent.parent / image_path
                    if file_path.exists():
                        file_path.unlink()
            except Exception as e:
                print(f"[预设] 删除图片失败: {e}")

        # 删除数据库记录
        conn.execute("DELETE FROM sheet_presets WHERE sheet_id = ?", (sheet_id,))

    return {"success": True, "message": "预设已删除"}
