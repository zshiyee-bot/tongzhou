"""工作表预设管理 API。"""

import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.repositories.db import get_db


router = APIRouter()


class PresetResponse(BaseModel):
    """预设响应模型。"""
    sheet_id: str
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_image_path: Optional[str] = None


@router.get("/api/sheets/{sheet_id}/preset", response_model=PresetResponse)
async def get_preset(sheet_id: str):
    """获取工作表的预设配置。"""
    with get_db() as conn:
        preset = conn.execute(
            "SELECT * FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        if preset:
            return {
                "sheet_id": preset["sheet_id"],
                "product_name": preset["product_name"],
                "product_description": preset["product_description"],
                "product_image_path": preset["product_image_path"]
            }
        else:
            # 返回空预设
            return {
                "sheet_id": sheet_id,
                "product_name": None,
                "product_description": None,
                "product_image_path": None
            }


@router.post("/api/sheets/{sheet_id}/preset")
async def save_preset(
    sheet_id: str,
    product_name: str = Form(...),
    product_description: str = Form(...),
    product_image: Optional[UploadFile] = File(None)
):
    """保存工作表的预设配置。"""

    # 处理图片上传
    image_path = None
    if product_image and product_image.filename:
        # 创建预设图片目录
        preset_images_dir = Path(__file__).parent.parent.parent.parent / "preset_images"
        preset_images_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        file_extension = os.path.splitext(product_image.filename)[1]
        image_filename = f"{sheet_id}{file_extension}"
        image_path = preset_images_dir / image_filename

        # 保存图片
        with open(image_path, "wb") as f:
            shutil.copyfileobj(product_image.file, f)

        # 存储相对路径
        image_path = str(image_path.relative_to(Path(__file__).parent.parent.parent.parent))

    # 保存到数据库
    with get_db() as conn:
        # 检查是否已存在
        existing = conn.execute(
            "SELECT id FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        if existing:
            # 更新
            if image_path:
                conn.execute(
                    """UPDATE sheet_presets
                       SET product_name = ?, product_description = ?, product_image_path = ?, updated_at = datetime('now')
                       WHERE sheet_id = ?""",
                    (product_name, product_description, image_path, sheet_id)
                )
            else:
                # 不更新图片
                conn.execute(
                    """UPDATE sheet_presets
                       SET product_name = ?, product_description = ?, updated_at = datetime('now')
                       WHERE sheet_id = ?""",
                    (product_name, product_description, sheet_id)
                )
        else:
            # 插入
            conn.execute(
                """INSERT INTO sheet_presets (sheet_id, product_name, product_description, product_image_path)
                   VALUES (?, ?, ?, ?)""",
                (sheet_id, product_name, product_description, image_path)
            )

    return {"success": True, "message": "预设已保存"}


@router.delete("/api/sheets/{sheet_id}/preset")
async def delete_preset(sheet_id: str):
    """删除工作表的预设配置。"""
    with get_db() as conn:
        # 获取图片路径
        preset = conn.execute(
            "SELECT product_image_path FROM sheet_presets WHERE sheet_id = ?",
            (sheet_id,)
        ).fetchone()

        # 删除图片文件
        if preset and preset["product_image_path"]:
            image_path = Path(__file__).parent.parent.parent.parent / preset["product_image_path"]
            if image_path.exists():
                image_path.unlink()

        # 删除数据库记录
        conn.execute("DELETE FROM sheet_presets WHERE sheet_id = ?", (sheet_id,))

    return {"success": True, "message": "预设已删除"}
