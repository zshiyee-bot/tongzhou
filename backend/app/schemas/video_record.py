"""视频记录相关的请求和响应模型。"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VideoRecordCreate(BaseModel):
    """创建视频记录的请求模型。"""
    video_url: str
    sheet_id: Optional[str] = "sheet1"


class VideoRecordUpdate(BaseModel):
    """更新视频记录的请求模型。"""
    video_time: Optional[str] = None
    category: Optional[str] = None
    product: Optional[str] = None
    golden_3s_copy: Optional[str] = None
    transcript: Optional[str] = None
    video_copy: Optional[str] = None
    viral_analysis: Optional[str] = None
    scene_analysis: Optional[str] = None
    exposure: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    collects: Optional[int] = None
    remarks: Optional[str] = None


class VideoRecordResponse(BaseModel):
    """视频记录的响应模型。"""
    id: int
    video_url: str
    video_file_path: Optional[str] = None
    video_time: Optional[str] = None
    category: Optional[str] = None
    product: Optional[str] = None
    golden_3s_copy: Optional[str] = None
    transcript: Optional[str] = None
    video_copy: Optional[str] = None
    viral_analysis: Optional[str] = None
    scene_analysis: Optional[str] = None
    exposure: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    collects: Optional[int] = None
    remarks: Optional[str] = None
    sheet_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
