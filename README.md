# 视频分析系统

基于 FastAPI + Gemini AI 的智能视频分析工具。支持视频自动下载、AI内容分析、多工作表管理等功能。

**🐳 推荐使用 Docker 部署，3 条命令即可运行！**

## ✨ 功能特性

- ✅ **视频自动下载** - 支持抖音等平台视频链接解析和下载
- ✅ **AI智能分析** - 自动识别品类、产品、黄金3秒、口播文案、爆款分析、画面分析
- ✅ **多工作表管理** - Excel风格的多工作表，支持添加、删除、重命名
- ✅ **实时流式更新** - SSE流式推送，实时显示处理进度
- ✅ **Excel风格编辑** - 可调整列宽、自定义列、双击编辑
- ✅ **数据持久化** - SQLite数据库存储，支持跨浏览器同步
- ✅ **自动恢复机制** - 刷新页面后自动检测未完成任务并继续处理
- ✅ **Docker 支持** - 简单部署，无需配置环境

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

**前置要求：** 安装 Docker 和 Docker Compose

```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 启动服务（首次构建需要 5-10 分钟）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问应用
# http://localhost:1018
```

**访问地址：**
- 前端页面：http://localhost:1018（密码：tongzhou）
- 管理后台：http://localhost:1018/admin（密码：tzadmin）

---

### 方式二：本地开发部署

适合需要修改代码的开发者。

```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou/backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 1018 --reload
```

**首次启动说明：**
- FFmpeg 会自动下载（约 50MB）
- Chromium 浏览器会自动安装（约 150MB）
- 整个过程需要 5-10 分钟，请耐心等待

**访问地址：**
- 前端页面：http://localhost:1018（密码：tongzhou）
- 管理后台：http://localhost:1018/admin（密码：tzadmin）

**配置 API 密钥：**
访问管理后台，在"API配置"中填入你的 Gemini API 密钥（[获取地址](https://aistudio.google.com/app/apikey)）

---

## 🐳 Docker 部署详细说明

### 优势

- ✅ **零配置** - 无需安装 Python、FFmpeg、Chromium 等依赖
- ✅ **环境隔离** - 不污染系统环境
- ✅ **一键启动** - 一条命令即可运行
- ✅ **跨平台** - Windows/Linux/Mac 统一部署方式

### 前置要求

**安装 Docker 和 Docker Compose：**

**Ubuntu/Debian：**
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 重新登录使权限生效
exit
# 重新 SSH 登录

# 验证安装
docker --version
docker-compose --version
```

**CentOS/RHEL：**
```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 重新登录使权限生效
exit
# 重新 SSH 登录

# 验证安装
docker --version
docker-compose --version
```

**Windows：**
- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
- 启动 Docker Desktop

**Mac：**
- 下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
- 启动 Docker Desktop

### 部署步骤

```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 启动服务（首次构建需要 5-10 分钟）
docker-compose up -d

# 3. 查看启动日志
docker-compose logs -f

# 4. 等待服务启动完成
# 看到 "Application startup complete" 表示启动成功

# 5. 访问应用
# http://localhost:1018
```

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 进入容器调试
docker-compose exec tongzhou-video bash

# 更新代码后重新构建
git pull
docker-compose build --no-cache
docker-compose up -d
```

### 数据持久化

以下目录会自动挂载到宿主机，数据不会丢失：
- `backend/video_analysis.db` - 数据库文件
- `backend/downloads/` - 下载的视频
- `backend/compressed/` - 压缩后的视频
- `backend/preset_images/` - 预设图片
- `backend/api_config.yaml` - API 配置

**备份数据：**
```bash
# 备份数据库
cp backend/video_analysis.db backup/video_analysis_$(date +%Y%m%d).db

# 备份所有数据
tar -czf backup_$(date +%Y%m%d).tar.gz backend/video_analysis.db backend/downloads backend/preset_images
```

### 故障排查

**容器无法启动：**
```bash
# 查看详细日志
docker-compose logs

# 检查端口占用
sudo lsof -i :1018  # Linux/Mac
netstat -ano | findstr :1018  # Windows

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**数据丢失：**
```bash
# 检查挂载目录
docker-compose config

# 确保目录存在
ls -la backend/
```

---

## 🌐 生产环境部署

### 方式一：Docker 生产部署（推荐）

**1. 服务器准备**

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y  # CentOS/RHEL

# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 重新登录使权限生效
exit
```

**2. 部署应用**

```bash
# 克隆项目
cd /opt
sudo git clone https://github.com/zshiyee-bot/tongzhou.git
sudo chown -R $USER:$USER tongzhou
cd tongzhou

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

**3. 配置防火墙**

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 1018/tcp
sudo ufw enable
sudo ufw status

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=1018/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

**4. 配置 Nginx 反向代理（可选）**

```bash
# 安装 Nginx
sudo apt install -y nginx  # Ubuntu/Debian
sudo yum install -y nginx  # CentOS/RHEL

# 创建配置文件
sudo nano /etc/nginx/sites-available/tongzhou-video
```

配置内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:1018;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 3600s;
    }
}
```

启用配置：
```bash
# Ubuntu/Debian
sudo ln -s /etc/nginx/sites-available/tongzhou-video /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# CentOS/RHEL
sudo cp /etc/nginx/sites-available/tongzhou-video /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl restart nginx

# 开放 HTTP 端口
sudo ufw allow 80/tcp  # Ubuntu/Debian
sudo firewall-cmd --permanent --add-service=http && sudo firewall-cmd --reload  # CentOS/RHEL
```

**5. 配置 HTTPS（推荐）**

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu/Debian
sudo yum install -y certbot python3-certbot-nginx  # CentOS/RHEL

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

**6. 设置自动启动**

Docker Compose 已配置 `restart: unless-stopped`，容器会自动重启。

**7. 监控和日志**

```bash
# 查看容器状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看资源使用
docker stats tongzhou-video

# 设置日志轮转
sudo nano /etc/docker/daemon.json
```

添加：
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

重启 Docker：
```bash
sudo systemctl restart docker
docker-compose up -d
```

---

### 方式二：传统部署（不使用 Docker）

详细的传统部署指南请查看：[DEPLOY_LINUX.md](backend/DEPLOY_LINUX.md)

**快速步骤：**

```bash
# 1. 安装系统依赖
sudo apt install -y python3 python3-pip python3-venv git  # Ubuntu/Debian
sudo yum install -y python3 python3-pip git  # CentOS/RHEL

# 2. 克隆项目
cd /opt
sudo git clone https://github.com/zshiyee-bot/tongzhou.git
sudo chown -R $USER:$USER tongzhou
cd tongzhou/backend

# 3. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务（首次启动会自动安装 Chromium）
python -m uvicorn app.main:app --host 0.0.0.0 --port 1018
```

**配置 systemd 服务：**

```bash
sudo nano /etc/systemd/system/tongzhou-video.service
```

内容：
```ini
[Unit]
Description=Tongzhou Video Analysis Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/tongzhou/backend
Environment="PATH=/opt/tongzhou/backend/venv/bin"
ExecStart=/opt/tongzhou/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 1018 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl start tongzhou-video
sudo systemctl enable tongzhou-video
sudo systemctl status tongzhou-video
```

---

### 生产环境对比

| 特性 | Docker 部署 | 传统部署 |
|------|------------|---------|
| 部署难度 | ⭐ 简单 | ⭐⭐⭐ 复杂 |
| 环境隔离 | ✅ 完全隔离 | ❌ 共享系统 |
| 依赖管理 | ✅ 自动处理 | ⚠️ 手动安装 |
| 更新升级 | ✅ 一键重建 | ⚠️ 手动更新 |
| 资源占用 | ⚠️ 稍高 | ✅ 较低 |
| 故障恢复 | ✅ 自动重启 | ⚠️ 需配置 |
| 推荐场景 | 生产环境 | 开发调试 |

**推荐：** 生产环境使用 Docker 部署，开发环境使用传统部署。

---

## 🔧 使用说明

### 主应用

访问：`http://localhost:1018`

- **添加视频**：点击"添加视频"按钮，粘贴视频链接
- **工作表管理**：添加、切换、重命名、删除工作表
- **数据编辑**：双击单元格编辑，拖动表头调整列宽
- **预设配置**：配置产品信息和图片，AI 会生成仿写文案

### 管理后台

访问：`http://localhost:1018/admin`  
密码：`tzadmin`

#### 功能模块

1. **数据统计**
   - 总视频记录数
   - 工作表数量
   - 今日新增记录
   - AI分析完成率

2. **API配置管理**
   - 配置 Gemini API 密钥
   - 修改 API 地址和模型
   - 调整并发处理线程数（1-20）
   - ⚠️ 修改后需要重启后端生效

3. **密码管理**
   - 查看当前前端登录密码
   - 修改前端登录密码
   - 即时生效，无需重启

4. **危险操作**
   - 清空所有视频数据
   - 二次确认保护

---

## 📁 项目结构

```
tongzhou-videoAI/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API接口
│   │   ├── core/              # 核心配置
│   │   ├── integrations/      # 第三方集成
│   │   ├── repositories/      # 数据访问层
│   │   ├── services/          # 业务服务
│   │   └── main.py           # 应用入口
│   ├── downloads/             # 下载的视频
│   ├── compressed/            # 压缩后的视频
│   ├── preset_images/         # 预设图片
│   ├── Dockerfile            # Docker 镜像配置
│   ├── requirements.txt       # Python依赖
│   └── DEPLOY_LINUX.md       # Linux 部署指南
├── frontend/                  # 前端页面
│   ├── table-new.html        # 主页面
│   ├── admin.html            # 管理后台
│   └── tongzhou.png          # 网站图标
├── docker-compose.yml        # Docker Compose 配置
├── install.sh                # Linux/Mac 一键安装脚本
├── install.bat               # Windows 一键安装脚本
└── README.md                 # 项目说明
```

---

## 📝 常见问题

### Q: 如何配置API密钥？

A: 访问 `http://localhost:1018/admin`，在"API配置"中填入密钥，保存后重启后端

### Q: Docker 部署失败？

A: 确保 Docker 和 Docker Compose 已正确安装并运行。Windows 用户需要启动 Docker Desktop。

### Q: 视频下载失败？

A: 
1. 检查网络连接
2. 某些视频链接可能已失效（404错误）
3. 系统会自动使用浏览器下载插件作为备用方案

### Q: AI分析超时？

A: 
1. 信息密度大的视频（>1分钟）处理时间较长，已优化超时时间为10分钟
2. 可以在管理后台降低并发处理线程数

### Q: 如何更新代码？

A: 
```bash
# Docker 部署
git pull
docker-compose build
docker-compose up -d

# 本地部署
git pull
pip install -r backend/requirements.txt
# 重启服务
```

### Q: 数据会丢失吗？

A: 不会。Docker 部署会自动挂载数据目录，更新代码不影响数据。

---

## 🛠️ 技术栈

- **后端**: FastAPI + Python 3.11
- **前端**: 原生HTML + JavaScript
- **数据库**: SQLite
- **AI模型**: Google Gemini
- **视频解析**: yt-dlp + 浏览器下载插件
- **视频处理**: FFmpeg
- **容器化**: Docker + Docker Compose

---

## 🔐 安全建议

1. **修改管理员密码**：在管理后台的"密码管理"中修改
2. **保护API密钥**：不要在公开场合泄露API密钥
3. **使用HTTPS**：生产环境配置SSL证书（参考 DEPLOY_LINUX.md）
4. **配置防火墙**：只开放必要端口
5. **定期备份**：备份 `backend/video_analysis.db` 数据库文件

---

## 📄 开源协议

MIT License

---

## ⚠️ 免责声明

本项目仅用于技术学习和研究目的。请用户仅下载自己拥有版权或已获得合法授权的内容。用户应自行遵守所在地区的法律法规及各平台的服务条款，开发者不对用户的使用行为承担任何法律责任。
