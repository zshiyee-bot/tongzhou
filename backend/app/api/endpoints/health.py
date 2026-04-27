from fastapi import APIRouter


router = APIRouter()


@router.get("/api/health")
async def health_check() -> dict:
    return {"status": "ok", "message": "万能视频下载器服务运行中"}