# 视频分析系统

基于 FastAPI + Gemini AI 的智能视频分析工具。支持视频自动下载、AI内容分析、多工作表管理等功能。

**🐳 推荐使用 Docker 一键部署，3 分钟即可运行！**

## ✨ 功能特性

- ✅ **视频自动下载** - 支持抖音等平台视频链接解析和下载
- ✅ **AI智能分析** - 自动识别品类、产品、黄金3秒、口播文案、爆款分析、画面分析
- ✅ **多工作表管理** - Excel风格的多工作表，支持添加、删除、重命名
- ✅ **实时流式更新** - SSE流式推送，实时显示处理进度
- ✅ **Excel风格编辑** - 可调整列宽、自定义列、双击编辑
- ✅ **数据持久化** - SQLite数据库存储，支持跨浏览器同步
- ✅ **自动恢复机制** - 刷新页面后自动检测未完成任务并继续处理
- ✅ **Docker 支持** - 一键部署，无需配置环境

## 🚀 快速开始

### 方式一：一键安装（推荐，最简单）

**Windows 用户：**
```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 双击运行
install.bat
```

**Linux/Mac 用户：**
```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 运行安装脚本
chmod +x install.sh
./install.sh
```

**就这么简单！** 脚本会自动：
- ✅ 检查 Docker 环境
- ✅ 创建必要的目录
- ✅ 构建 Docker 镜像（包含所有依赖）
- ✅ 启动服务

安装完成后访问：
- 前端页面：http://localhost:1018
- 管理后台：http://localhost:1018/admin（默认密码：admin123）

---

### 方式二：手动 Docker 部署

```bash
# 1. 克隆项目
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou

# 2. 启动服务
docker-compose up -d

# 3. 访问应用
# http://localhost:1018
```

---

### 方式三：本地开发部署

适合需要修改代码的开发者。

#### 1. 克隆项目

```bash
git clone https://github.com/zshiyee-bot/tongzhou.git
cd tongzhou/backend
```

#### 2. 安装依赖

```bash
pip install -r requirements.txt
```

#### 3. 启动服务

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 1018 --reload
```

**首次启动说明：**
- FFmpeg 会自动下载（约 50MB）
- Chromium 浏览器会自动安装（约 150MB）
- 整个过程需要 5-10 分钟，请耐心等待

#### 4. 访问应用

- 前端页面：http://localhost:1018
- 管理后台：http://localhost:1018/admin（默认密码：admin123）

#### 5. 配置 API 密钥

访问管理后台，在"API配置"中填入你的 Gemini API 密钥（[获取地址](https://aistudio.google.com/app/apikey)）

---

## 🐳 Docker 部署详细说明

### 优势

- ✅ **零配置** - 无需安装 Python、FFmpeg、Chromium 等依赖
- ✅ **环境隔离** - 不污染系统环境
- ✅ **一键启动** - 一条命令即可运行
- ✅ **跨平台** - Windows/Linux/Mac 统一部署方式

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新代码后重新构建
git pull
docker-compose build
docker-compose up -d
```

### 数据持久化

以下目录会自动挂载到宿主机，数据不会丢失：
- `backend/video_analysis.db` - 数据库文件
- `backend/downloads/` - 下载的视频
- `backend/compressed/` - 压缩后的视频
- `backend/preset_images/` - 预设图片
- `backend/api_config.yaml` - API 配置

---

## 🌐 生产环境部署

### Linux 服务器部署

详细的 Linux 部署指南请查看：[DEPLOY_LINUX.md](backend/DEPLOY_LINUX.md)

包含：
- 系统依赖安装（Ubuntu/CentOS）
- 防火墙配置
- systemd 服务配置
- Nginx 反向代理
- HTTPS 证书配置
- 性能优化建议

### 快速部署（使用一键脚本）

```bash
# 1. 上传项目到服务器
scp -r tongzhou user@your-server:/opt/

# 2. SSH 登录服务器
ssh user@your-server

# 3. 运行安装脚本
cd /opt/tongzhou
chmod +x install.sh
./install.sh

# 4. 配置防火墙
sudo firewall-cmd --permanent --add-port=1018/tcp
sudo firewall-cmd --reload

# 5. 访问
http://your-server-ip:1018
```

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
默认密码：`admin123`

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
