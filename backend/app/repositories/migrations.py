"""数据库迁移管理。

使用方法：
1. 添加新字段时，在 MIGRATIONS 列表中添加新的迁移函数
2. 启动应用时会自动执行未执行的迁移
3. 已执行的迁移会记录在 schema_migrations 表中
"""

from app.repositories.db import get_db


# 当前数据库版本
CURRENT_VERSION = 4


def get_db_version():
    """获取当前数据库版本。"""
    with get_db() as conn:
        # 创建版本表（如果不存在）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now'))
            )
        """)

        row = conn.execute("SELECT MAX(version) as v FROM schema_migrations").fetchone()
        return row["v"] if row["v"] is not None else 0


def migration_v1(conn):
    """版本1：添加 category 和 product 字段。"""
    print("[迁移] 执行版本1：添加品类和产品字段")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN category TEXT")
    except Exception:
        pass

    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN product TEXT")
    except Exception:
        pass


def migration_v2(conn):
    """版本2：添加 scene_analysis 字段。"""
    print("[迁移] 执行版本2：添加画面分析字段")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN scene_analysis TEXT")
    except Exception:
        pass


def migration_v3(conn):
    """版本3：添加 sheet_id 字段和 sheets 表。"""
    print("[迁移] 执行版本3：添加工作表功能")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN sheet_id TEXT DEFAULT 'sheet1'")
    except Exception:
        pass

    # 创建 sheets 表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sheets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            position INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # 初始化默认工作表
    conn.execute("INSERT OR IGNORE INTO sheets (id, name, position) VALUES ('sheet1', '工作表1', 0)")


def migration_v4(conn):
    """版本4：添加索引优化查询性能。"""
    print("[迁移] 执行版本4：添加数据库索引")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_records_sheet_id ON video_records(sheet_id)")


# 迁移列表：按版本号顺序排列
MIGRATIONS = {
    1: migration_v1,
    2: migration_v2,
    3: migration_v3,
    4: migration_v4,
}


def run_migrations():
    """执行所有未执行的迁移。"""
    current_version = get_db_version()
    print(f"[迁移] 当前数据库版本: {current_version}")

    if current_version >= CURRENT_VERSION:
        print("[迁移] 数据库已是最新版本")
        return

    with get_db() as conn:
        for version in range(current_version + 1, CURRENT_VERSION + 1):
            if version in MIGRATIONS:
                print(f"[迁移] 开始执行版本 {version}")
                MIGRATIONS[version](conn)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                print(f"[迁移] 版本 {version} 执行完成")

    print(f"[迁移] 数据库已更新到版本 {CURRENT_VERSION}")


# 示例：如何添加新迁移
"""
假设你要添加一个新字段 'tags'：

1. 定义新的迁移函数：
def migration_v5(conn):
    print("[迁移] 执行版本5：添加标签字段")
    try:
        conn.execute("ALTER TABLE video_records ADD COLUMN tags TEXT")
    except Exception:
        pass

2. 添加到 MIGRATIONS 字典：
MIGRATIONS = {
    1: migration_v1,
    2: migration_v2,
    3: migration_v3,
    4: migration_v4,
    5: migration_v5,  # 新增
}

3. 更新 CURRENT_VERSION：
CURRENT_VERSION = 5

4. 重启应用，迁移会自动执行
"""
