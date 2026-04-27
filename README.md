# 抖音视频AI分析系统

基于 FastAPI + Gemini AI 的抖音视频智能分析工具。支持视频自动下载、AI内容分析、多工作表管理等功能。

## ✨ 功能特性

- ✅ **抖音视频自动下载** - 支持抖音视频链接解析和下载
- ✅ **AI智能分析** - 自动识别品类、产品、黄金3秒、口播文案、爆款分析、画面分析
- ✅ **多工作表管理** - Excel风格的多工作表，支持添加、删除、重命名
- ✅ **实时流式更新** - SSE流式推送，实时显示处理进度
- ✅ **Excel风格编辑** - 可调整列宽、自定义列、双击编辑
- ✅ **数据持久化** - SQLite数据库存储，支持跨浏览器同步
- ✅ **自动恢复机制** - 刷新页面后自动检测未完成任务并继续处理

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/SummaVideo.git
cd SummaVideo
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 启动服务

```bash
python main.py
```

看到以下输出说明启动成功：

```
INFO:     Uvicorn running on http://0.0.0.0:1018
INFO:     Application startup complete.
```

### 4. 配置API密钥（首次使用）

**方式1：通过管理后台配置（推荐）**

1. 访问管理后台：`http://localhost:1018/admin`
2. 输入管理员密码：`tzadmin`
3. 切换到"API配置"标签
4. 填入你的Gemini API密钥（在 https://aistudio.google.com/app/apikey 获取）
5. 点击"保存配置"
6. 重启后端服务

**方式2：手动编辑配置文件**

编辑 `backend/api_config.yaml`：

```yaml
apis:
  gemini:
    api_key: "你的Gemini API密钥"
```

### 5. 访问应用

打开浏览器访问：

```
http://localhost:1018
```

默认密码：`tongzhou`（可在管理后台修改）

## 📁 项目结构

```
SummaVideo/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── api/               # API接口
│   │   │   └── endpoints/     
│   │   │       ├── health.py          # 健康检查
│   │   │       ├── video_records.py   # 视频记录管理
│   │   │       └── sheets.py          # 工作表管理
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── lifespan.py    # 应用生命周期
│   │   │   └── logging.py     # 日志配置
│   │   ├── integrations/      # 第三方集成
│   │   │   ├── douyin_client.py   # 抖音视频解析
│   │   │   └── yt_dlp_client.py   # 通用视频下载
│   │   ├── repositories/      # 数据访问层
│   │   │   ├── db.py              # 数据库操作
│   │   │   └── migrations.py      # 数据库迁移
│   │   ├── schemas/           # 数据模型
│   │   │   └── video_record.py
│   │   ├── services/          # 业务服务
│   │   │   ├── gemini_video_analyzer.py  # AI视频分析
│   │   │   └── video_compressor.py       # 视频压缩
│   │   └── main.py           # 应用入口
│   ├── data/                  # 数据库文件（不提交）
│   ├── downloads/             # 下载的视频（不提交）
│   ├── compressed/            # 压缩后的视频（不提交）
│   ├── api_config.yaml        # API配置（不提交）
│   ├── api_config.yaml.example # 配置模板
│   ├── requirements.txt       # Python依赖
│   └── main.py               # 启动入口
├── frontend/                  # 前端页面
│   ├── table-new.html        # 主页面
│   └── tongzhou.png          # 网站图标
├── .gitignore                # Git忽略文件
├── README.md                 # 项目说明
└── DATABASE_MIGRATION.md     # 数据库迁移指南
```

## 🔧 使用说明

### 主应用

访问：`http://localhost:1018`

- **添加视频**：点击"添加视频"按钮，粘贴抖音视频链接
- **工作表管理**：添加、切换、重命名、删除工作表
- **数据编辑**：双击单元格编辑，拖动表头调整列宽

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
   - 修改Gemini API密钥
   - 修改API地址和模型
   - 切换不同的API配置
   - ⚠️ 修改后需要重启后端生效

3. **密码管理**
   - 查看当前前端登录密码
   - 修改前端登录密码
   - 即时生效，无需重启

4. **危险操作**
   - 清空所有视频数据
   - 二次确认保护

## 🌐 生产环境部署

### 方式1：直接部署

```bash
# 1. 上传代码到服务器
scp -r SummaVideo user@your-server:/path/to/

# 2. SSH登录服务器
ssh user@your-server

# 3. 安装依赖
cd /path/to/SummaVideo/backend
pip install -r requirements.txt

# 4. 配置API密钥
cp api_config.yaml.example api_config.yaml
nano api_config.yaml

# 5. 启动服务（使用 nohup 后台运行）
nohup python main.py > app.log 2>&1 &

# 6. 访问
http://your-server-ip:1018
```

### 方式2：使用 systemd（推荐）

创建服务文件 `/etc/systemd/system/summavideo.service`：

```ini
[Unit]
Description=SummaVideo Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/SummaVideo/backend
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable summavideo
sudo systemctl start summavideo
sudo systemctl status summavideo
```

### 方式3：使用 Nginx 反向代理

配置 `/etc/nginx/sites-available/summavideo`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:1018;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 🔄 数据库更新

项目使用版本化的数据库迁移系统，更新时数据不会丢失。

详细说明请查看：[DATABASE_MIGRATION.md](DATABASE_MIGRATION.md)

### 添加新字段示例

```python
# 1. 在 backend/app/repositories/migrations.py 中添加
def migration_v5(conn):
    print("[迁移] 执行版本5：添加标签字段")
    conn.execute("ALTER TABLE video_records ADD COLUMN tags TEXT")

# 2. 注册到 MIGRATIONS 字典
MIGRATIONS = {
    # ...
    5: migration_v5,
}

# 3. 更新版本号
CURRENT_VERSION = 5

# 4. 重启应用，自动执行迁移
```

## 🔐 安全建议

1. **修改管理员密码**：编辑 `backend/app/api/endpoints/admin.py` 中的 `ADMIN_PASSWORD`
2. **修改前端密码**：在管理后台的"密码管理"中修改
3. **使用HTTPS**：生产环境配置SSL证书
4. **定期备份**：备份 `backend/data/app.db` 数据库文件
5. **保护API密钥**：不要在公开场合泄露API密钥

## 📝 常见问题

### Q: 如何配置API密钥？

A: 访问 `http://localhost:1018/admin`，在"API配置"中填入密钥，保存后重启后端

### Q: 如何修改前端登录密码？

A: 访问 `http://localhost:1018/admin`，在"密码管理"中修改，立即生效

### Q: 如何添加新字段？

A: 参考 `DATABASE_MIGRATION.md` 文档

### Q: 视频下载失败？

A: 检查网络连接，确保可以访问抖音

### Q: AI分析失败？

A: 检查 `api_config.yaml` 中的API密钥是否正确，以及API额度是否充足

### Q: 刷新页面后数据丢失？

A: 检查后端是否正常运行，数据库文件是否存在

## 🛠️ 技术栈

- **后端**: FastAPI + Python 3.10+
- **前端**: 原生HTML + JavaScript
- **数据库**: SQLite
- **AI模型**: Google Gemini
- **视频解析**: yt-dlp + 抖音专用解析器
- **视频处理**: FFmpeg

## 📄 开源协议

MIT License

## 📞 技术支持

- 问题反馈：[GitHub Issues](https://github.com/你的用户名/SummaVideo/issues)
- 数据库迁移：查看 `DATABASE_MIGRATION.md`

## ⚠️ 免责声明

本项目仅用于技术学习和研究目的。请用户仅下载自己拥有版权或已获得合法授权的内容。用户应自行遵守所在地区的法律法规及各平台的服务条款，开发者不对用户的使用行为承担任何法律责任。
