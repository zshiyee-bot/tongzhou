@echo off
REM 清理下载目录中的视频文件
REM 使用方法：双击运行此文件

echo 正在清理下载目录...
cd /d "%~dp0"
cd downloads

echo 当前目录中的文件：
dir /b

echo.
echo 是否要删除所有视频文件？
pause

del /q *.mp4 *.flv *.webm *.mkv 2>nul

echo.
echo 清理完成！
pause
