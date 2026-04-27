FROM python:3.10-slim

# 安装 ffmpeg（视频处理需要）
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY backend/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY backend/ .
COPY frontend/ /app/frontend/

# 创建必要的目录
RUN mkdir -p data downloads compressed

# 暴露端口
EXPOSE 1018

# 启动命令
CMD ["python", "main.py"]
