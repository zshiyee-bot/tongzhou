# Docker 快速部署指南

## 方式一：Docker Compose（推荐）

**一键启动，最简单：**

```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 复制配置文件
cd backend
cp .env.example .env
cp api_config.yaml api_config.yaml  # 如果没有就先启动，后面在管理后台配置

# 3. 启动服务
cd ..
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 停止服务
docker-compose down
```

访问 `http://localhost:1018`，密码 `tongzhou`

首次使用在管理后台（`http://localhost:1018/admin`，密码 `tzadmin`）配置 Gemini API 密钥即可。

## 方式二：纯 Docker

```bash
# 1. 构建镜像
docker build -t tongzhou-video .

# 2. 运行容器
docker run -d \
  --name tongzhou-video \
  -p 1018:1018 \
  -v $(pwd)/backend/data:/app/data \
  -v $(pwd)/backend/downloads:/app/downloads \
  -v $(pwd)/backend/compressed:/app/compressed \
  -v $(pwd)/backend/api_config.yaml:/app/api_config.yaml \
  -v $(pwd)/backend/.env:/app/.env \
  tongzhou-video

# 3. 查看日志
docker logs -f tongzhou-video

# 4. 停止容器
docker stop tongzhou-video
docker rm tongzhou-video
```

## 服务器部署

**在服务器上只需要：**

```bash
# 1. 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com | sh
sudo systemctl start docker
sudo systemctl enable docker

# 2. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 3. 配置并启动
cd backend
cp .env.example .env
cd ..
docker-compose up -d

# 4. 配置防火墙（如果需要）
sudo ufw allow 1018
```

访问 `http://服务器IP:1018`

## 数据持久化

Docker 会自动挂载以下目录，数据不会丢失：
- `backend/data` - 数据库文件
- `backend/downloads` - 下载的视频
- `backend/compressed` - 压缩后的视频
- `backend/api_config.yaml` - API 配置
- `backend/.env` - 环境变量

## 更新项目

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建并启动
docker-compose up -d --build
```

## 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理（包括数据）
docker-compose down -v
```
