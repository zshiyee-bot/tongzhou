@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════════╗
echo ║          视频分析系统 - 一键安装（Docker 版）              ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装
    echo.
    echo 请先安装 Docker Desktop:
    echo   https://www.docker.com/products/docker-desktop
    echo.
    echo 安装完成后，请重新运行此脚本
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否可用
docker compose version >nul 2>&1
if errorlevel 1 (
    docker-compose --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose 未安装
        echo.
        echo Docker Desktop 应该已包含 Docker Compose
        echo 请确保 Docker Desktop 正在运行
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker-compose
) else (
    set COMPOSE_CMD=docker compose
)

echo ✅ Docker 已安装
echo ✅ Docker Compose 已安装
echo.

REM 创建必要的目录
echo 📁 创建数据目录...
if not exist "backend\downloads" mkdir backend\downloads
if not exist "backend\compressed" mkdir backend\compressed
if not exist "backend\preset_images" mkdir backend\preset_images

REM 创建默认配置文件（如果不存在）
if not exist "backend\api_config.yaml" (
    echo 📝 创建默认配置文件...
    (
        echo active: gemini
        echo max_concurrency: 5
        echo apis:
        echo   gemini:
        echo     name: Google Gemini
        echo     api_key: ""
        echo     base_url: https://generativelanguage.googleapis.com/v1beta
        echo     model: gemini-2.0-flash-exp
        echo     temperature: 0.7
        echo     max_tokens: 4096
        echo     use_native_sdk: false
        echo   custom:
        echo     name: 自定义 API
        echo     api_key: ""
        echo     base_url: ""
        echo     model: ""
        echo     temperature: 0.7
        echo     max_tokens: 4096
    ) > backend\api_config.yaml
)

echo.
echo 🚀 开始构建 Docker 镜像...
echo    （首次构建需要 5-10 分钟，请耐心等待）
echo.

REM 构建并启动容器
%COMPOSE_CMD% build
%COMPOSE_CMD% up -d

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                    🎉 安装完成！                           ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📍 访问地址：
echo    前端页面：http://localhost:1018
echo    管理后台：http://localhost:1018/admin
echo.
echo 🔧 配置 API 密钥：
echo    1. 访问管理后台：http://localhost:1018/admin
echo    2. 默认密码：admin123
echo    3. 在 API 配置页面填写 Gemini API Key
echo.
echo 📊 查看日志：
echo    %COMPOSE_CMD% logs -f
echo.
echo 🛑 停止服务：
echo    %COMPOSE_CMD% down
echo.
echo 🔄 重启服务：
echo    %COMPOSE_CMD% restart
echo.
pause
