"""数据库访问层（Repository）。

职责:
- 管理 SQLite 连接与数据库初始化
- 提供视频记录和工作表的数据访问

边界:
- 仅负责数据持久化与查询，不包含业务编排逻辑
- 所有写操作通过 get_db 上下文管理器自动提交/回滚
"""

import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "app.db")


def get_db_path():
    """获取数据库文件路径，确保父目录存在。

    Returns:
        数据库文件的绝对路径。
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    """获取 SQLite 数据库连接的上下文管理器。

    启用 WAL 日志模式和外键约束，退出时自动提交或回滚。

    Yields:
        sqlite3.Connection: 配置了 Row 工厂的数据库连接。

    Raises:
        事务中发生的任何异常均会触发回滚后重新抛出。
    """
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表结构与索引。

    创建 video_records 和 sheets 表（IF NOT EXISTS），并建立常用查询索引。
    可安全重复调用，不会覆盖已有数据。
    """
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS video_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_url TEXT NOT NULL,
                video_file_path TEXT,
                video_time TEXT,
                category TEXT,
                product TEXT,
                golden_3s_copy TEXT,
                transcript TEXT,
                video_copy TEXT,
                viral_analysis TEXT,
                scene_analysis TEXT,
                exposure INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                collects INTEGER DEFAULT 0,
                remarks TEXT,
                sheet_id TEXT DEFAULT 'sheet1',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sheets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                position INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sheet_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id TEXT NOT NULL UNIQUE,
                product_name TEXT,
                product_description TEXT,
                product_image_paths TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (sheet_id) REFERENCES sheets(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_video_records_url ON video_records(video_url);
            CREATE INDEX IF NOT EXISTS idx_video_records_sheet_id ON video_records(sheet_id);
            CREATE INDEX IF NOT EXISTS idx_sheet_presets_sheet_id ON sheet_presets(sheet_id);
        """)

        # 迁移：为已存在的表添加新列
        try:
            conn.execute("ALTER TABLE video_records ADD COLUMN category TEXT")
        except Exception:
            pass

        try:
            conn.execute("ALTER TABLE video_records ADD COLUMN product TEXT")
        except Exception:
            pass

        try:
            conn.execute("ALTER TABLE video_records ADD COLUMN scene_analysis TEXT")
        except Exception:
            pass

        try:
            conn.execute("ALTER TABLE video_records ADD COLUMN sheet_id TEXT DEFAULT 'sheet1'")
        except Exception:
            pass

        # 添加文案仿写列
        try:
            conn.execute("ALTER TABLE video_records ADD COLUMN copywriting TEXT")
        except Exception:
            pass

        # 迁移：将 product_image_path 改为 product_image_paths（支持多图）
        try:
            # 检查是否已经是新字段
            cursor = conn.execute("PRAGMA table_info(sheet_presets)")
            columns = [row[1] for row in cursor.fetchall()]
            if "product_image_path" in columns and "product_image_paths" not in columns:
                # 创建新表
                conn.execute("""
                    CREATE TABLE sheet_presets_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sheet_id TEXT NOT NULL UNIQUE,
                        product_name TEXT,
                        product_description TEXT,
                        product_image_paths TEXT,
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        FOREIGN KEY (sheet_id) REFERENCES sheets(id) ON DELETE CASCADE
                    )
                """)
                # 迁移数据（将单个路径转为 JSON 数组）
                conn.execute("""
                    INSERT INTO sheet_presets_new (id, sheet_id, product_name, product_description, product_image_paths, created_at, updated_at)
                    SELECT id, sheet_id, product_name, product_description,
                           CASE WHEN product_image_path IS NOT NULL THEN '["' || product_image_path || '"]' ELSE NULL END,
                           created_at, updated_at
                    FROM sheet_presets
                """)
                # 删除旧表，重命名新表
                conn.execute("DROP TABLE sheet_presets")
                conn.execute("ALTER TABLE sheet_presets_new RENAME TO sheet_presets")
                print("[数据库迁移] sheet_presets 表已更新为支持多图")
        except Exception as e:
            print(f"[数据库迁移] sheet_presets 迁移跳过或失败: {e}")
            pass

        # 初始化默认工作表
        try:
            conn.execute("INSERT OR IGNORE INTO sheets (id, name, position) VALUES ('sheet1', '工作表1', 0)")
        except Exception:
            pass
