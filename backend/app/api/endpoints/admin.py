"""管理后台 API。"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import yaml
import os
from pathlib import Path

from app.repositories.db import get_db


router = APIRouter()

# 管理员密码
ADMIN_PASSWORD = "tzadmin"

# 前端用户密码
FRONTEND_PASSWORD = "123456"


class AdminLoginRequest(BaseModel):
    """管理员登录请求。"""
    password: str


class PasswordUpdateRequest(BaseModel):
    """密码更新请求。"""
    new_password: str


class APIConfigUpdateRequest(BaseModel):
    """API配置更新请求。"""
    active: str
    api_key: str
    base_url: str = None
    model: str = None


def verify_admin_password(password: str):
    """验证管理员密码。"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    return True


@router.post("/api/admin/login")
async def admin_login(req: AdminLoginRequest):
    """管理员登录。"""
    verify_admin_password(req.password)
    return {"success": True, "message": "登录成功"}


@router.post("/api/auth/login")
async def frontend_login(req: AdminLoginRequest):
    """前端用户登录。"""
    if req.password != FRONTEND_PASSWORD:
        raise HTTPException(status_code=401, detail="密码错误")
    return {"success": True, "message": "登录成功"}


@router.get("/api/admin/stats")
async def get_stats(password: str):
    """获取数据统计。"""
    verify_admin_password(password)

    with get_db() as conn:
        # 视频记录统计
        total_records = conn.execute("SELECT COUNT(*) as cnt FROM video_records").fetchone()["cnt"]

        # 工作表统计
        total_sheets = conn.execute("SELECT COUNT(*) as cnt FROM sheets").fetchone()["cnt"]

        # 今日新增
        today_records = conn.execute(
            "SELECT COUNT(*) as cnt FROM video_records WHERE DATE(created_at) = DATE('now')"
        ).fetchone()["cnt"]

        # 有AI分析的记录数
        analyzed_records = conn.execute(
            "SELECT COUNT(*) as cnt FROM video_records WHERE golden_3s_copy IS NOT NULL"
        ).fetchone()["cnt"]

        return {
            "total_records": total_records,
            "total_sheets": total_sheets,
            "today_records": today_records,
            "analyzed_records": analyzed_records,
            "analysis_rate": f"{analyzed_records / total_records * 100:.1f}%" if total_records > 0 else "0%"
        }


@router.get("/api/admin/config")
async def get_api_config(password: str):
    """获取API配置。"""
    verify_admin_password(password)

    config_path = Path(__file__).parent.parent.parent.parent / "api_config.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    active = config.get("active", "gemini")
    active_config = config.get("apis", {}).get(active, {})

    return {
        "active": active,
        "api_key": active_config.get("api_key", ""),
        "base_url": active_config.get("base_url", ""),
        "model": active_config.get("model", ""),
        "available_apis": list(config.get("apis", {}).keys())
    }


@router.put("/api/admin/config")
async def update_api_config(req: APIConfigUpdateRequest, password: str):
    """更新API配置。"""
    verify_admin_password(password)

    config_path = Path(__file__).parent.parent.parent.parent / "api_config.yaml"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 更新配置
    if req.active not in config.get("apis", {}):
        raise HTTPException(status_code=400, detail=f"API配置 '{req.active}' 不存在")

    config["active"] = req.active
    config["apis"][req.active]["api_key"] = req.api_key

    if req.base_url:
        config["apis"][req.active]["base_url"] = req.base_url
    if req.model:
        config["apis"][req.active]["model"] = req.model

    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    return {"success": True, "message": "配置已更新，请重启后端服务生效"}


@router.get("/api/admin/frontend-password")
async def get_frontend_password(password: str):
    """获取前端登录密码。"""
    verify_admin_password(password)

    # 读取前端HTML文件
    frontend_path = Path(__file__).parent.parent.parent.parent.parent / "frontend" / "table-new.html"

    if not frontend_path.exists():
        raise HTTPException(status_code=404, detail="前端文件不存在")

    with open(frontend_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取密码
    import re
    match = re.search(r'const CORRECT_PASSWORD = [\'"](.+?)[\'"]', content)

    if match:
        return {"password": match.group(1)}
    else:
        return {"password": "未找到"}


@router.put("/api/admin/frontend-password")
async def update_frontend_password(req: PasswordUpdateRequest, password: str):
    """更新前端登录密码。"""
    verify_admin_password(password)

    frontend_path = Path(__file__).parent.parent.parent.parent.parent / "frontend" / "table-new.html"

    if not frontend_path.exists():
        raise HTTPException(status_code=404, detail="前端文件不存在")

    with open(frontend_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换密码
    import re
    new_content = re.sub(
        r'const CORRECT_PASSWORD = [\'"](.+?)[\'"]',
        f"const CORRECT_PASSWORD = '{req.new_password}'",
        content
    )

    with open(frontend_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return {"success": True, "message": "前端密码已更新"}


@router.delete("/api/admin/records/{record_id}")
async def delete_record(record_id: int, password: str):
    """删除视频记录。"""
    verify_admin_password(password)

    with get_db() as conn:
        # 检查记录是否存在
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        # 删除记录
        conn.execute("DELETE FROM video_records WHERE id = ?", (record_id,))

    return {"success": True, "message": "记录已删除"}


@router.post("/api/admin/clear-data")
async def clear_all_data(password: str):
    """清空所有数据（危险操作）。"""
    verify_admin_password(password)

    with get_db() as conn:
        conn.execute("DELETE FROM video_records")
        # 保留默认工作表
        conn.execute("DELETE FROM sheets WHERE id != 'sheet1'")

    return {"success": True, "message": "所有数据已清空"}
