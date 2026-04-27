"""工作表管理 API。"""

from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.repositories.db import get_db


router = APIRouter()


class SheetCreate(BaseModel):
    """创建工作表的请求模型。"""
    id: str
    name: str
    position: int = 0


class SheetUpdate(BaseModel):
    """更新工作表的请求模型。"""
    name: str = None
    position: int = None


class SheetResponse(BaseModel):
    """工作表的响应模型。"""
    id: str
    name: str
    position: int
    created_at: str = None
    updated_at: str = None


@router.get("/api/sheets", response_model=List[SheetResponse])
async def get_sheets():
    """获取所有工作表。"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sheets ORDER BY position ASC"
        ).fetchall()
        return [dict(row) for row in rows]


@router.post("/api/sheets", response_model=SheetResponse)
async def create_sheet(req: SheetCreate):
    """创建新工作表。"""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO sheets (id, name, position) VALUES (?, ?, ?)""",
            (req.id, req.name, req.position)
        )

        row = conn.execute(
            "SELECT * FROM sheets WHERE id = ?", (req.id,)
        ).fetchone()

        return dict(row)


@router.put("/api/sheets/{sheet_id}", response_model=SheetResponse)
async def update_sheet(sheet_id: str, req: SheetUpdate):
    """更新工作表。"""
    with get_db() as conn:
        # 检查工作表是否存在
        sheet = conn.execute(
            "SELECT * FROM sheets WHERE id = ?", (sheet_id,)
        ).fetchone()

        if not sheet:
            raise HTTPException(status_code=404, detail="工作表不存在")

        # 构建更新语句
        updates = []
        params = []

        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name)

        if req.position is not None:
            updates.append("position = ?")
            params.append(req.position)

        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(sheet_id)

            sql = f"UPDATE sheets SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, params)

        row = conn.execute(
            "SELECT * FROM sheets WHERE id = ?", (sheet_id,)
        ).fetchone()

        return dict(row)


@router.delete("/api/sheets/{sheet_id}")
async def delete_sheet(sheet_id: str):
    """删除工作表。"""
    with get_db() as conn:
        # 检查工作表是否存在
        sheet = conn.execute(
            "SELECT * FROM sheets WHERE id = ?", (sheet_id,)
        ).fetchone()

        if not sheet:
            raise HTTPException(status_code=404, detail="工作表不存在")

        # 检查是否是最后一个工作表
        count = conn.execute("SELECT COUNT(*) as cnt FROM sheets").fetchone()["cnt"]
        if count <= 1:
            raise HTTPException(status_code=400, detail="至少需要保留一个工作表")

        # 删除工作表
        conn.execute("DELETE FROM sheets WHERE id = ?", (sheet_id,))

        # 删除该工作表下的所有视频记录
        conn.execute("DELETE FROM video_records WHERE sheet_id = ?", (sheet_id,))

        return {"message": "删除成功"}
