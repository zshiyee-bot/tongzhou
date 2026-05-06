# 生产环境部署检查清单

## ✅ 已完成的清理

- [x] 删除测试脚本（test_*.py, deep_debug.py 等8个文件）
- [x] 删除临时JSON文件（douyin_item_info.json, share_page_item.json）
- [x] 删除测试视频和调试文件（test_baby_bed.mp4, video_page.html, 清理下载文件.bat）
- [x] 清理Python缓存文件（__pycache__, *.pyc）
- [x] 创建生产环境依赖文件（requirements.prod.txt，移除了pytest）

## ⚠️ 部署前需要手动处理

### 1. 清理测试数据
```bash
# 清空下载目录
rm -rf backend/downloads/*

# 清空压缩目录
rm -rf backend/compressed/*

# 删除开发数据库（生产环境会自动创建新的）
rm -f backend/data/app.db
```

### 2. 配置生产环境变量
复制 `.env.example` 创建新的 `.env` 文件，并配置生产环境的密钥：

```bash
# 生产环境必须修改的配置
JWT_SECRET=<生成一个强随机密钥>
DEEPSEEK_API_KEY=<你的实际API密钥>
STRIPE_SECRET_KEY=<你的Stripe生产密钥>
STRIPE_WEBHOOK_SECRET=<你的Stripe Webhook密钥>
STRIPE_PRICE_ID_MONTHLY=<你的价格ID>
FRONTEND_URL=<你的生产域名>
```

**生成强随机密钥的方法：**
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. 安装生产依赖
```bash
pip install -r requirements.prod.txt
```

### 4. 生产环境启动命令
```bash
# 不要使用 --reload 参数
python -m uvicorn app.main:app --host 0.0.0.0 --port 1018
```

或使用 gunicorn（推荐）：
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:1018
```

## 📋 安全检查清单

- [ ] 确保 `.env` 文件不会被提交到Git（已在.gitignore中配置）
- [ ] 修改所有默认密钥和API密钥
- [ ] 配置CORS允许的域名（当前设置为允许所有域名 `*`）
- [ ] 检查数据库备份策略
- [ ] 配置日志轮转和监控
- [ ] 设置防火墙规则
- [ ] 配置HTTPS证书

## 🔧 性能优化建议

1. **并发控制**：已在 `api_config.yaml` 中配置最大并发数
2. **数据库**：考虑使用PostgreSQL替代SQLite（生产环境）
3. **缓存**：考虑添加Redis缓存
4. **CDN**：静态文件使用CDN加速
5. **监控**：添加APM监控（如Sentry）

## 📦 Docker部署

项目已包含 `Dockerfile`，可以使用Docker部署：

```bash
docker build -t video-downloader .
docker run -d -p 1018:1018 --env-file .env video-downloader
```

## 🚀 部署后验证

1. 访问健康检查端点：`http://your-domain:1018/api/health`
2. 测试视频下载功能
3. 检查日志输出
4. 验证数据库连接
5. 测试AI分析功能（如果配置了API密钥）
