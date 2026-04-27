# 数据库更新指南

## 📖 概述

本项目使用版本化的数据库迁移系统，确保更新时数据不丢失。

## 🔄 如何添加新字段

### 步骤1：编写迁移函数

打开 `backend/app/repositories/migrations.py`，添加新的迁移函数：

```python
def migration_v5(conn):
    """版本5：添加标签字段。"""
    print("[迁移] 执行版本5：添加标签字段")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN tags TEXT")
    except Exception:
        pass
```

### 步骤2：注册迁移

在 `MIGRATIONS` 字典中添加新版本：

```python
MIGRATIONS = {
    1: migration_v1,
    2: migration_v2,
    3: migration_v3,
    4: migration_v4,
    5: migration_v5,  # 新增
}
```

### 步骤3：更新版本号

修改 `CURRENT_VERSION`：

```python
CURRENT_VERSION = 5  # 从 4 改为 5
```

### 步骤4：重启应用

```bash
cd backend
python main.py
```

启动时会自动执行新的迁移，控制台会显示：

```
[迁移] 当前数据库版本: 4
[迁移] 开始执行版本 5
[迁移] 执行版本5：添加标签字段
[迁移] 版本 5 执行完成
[迁移] 数据库已更新到版本 5
```

## ✅ 数据安全保证

1. **自动迁移**：启动时自动检测并执行未执行的迁移
2. **幂等性**：重复执行不会出错（使用 `ALTER TABLE IF NOT EXISTS`）
3. **版本追踪**：已执行的迁移记录在 `schema_migrations` 表中
4. **向后兼容**：只添加字段，不删除旧数据

## 📦 更新部署流程

### 本地开发环境更新

```bash
# 1. 拉取最新代码
git pull

# 2. 重启后端（迁移会自动执行）
cd backend
python main.py
```

### 生产服务器更新

```bash
# 1. 备份数据库（重要！）
cp backend/data/app.db backend/data/app.db.backup

# 2. 拉取最新代码
git pull

# 3. 更新Python依赖（如果有新依赖）
cd backend
pip install -r requirements.txt

# 4. 重启服务
python main.py
```

## 🛡️ 数据备份建议

### 自动备份脚本

创建 `backup.sh`：

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp backend/data/app.db backend/data/backups/app_${DATE}.db
echo "备份完成: app_${DATE}.db"

# 只保留最近7天的备份
find backend/data/backups/ -name "app_*.db" -mtime +7 -delete
```

### 定时备份（Linux/Mac）

```bash
# 添加到 crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

## 🔧 常见问题

### Q: 迁移失败怎么办？

A: 查看错误信息，通常是SQL语法错误。修复后重启应用会重新执行。

### Q: 如何回滚迁移？

A: 
1. 停止应用
2. 恢复备份：`cp backend/data/app.db.backup backend/data/app.db`
3. 回退代码到旧版本
4. 重启应用

### Q: 如何查看当前数据库版本？

A: 启动应用时会在控制台显示，或者查询数据库：

```sql
SELECT MAX(version) FROM schema_migrations;
```

## 📝 迁移示例

### 示例1：添加新字段

```python
def migration_v6(conn):
    """版本6：添加视频时长字段。"""
    print("[迁移] 执行版本6：添加视频时长字段")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN duration INTEGER DEFAULT 0")
    except Exception:
        pass
```

### 示例2：创建新表

```python
def migration_v7(conn):
    """版本7：创建评论表。"""
    print("[迁移] 执行版本7：创建评论表")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (video_id) REFERENCES video_records(id)
        )
    """)
```

### 示例3：添加索引

```python
def migration_v8(conn):
    """版本8：优化查询性能。"""
    print("[迁移] 执行版本8：添加索引")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_records_category ON video_records(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_records_created_at ON video_records(created_at)")
```

## 🚀 高级方案（可选）

如果项目规模扩大，可以考虑使用专业的迁移工具：

### Alembic（推荐）

```bash
# 安装
pip install alembic

# 初始化
alembic init alembic

# 创建迁移
alembic revision -m "add tags column"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

但对于当前项目，简单的版本管理系统已经足够。
