from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.router import api_router
from app.core.lifespan import lifespan
from app.core.logging import configure_logging


load_dotenv()
configure_logging()

app = FastAPI(
    title="万能视频下载器 API",
    description="基于 yt-dlp 的万能视频下载服务，支持 1800+ 平台",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 提供前端静态文件
frontend_path = Path(__file__).parent.parent.parent / "frontend"
if frontend_path.exists():
    # 首页路由
    @app.get("/")
    async def read_root():
        return FileResponse(frontend_path / "table-new.html")

    # 管理后台路由
    @app.get("/admin")
    async def read_admin():
        return FileResponse(frontend_path / "admin.html")

    # 静态文件（图片等）
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")