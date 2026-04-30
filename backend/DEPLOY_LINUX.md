# Linux 生产环境部署指南

## 系统要求

- Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- Python 3.8+
- 至少 2GB 内存
- 至少 5GB 磁盘空间

## 1. 安装系统依赖

### Ubuntu/Debian

```bash
# 更新包列表
sudo apt update

# 安装 Python 和基础工具
sudo apt install -y python3 python3-pip python3-venv git

# 安装 Playwright Chromium 所需的系统库
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0
```

### CentOS/RHEL

```bash
# 安装 EPEL 仓库
sudo yum install -y epel-release

# 安装 Python 和基础工具
sudo yum install -y python3 python3-pip git

# 安装 Playwright Chromium 所需的系统库
sudo yum install -y \
    nss \
    nspr \
    atk \
    at-spi2-atk \
    cups-libs \
    libdrm \
    dbus-libs \
    libxkbcommon \
    libXcomposite \
    libXdamage \
    libXfixes \
    libXrandr \
    mesa-libgbm \
    pango \
    cairo \
    alsa-lib
```

## 2. 克隆项目

```bash
cd /opt
sudo git clone https://github.com/zshiyee-bot/tongzhou.git
sudo chown -R $USER:$USER tongzhou
cd tongzhou/backend
```

## 3. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

## 4. 安装 Python 依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 5. 配置防火墙

### 使用 firewalld（CentOS/RHEL）

```bash
# 开放后端端口
sudo firewall-cmd --permanent --add-port=1018/tcp
sudo firewall-cmd --reload

# 验证
sudo firewall-cmd --list-ports
```

### 使用 ufw（Ubuntu/Debian）

```bash
# 开放后端端口
sudo ufw allow 1018/tcp

# 如果 ufw 未启用
sudo ufw enable

# 验证
sudo ufw status
```

### 使用 iptables

```bash
# 开放后端端口
sudo iptables -A INPUT -p tcp --dport 1018 -j ACCEPT

# 保存规则
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## 6. 配置 API 密钥

访问管理后台配置 Gemini API：
```
http://your-server-ip:1018/admin
```

或手动编辑配置文件：
```bash
nano api_config.yaml
```

## 7. 启动服务

### 开发模式（测试用）

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 1018 --reload
```

### 生产模式（推荐使用 systemd）

创建 systemd 服务文件：

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
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start tongzhou-video

# 设置开机自启
sudo systemctl enable tongzhou-video

# 查看状态
sudo systemctl status tongzhou-video

# 查看日志
sudo journalctl -u tongzhou-video -f
```

## 8. 配置 Nginx 反向代理（可选）

安装 Nginx：

```bash
# Ubuntu/Debian
sudo apt install -y nginx

# CentOS/RHEL
sudo yum install -y nginx
```

创建配置文件：

```bash
sudo nano /etc/nginx/sites-available/tongzhou-video
```

内容：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    client_max_body_size 500M;  # 允许上传大文件

    location / {
        proxy_pass http://127.0.0.1:1018;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }
}
```

启用配置：

```bash
# Ubuntu/Debian
sudo ln -s /etc/nginx/sites-available/tongzhou-video /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx

# 开放 HTTP/HTTPS 端口
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 9. 配置 HTTPS（可选但推荐）

使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu/Debian
sudo yum install -y certbot python3-certbot-nginx  # CentOS/RHEL

# 获取证书并自动配置 Nginx
sudo certbot --nginx -d your-domain.com

# 自动续期（certbot 会自动添加 cron 任务）
sudo certbot renew --dry-run
```

## 10. 首次启动说明

**重要：** 首次启动时，系统会自动下载安装：
1. **FFmpeg**（约 50MB）- 用于视频压缩
2. **Chromium 浏览器**（约 150MB）- 用于浏览器下载插件

这个过程可能需要 5-10 分钟，请耐心等待。你会在日志中看到：

```
[启动检查] 检查 Playwright Chromium 安装状态...
[启动检查] Chromium 未安装，正在自动安装...
[启动检查] 这可能需要几分钟时间（约150MB），请稍候...
[启动检查] ✓ Chromium 安装成功
```

## 11. 常见问题

### Chromium 启动失败

如果看到 `Failed to launch browser` 错误，手动安装系统依赖：

```bash
# Ubuntu/Debian
sudo playwright install-deps chromium

# CentOS/RHEL（需要手动安装依赖，见步骤1）
```

### 端口被占用

```bash
# 查看端口占用
sudo lsof -i :1018

# 或
sudo netstat -tulpn | grep 1018

# 杀死占用进程
sudo kill -9 <PID>
```

### 权限问题

```bash
# 确保目录权限正确
sudo chown -R $USER:$USER /opt/tongzhou

# 确保虚拟环境可执行
chmod +x /opt/tongzhou/backend/venv/bin/*
```

### 内存不足

如果服务器内存小于 2GB，建议：
1. 减少 uvicorn workers 数量（改为 2 或 1）
2. 在 `api_config.yaml` 中降低 `max_concurrency`（改为 2-3）

## 12. 监控和维护

### 查看日志

```bash
# systemd 服务日志
sudo journalctl -u tongzhou-video -f

# 或查看应用日志
tail -f /opt/tongzhou/backend/logs/*.log
```

### 更新代码

```bash
cd /opt/tongzhou
git pull origin main
source backend/venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart tongzhou-video
```

### 备份数据库

```bash
# 备份 SQLite 数据库
cp /opt/tongzhou/backend/video_analysis.db /backup/video_analysis_$(date +%Y%m%d).db

# 备份预设图片
tar -czf /backup/preset_images_$(date +%Y%m%d).tar.gz /opt/tongzhou/backend/preset_images
```

## 13. 性能优化

### 使用 Gunicorn（推荐）

```bash
pip install gunicorn

# 修改 systemd 服务文件中的 ExecStart
ExecStart=/opt/tongzhou/backend/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:1018 \
    --timeout 600 \
    --access-logfile /var/log/tongzhou/access.log \
    --error-logfile /var/log/tongzhou/error.log
```

### 配置日志轮转

```bash
sudo nano /etc/logrotate.d/tongzhou-video
```

内容：

```
/var/log/tongzhou/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 your-username your-username
    sharedscripts
    postrotate
        systemctl reload tongzhou-video > /dev/null 2>&1 || true
    endscript
}
```

## 14. 安全建议

1. **修改默认管理员密码**（在管理后台）
2. **配置防火墙**，只开放必要端口
3. **使用 HTTPS**（Let's Encrypt 免费证书）
4. **定期更新系统和依赖**
5. **配置日志监控**（如 fail2ban）
6. **限制上传文件大小**（Nginx `client_max_body_size`）

## 支持

如有问题，请查看：
- GitHub Issues: https://github.com/zshiyee-bot/tongzhou/issues
- 日志文件: `sudo journalctl -u tongzhou-video -f`
