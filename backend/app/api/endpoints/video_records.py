"""视频记录管理 API。"""

import asyncio
import time
import random
import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.repositories.db import get_db
from app.schemas.video_record import VideoRecordCreate, VideoRecordUpdate, VideoRecordResponse
from app.integrations.yt_dlp_client import downloader
from app.integrations.douyin_client import douyin_parser, is_douyin_url


router = APIRouter()

# 全局字典：存储每个记录的 AI 分析更新队列
ai_update_queues = {}


def download_with_retry(url: str, filepath, max_retries: int = 3):
    """
    带智能重试机制的视频下载函数，模拟真实用户行为以避免反爬虫识别。

    策略：
    - 随机延迟（模拟人类思考时间）
    - 指数退避（每次失败后等待时间递增）
    - User-Agent 轮换
    - SSL 错误专门处理
    """
    import requests

    # 多个真实浏览器 User-Agent 池
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    for attempt in range(max_retries):
        try:
            # 第一次请求前添加随机延迟（模拟用户浏览行为）
            if attempt > 0:
                # 指数退避：1-3秒、2-5秒、4-8秒
                base_delay = 2 ** attempt
                jitter = random.uniform(0, base_delay)
                wait_time = base_delay + jitter
                print(f"[下载重试] 第 {attempt + 1} 次重试，等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
            else:
                # 首次请求也添加小延迟（0.5-1.5秒），模拟真实用户
                time.sleep(random.uniform(0.5, 1.5))

            # 随机选择 User-Agent
            headers = {
                "User-Agent": random.choice(user_agents),
                "Referer": "https://www.douyin.com/",
                "Accept": "video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }

            # 发起请求，增加超时时间
            response = requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(10, 120),  # (连接超时, 读取超时)
                verify=True  # 启用 SSL 验证
            )
            response.raise_for_status()

            # 下载文件
            downloaded_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

            print(f"[下载成功] 已下载 {downloaded_size / 1024 / 1024:.2f} MB")
            return True

        except requests.exceptions.SSLError as e:
            print(f"[下载失败] SSL 错误 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt == max_retries - 1:
                raise Exception(f"SSL 连接失败，已重试 {max_retries} 次")

        except requests.exceptions.Timeout as e:
            print(f"[下载失败] 超时 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt == max_retries - 1:
                raise Exception(f"下载超时，已重试 {max_retries} 次")

        except requests.exceptions.ConnectionError as e:
            print(f"[下载失败] 连接错误 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt == max_retries - 1:
                raise Exception(f"网络连接失败，已重试 {max_retries} 次")

        except Exception as e:
            print(f"[下载失败] 未知错误 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}")
            if attempt == max_retries - 1:
                raise

    return False


@router.get("/api/video-records", response_model=List[VideoRecordResponse])
async def get_video_records(sheet_id: str = None):
    """获取视频记录，可按工作表筛选。"""
    with get_db() as conn:
        if sheet_id:
            rows = conn.execute(
                "SELECT * FROM video_records WHERE sheet_id = ? ORDER BY id DESC",
                (sheet_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM video_records ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]


@router.post("/api/video-records")
async def create_video_record(req: VideoRecordCreate):
    """创建视频记录并流式推送进度更新。支持批量创建多个视频。"""
    from sse_starlette.sse import EventSourceResponse
    from app.utils.url_extractor import extract_all_urls, is_video_url

    async def event_generator():
        loop = asyncio.get_event_loop()

        try:
            # 1. 提取所有视频链接
            all_urls = extract_all_urls(req.video_url)
            video_urls = [url for url in all_urls if is_video_url(url)]

            if not video_urls:
                # 如果没有识别到视频链接，使用原始输入
                video_urls = [req.video_url]

            print(f"[视频记录] 识别到 {len(video_urls)} 个视频链接")

            # 2. 为每个视频链接创建记录并处理
            for idx, video_url in enumerate(video_urls, 1):
                print(f"[视频记录] 处理第 {idx}/{len(video_urls)} 个视频: {video_url}")

                record_id = None

                try:
                    # 创建空记录
                    with get_db() as conn:
                        cursor = conn.execute(
                            """INSERT INTO video_records (video_url, sheet_id) VALUES (?, ?)""",
                            (video_url, req.sheet_id)
                        )
                        record_id = cursor.lastrowid

                        # 查询新创建的记录
                        row = conn.execute(
                            "SELECT * FROM video_records WHERE id = ?", (record_id,)
                        ).fetchone()

                        # 推送初始记录
                        yield {
                            "event": "created",
                            "data": json.dumps(dict(row), ensure_ascii=False)
                        }

                    # 解析视频信息
                    yield {
                        "event": "status",
                        "data": json.dumps({"message": f"正在解析视频信息... ({idx}/{len(video_urls)})"}, ensure_ascii=False)
                    }

                    if is_douyin_url(video_url):
                        video_info = await loop.run_in_executor(None, douyin_parser.parse, video_url)
                    else:
                        video_info = await loop.run_in_executor(None, downloader.parse_video, video_url)

                    # 提取基本信息
                    video_time = None
                    if video_info.get("upload_date"):
                        try:
                            upload_date = video_info["upload_date"]
                            video_time = datetime.strptime(upload_date, "%Y%m%d").isoformat()
                        except Exception:
                            pass

                    video_copy = video_info.get("description", "")[:500] if video_info.get("description") else ""
                    if not video_copy:
                        video_copy = video_info.get("title", "")[:500]

                    likes = video_info.get("like_count", 0) or 0
                    comments = video_info.get("comment_count", 0) or 0
                    shares = video_info.get("share_count", 0) or 0
                    collects = video_info.get("collect_count", 0) or 0

                    # 更新数据库并推送基本信息
                    with get_db() as conn:
                        conn.execute(
                            """UPDATE video_records
                               SET video_time = ?, video_copy = ?, likes = ?, comments = ?, shares = ?, collects = ?, updated_at = datetime('now')
                               WHERE id = ?""",
                            (video_time, video_copy, likes, comments, shares, collects, record_id)
                        )

                        row = conn.execute(
                            "SELECT * FROM video_records WHERE id = ?", (record_id,)
                        ).fetchone()

                        # 推送基本信息更新
                        yield {
                            "event": "basic_info",
                            "data": json.dumps(dict(row), ensure_ascii=False)
                        }

                    # 3. 下载视频
                    yield {
                        "event": "status",
                        "data": json.dumps({"message": f"正在下载视频... ({idx}/{len(video_urls)})"}, ensure_ascii=False)
                    }

                    video_file_path = ""
                    try:
                        formats = video_info.get("formats", [])
                        if formats and len(formats) > 0:
                            direct_url = formats[0].get("_direct_url") or formats[0].get("url")

                            if direct_url:
                                import requests
                                from pathlib import Path

                                title = video_info.get("title", "video")
                                safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:60]
                                filename = f"{safe_title}_{record_id}.mp4"  # 添加 record_id 避免文件名冲突

                                download_dir = Path(__file__).parent.parent.parent.parent / "downloads"
                                download_dir.mkdir(parents=True, exist_ok=True)
                                filepath = download_dir / filename

                                download_with_retry(direct_url, filepath, max_retries=3)
                                video_file_path = str(filepath)

                                # 更新视频文件路径
                                with get_db() as conn:
                                    conn.execute(
                                        "UPDATE video_records SET video_file_path = ?, updated_at = datetime('now') WHERE id = ?",
                                        (video_file_path, record_id)
                                    )

                                    row = conn.execute(
                                        "SELECT * FROM video_records WHERE id = ?", (record_id,)
                                    ).fetchone()

                                    # 推送下载完成
                                    yield {
                                        "event": "video_downloaded",
                                        "data": json.dumps(dict(row), ensure_ascii=False)
                                    }

                                # 4. 启动后台 AI 分析任务
                                yield {
                                    "event": "status",
                                    "data": json.dumps({"message": f"AI 分析已启动... ({idx}/{len(video_urls)})"}, ensure_ascii=False)
                                }

                                from app.services.video_compressor import compressor
                                from app.services.gemini_video_analyzer import analyzer

                                def compress_and_analyze():
                                    try:
                                        import os
                                        from app.repositories.db import get_db

                                        print(f"[视频记录] 开始压缩视频: {os.path.basename(video_file_path)}")
                                        compress_result = compressor.compress_video(video_file_path, "medium", 1280)

                                        if compress_result:
                                            print(f"[视频记录] 压缩完成，开始 AI 分析")
                                        else:
                                            print(f"[视频记录] 压缩失败，使用原视频进行 AI 分析")

                                        if analyzer.is_available():
                                            print(f"[视频记录] 开始 AI 分析视频")
                                            analysis_result = analyzer.analyze_compressed_video(video_file_path)

                                            if analysis_result:
                                                print(f"[视频记录] AI 分析完成，更新数据库")
                                                with get_db() as conn:
                                                    category = analysis_result.get("category", "")
                                                    product = analysis_result.get("product", "")
                                                    golden_3s = analysis_result.get("golden_3s", "")
                                                    transcript = analysis_result.get("transcript", "")
                                                    viral_analysis = analysis_result.get("viral_analysis", "")
                                                    scenes = analysis_result.get("scenes", "")

                                                    conn.execute(
                                                        """UPDATE video_records
                                                           SET category = ?, product = ?, golden_3s_copy = ?, transcript = ?, viral_analysis = ?, scene_analysis = ?, updated_at = datetime('now')
                                                           WHERE id = ?""",
                                                        (category, product, golden_3s, transcript, viral_analysis, scenes, record_id)
                                                    )
                                                print(f"[视频记录] 记录 {record_id} 的 AI 分析结果已保存")

                                                # 推送到 SSE 队列
                                                if record_id in ai_update_queues:
                                                    try:
                                                        ai_update_queues[record_id].put_nowait({
                                                            "category": category,
                                                            "product": product,
                                                            "golden_3s_copy": golden_3s,
                                                            "transcript": transcript,
                                                            "viral_analysis": viral_analysis,
                                                            "scene_analysis": scenes
                                                        })
                                                        print(f"[视频记录] 已推送 AI 分析结果到前端")
                                                    except Exception as e:
                                                        print(f"[视频记录] 推送失败: {e}")
                                            else:
                                                print(f"[视频记录] AI 分析失败")
                                        else:
                                            print(f"[视频记录] Gemini 服务不可用，跳过 AI 分析")

                                    except Exception as e:
                                        print(f"[视频记录] 压缩和分析任务失败: {e}")
                                        import traceback
                                        traceback.print_exc()

                                # 在后台执行
                                loop.run_in_executor(None, compress_and_analyze)

                    except Exception as e:
                        print(f"[视频记录] 视频 {idx} 下载失败: {e}")
                        yield {
                            "event": "error",
                            "data": json.dumps({"message": f"视频 {idx} 下载失败: {str(e)}"}, ensure_ascii=False)
                        }

                except Exception as e:
                    print(f"[视频记录] 视频 {idx} 处理失败: {e}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": f"视频 {idx} 处理失败: {str(e)}"}, ensure_ascii=False)
                    }

        except Exception as e:
            print(f"[视频记录] 批量创建失败: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": f"批量创建失败: {str(e)}"}, ensure_ascii=False)
            }

        # 完成
        yield {
            "event": "done",
            "data": "{}"
        }

    return EventSourceResponse(event_generator())


@router.put("/api/video-records/{record_id}", response_model=VideoRecordResponse)
async def update_video_record(record_id: int, req: VideoRecordUpdate):
            if video_info.get("upload_date"):
                try:
                    upload_date = video_info["upload_date"]
                    video_time = datetime.strptime(upload_date, "%Y%m%d").isoformat()
                except Exception:
                    pass

            video_copy = video_info.get("description", "")[:500] if video_info.get("description") else ""
            if not video_copy:
                video_copy = video_info.get("title", "")[:500]

            likes = video_info.get("like_count", 0) or 0
            comments = video_info.get("comment_count", 0) or 0
            shares = video_info.get("share_count", 0) or 0
            collects = video_info.get("collect_count", 0) or 0

            # 更新数据库并推送基本信息
            with get_db() as conn:
                conn.execute(
                    """UPDATE video_records
                       SET video_time = ?, video_copy = ?, likes = ?, comments = ?, shares = ?, collects = ?, updated_at = datetime('now')
                       WHERE id = ?""",
                    (video_time, video_copy, likes, comments, shares, collects, record_id)
                )

                row = conn.execute(
                    "SELECT * FROM video_records WHERE id = ?", (record_id,)
                ).fetchone()

                # 推送基本信息更新
                yield {
                    "event": "basic_info",
                    "data": json.dumps(dict(row), ensure_ascii=False)
                }

            # 3. 下载视频
            yield {
                "event": "status",
                "data": json.dumps({"message": "正在下载视频..."}, ensure_ascii=False)
            }

            video_file_path = ""
            try:
                formats = video_info.get("formats", [])
                if formats and len(formats) > 0:
                    direct_url = formats[0].get("_direct_url") or formats[0].get("url")

                    if direct_url:
                        import requests
                        from pathlib import Path

                        title = video_info.get("title", "video")
                        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)[:60]
                        filename = f"{safe_title}.mp4"

                        download_dir = Path(__file__).parent.parent.parent.parent / "downloads"
                        download_dir.mkdir(parents=True, exist_ok=True)
                        filepath = download_dir / filename

                        download_with_retry(direct_url, filepath, max_retries=3)
                        video_file_path = str(filepath)

                        # 更新视频文件路径
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE video_records SET video_file_path = ?, updated_at = datetime('now') WHERE id = ?",
                                (video_file_path, record_id)
                            )

                            row = conn.execute(
                                "SELECT * FROM video_records WHERE id = ?", (record_id,)
                            ).fetchone()

                            # 推送下载完成
                            yield {
                                "event": "video_downloaded",
                                "data": json.dumps(dict(row), ensure_ascii=False)
                            }

                        # 4. 启动后台 AI 分析任务
                        yield {
                            "event": "status",
                            "data": json.dumps({"message": "AI 分析已启动，将在后台进行..."}, ensure_ascii=False)
                        }

                        from app.services.video_compressor import compressor
                        from app.services.gemini_video_analyzer import analyzer

                        def compress_and_analyze():
                            try:
                                import os
                                from app.repositories.db import get_db

                                print(f"[视频记录] 开始压缩视频: {os.path.basename(video_file_path)}")
                                compress_result = compressor.compress_video(video_file_path, "medium", 1280)

                                if compress_result:
                                    print(f"[视频记录] 压缩完成，开始 AI 分析")
                                else:
                                    print(f"[视频记录] 压缩失败，使用原视频进行 AI 分析")

                                if analyzer.is_available():
                                    print(f"[视频记录] 开始 AI 分析视频")
                                    analysis_result = analyzer.analyze_compressed_video(video_file_path)

                                    if analysis_result:
                                        print(f"[视频记录] AI 分析完成，更新数据库")
                                        with get_db() as conn:
                                            category = analysis_result.get("category", "")
                                            product = analysis_result.get("product", "")
                                            golden_3s = analysis_result.get("golden_3s", "")
                                            transcript = analysis_result.get("transcript", "")
                                            viral_analysis = analysis_result.get("viral_analysis", "")
                                            scenes = analysis_result.get("scenes", "")

                                            conn.execute(
                                                """UPDATE video_records
                                                   SET category = ?, product = ?, golden_3s_copy = ?, transcript = ?, viral_analysis = ?, scene_analysis = ?, updated_at = datetime('now')
                                                   WHERE id = ?""",
                                                (category, product, golden_3s, transcript, viral_analysis, scenes, record_id)
                                            )
                                        print(f"[视频记录] 记录 {record_id} 的 AI 分析结果已保存")

                                        # 推送到 SSE 队列
                                        if record_id in ai_update_queues:
                                            try:
                                                ai_update_queues[record_id].put_nowait({
                                                    "category": category,
                                                    "product": product,
                                                    "golden_3s_copy": golden_3s,
                                                    "transcript": transcript,
                                                    "viral_analysis": viral_analysis,
                                                    "scene_analysis": scenes
                                                })
                                                print(f"[视频记录] 已推送 AI 分析结果到前端")
                                            except Exception as e:
                                                print(f"[视频记录] 推送失败: {e}")
                                    else:
                                        print(f"[视频记录] AI 分析失败")
                                else:
                                    print(f"[视频记录] Gemini 服务不可用，跳过 AI 分析")

                            except Exception as e:
                                print(f"[视频记录] 压缩和分析任务失败: {e}")
                                import traceback
                                traceback.print_exc()

                        # 在后台执行
                        loop.run_in_executor(None, compress_and_analyze)

            except Exception as e:
                print(f"[视频记录] 下载失败: {e}")
                yield {
                    "event": "error",
                    "data": json.dumps({"message": f"下载失败: {str(e)}"}, ensure_ascii=False)
                }

        except Exception as e:
            print(f"[视频记录] 创建失败: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": f"创建失败: {str(e)}"}, ensure_ascii=False)
            }

        # 完成
        yield {
            "event": "done",
            "data": "{}"
        }

    return EventSourceResponse(event_generator())


@router.put("/api/video-records/{record_id}", response_model=VideoRecordResponse)
async def update_video_record(record_id: int, req: VideoRecordUpdate):
    """更新视频记录。"""
    with get_db() as conn:
        # 检查记录是否存在
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        # 构建更新语句
        updates = []
        params = []

        if req.video_time is not None:
            updates.append("video_time = ?")
            params.append(req.video_time)

        if req.category is not None:
            updates.append("category = ?")
            params.append(req.category)

        if req.product is not None:
            updates.append("product = ?")
            params.append(req.product)

        if req.golden_3s_copy is not None:
            updates.append("golden_3s_copy = ?")
            params.append(req.golden_3s_copy)

        if req.transcript is not None:
            updates.append("transcript = ?")
            params.append(req.transcript)

        if req.video_copy is not None:
            updates.append("video_copy = ?")
            params.append(req.video_copy)

        if req.viral_analysis is not None:
            updates.append("viral_analysis = ?")
            params.append(req.viral_analysis)

        if req.scene_analysis is not None:
            updates.append("scene_analysis = ?")
            params.append(req.scene_analysis)

        if req.exposure is not None:
            updates.append("exposure = ?")
            params.append(req.exposure)

        if req.likes is not None:
            updates.append("likes = ?")
            params.append(req.likes)

        if req.comments is not None:
            updates.append("comments = ?")
            params.append(req.comments)

        if req.shares is not None:
            updates.append("shares = ?")
            params.append(req.shares)

        if req.collects is not None:
            updates.append("collects = ?")
            params.append(req.collects)

        if req.remarks is not None:
            updates.append("remarks = ?")
            params.append(req.remarks)

        if updates:
            updates.append("updated_at = datetime('now')")
            params.append(record_id)

            sql = f"UPDATE video_records SET {', '.join(updates)} WHERE id = ?"
            conn.execute(sql, params)

        # 返回更新后的记录
        row = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        return dict(row)


@router.delete("/api/video-records/{record_id}")
async def delete_video_record(record_id: int):
    """删除视频记录。"""
    with get_db() as conn:
        # 检查记录是否存在
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        conn.execute("DELETE FROM video_records WHERE id = ?", (record_id,))

        return {"success": True, "message": "删除成功"}


@router.get("/api/video-records/{record_id}/play")
async def play_video(record_id: int):
    """播放视频，优先使用原视频，如果不存在则使用压缩视频。"""
    import os
    from fastapi.responses import FileResponse
    from app.services.video_compressor import compressor

    with get_db() as conn:
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        video_file_path = record["video_file_path"]

        # 检查原视频是否存在
        if video_file_path and os.path.exists(video_file_path):
            return FileResponse(
                path=video_file_path,
                media_type="video/mp4",
                filename=os.path.basename(video_file_path)
            )

        # 原视频不存在，尝试使用压缩视频
        if video_file_path:
            compressed_path = compressor.get_compressed_video(video_file_path)
            if compressed_path and os.path.exists(compressed_path):
                return FileResponse(
                    path=compressed_path,
                    media_type="video/mp4",
                    filename=os.path.basename(compressed_path)
                )

        raise HTTPException(status_code=404, detail="视频文件不存在")


@router.post("/api/video-records/{record_id}/download")
async def download_video_for_record(record_id: int):
    """手动下载视频到本地。"""
    with get_db() as conn:
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        video_url = record["video_url"]

        try:
            from app.services.video_service import download_video_service
            from app.schemas.video import DownloadRequest
            from app.integrations.douyin_client import is_douyin_url
            from app.integrations.yt_dlp_client import downloader

            # 重新解析获取最新的下载链接
            loop = asyncio.get_event_loop()
            if is_douyin_url(video_url):
                video_info = await loop.run_in_executor(None, douyin_parser.parse, video_url)
            else:
                video_info = await loop.run_in_executor(None, downloader.parse_video, video_url)

            formats = video_info.get("formats", [])
            format_id = "best"
            if formats and len(formats) > 0:
                format_id = formats[0].get("format_id", "best")

            download_req = DownloadRequest(url=video_url, format_id=format_id)
            download_result = await download_video_service(download_req)

            if download_result and "filepath" in download_result:
                video_file_path = download_result["filepath"]

                # 更新数据库中的视频路径
                conn.execute(
                    "UPDATE video_records SET video_file_path = ?, updated_at = datetime('now') WHERE id = ?",
                    (video_file_path, record_id)
                )

                return {"success": True, "message": "下载成功", "filepath": video_file_path}
            else:
                raise HTTPException(status_code=500, detail="下载失败")

        except Exception as e:
            raise HTTPException(status_code=400, detail={"success": False, "error": f"下载失败: {str(e)}"})


@router.post("/api/video-records/{record_id}/analyze")
async def analyze_video_with_gemini(record_id: int):
    """使用 Gemini 分析视频，提取口播文案和画面描述。"""
    from app.services.gemini_video_analyzer import analyzer

    with get_db() as conn:
        record = conn.execute(
            "SELECT * FROM video_records WHERE id = ?", (record_id,)
        ).fetchone()

        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")

        if not analyzer.is_available():
            raise HTTPException(
                status_code=503,
                detail="Gemini 服务不可用，请在 api_config.yaml 中配置 Gemini API"
            )

        video_file_path = record["video_file_path"]
        if not video_file_path:
            raise HTTPException(status_code=400, detail="请先下载视频到本地")

        try:
            # 在后台执行分析
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, analyzer.analyze_compressed_video, video_file_path
            )

            if not result:
                raise HTTPException(status_code=500, detail="视频分析失败")

            # 提取分析结果
            golden_3s = result.get("golden_3s", "")
            transcript = result.get("transcript", "")
            scenes = result.get("scenes", "")
            viral_analysis = result.get("viral_analysis", "")

            # 更新数据库：
            # - 黄金三秒保存到 golden_3s_copy
            # - 口播文案保存到 transcript（新字段，不覆盖原有 video_copy）
            # - 爆款分析保存到 viral_analysis（新字段）
            # - 画面描述保存到 remarks
            golden_3s_copy = golden_3s if golden_3s else record["golden_3s_copy"]
            transcript_text = transcript if transcript and transcript != "无口播" else record.get("transcript", "")
            viral_analysis_text = viral_analysis if viral_analysis else record.get("viral_analysis", "")
            remarks = f"【AI分析】\n画面: {scenes}"

            conn.execute(
                """UPDATE video_records
                   SET golden_3s_copy = ?, transcript = ?, viral_analysis = ?, remarks = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                (golden_3s_copy, transcript_text, viral_analysis_text, remarks, record_id)
            )

            return {
                "success": True,
                "message": "分析完成",
                "data": {
                    "golden_3s": golden_3s,
                    "transcript": transcript,
                    "scenes": scenes,
                    "viral_analysis": viral_analysis,
                    "key_moments": result.get("key_moments", [])
                }
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail={"success": False, "error": f"分析失败: {str(e)}"})


@router.post("/api/video-all-in-one")
async def video_all_in_one(video_url: str):
    """一体化接口：输入视频链接，自动完成解析、下载、压缩、AI分析，返回完整数据。

    Args:
        video_url: 视频链接

    Returns:
        完整的视频数据，包括：
        - 基本信息（标题、时长、平台等）
        - 互动数据（点赞、评论、分享、收藏）
        - 本地文件路径（原视频、压缩视频）
        - AI分析结果（口播文案、画面描述、爆款原因分析）
    """
    import os
    from app.services.gemini_video_analyzer import analyzer
    from app.integrations.douyin_client import is_douyin_url
    from app.integrations.yt_dlp_client import downloader
    from app.services.video_service import download_video_service
    from app.schemas.video import DownloadRequest
    from app.services.video_compressor import compressor

    try:
        # 1. 解析视频信息
        print(f"[一体化API] 步骤1: 解析视频信息")
        loop = asyncio.get_event_loop()

        if is_douyin_url(video_url):
            video_info = await loop.run_in_executor(None, douyin_parser.parse, video_url)
        else:
            video_info = await loop.run_in_executor(None, downloader.parse_video, video_url)

        # 提取基本信息
        video_data = {
            "video_url": video_url,
            "title": video_info.get("title", ""),
            "platform": video_info.get("platform", ""),
            "duration": video_info.get("duration", 0),
            "uploader": video_info.get("uploader", ""),
            "thumbnail": video_info.get("thumbnail", ""),
            "description": video_info.get("description", ""),
            "likes": video_info.get("like_count", 0) or 0,
            "comments": video_info.get("comment_count", 0) or 0,
            "shares": video_info.get("share_count", 0) or 0,
            "collects": video_info.get("collect_count", 0) or 0,
        }

        # 2. 下载视频
        print(f"[一体化API] 步骤2: 下载视频")
        formats = video_info.get("formats", [])
        format_id = "best"
        if formats and len(formats) > 0:
            format_id = formats[0].get("format_id", "best")

        download_req = DownloadRequest(url=video_url, format_id=format_id)
        download_result = await download_video_service(download_req)

        if not download_result or "filepath" not in download_result:
            raise HTTPException(status_code=500, detail="视频下载失败")

        video_file_path = download_result["filepath"]
        video_data["video_file_path"] = video_file_path
        video_data["video_filename"] = download_result.get("filename", "")

        # 3. 等待压缩完成（压缩是异步的，等待一下）
        print(f"[一体化API] 步骤3: 等待视频压缩")
        await asyncio.sleep(5)  # 等待压缩任务启动

        # 检查压缩视频
        compressed_path = compressor.get_compressed_video(video_file_path)
        if compressed_path:
            video_data["compressed_file_path"] = compressed_path
            video_data["compressed_filename"] = os.path.basename(compressed_path)
        else:
            video_data["compressed_file_path"] = None
            video_data["compressed_filename"] = None

        # 4. AI 分析（如果 Gemini 可用）
        if analyzer.is_available():
            print(f"[一体化API] 步骤4: AI 分析视频")
            try:
                # 等待压缩完成
                max_wait = 60  # 最多等待60秒
                waited = 0
                while waited < max_wait:
                    compressed_path = compressor.get_compressed_video(video_file_path)
                    if compressed_path and os.path.exists(compressed_path):
                        break
                    await asyncio.sleep(2)
                    waited += 2

                # 执行分析
                analysis_result = await loop.run_in_executor(
                    None, analyzer.analyze_compressed_video, video_file_path
                )

                if analysis_result:
                    video_data["ai_analysis"] = {
                        "golden_3s": analysis_result.get("golden_3s", ""),
                        "transcript": analysis_result.get("transcript", ""),
                        "scenes": analysis_result.get("scenes", ""),
                        "viral_analysis": analysis_result.get("viral_analysis", ""),
                        "key_moments": analysis_result.get("key_moments", [])
                    }
                else:
                    video_data["ai_analysis"] = None
            except Exception as e:
                print(f"[一体化API] AI分析失败: {e}")
                video_data["ai_analysis"] = {"error": str(e)}
        else:
            video_data["ai_analysis"] = None

        print(f"[一体化API] 完成！")
        return {
            "success": True,
            "message": "视频处理完成",
            "data": video_data
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail={"success": False, "error": str(e)})


@router.get("/api/video-records/{record_id}/stream")
async def stream_ai_updates(record_id: int):
    """SSE 端点：实时推送 AI 分析结果更新。"""
    import queue

    print(f"[SSE] 客户端连接到记录 {record_id} 的 SSE 流")

    # 为这个记录创建一个队列
    update_queue = queue.Queue()
    ai_update_queues[record_id] = update_queue
    print(f"[SSE] 已为记录 {record_id} 创建更新队列")

    async def event_generator():
        try:
            # 先检查数据库中是否已有 AI 分析结果
            with get_db() as conn:
                record = conn.execute(
                    "SELECT golden_3s_copy, transcript, viral_analysis, remarks FROM video_records WHERE id = ?",
                    (record_id,)
                ).fetchone()

                if record:
                    # 如果已有数据，立即推送
                    if record["golden_3s_copy"] or record["transcript"] or record["viral_analysis"]:
                        print(f"[SSE] 记录 {record_id} 已有 AI 数据，立即推送")
                        yield {
                            "event": "ai_update",
                            "data": json.dumps({
                                "golden_3s_copy": record["golden_3s_copy"] or "",
                                "transcript": record["transcript"] or "",
                                "viral_analysis": record["viral_analysis"] or "",
                                "remarks": record["remarks"] or ""
                            }, ensure_ascii=False)
                        }
                        # 已有数据，关闭连接
                        yield {"event": "done", "data": "{}"}
                        return

            print(f"[SSE] 记录 {record_id} 等待 AI 分析完成...")
            # 等待 AI 分析完成（最多等待 10 分钟）
            timeout = 600
            start_time = asyncio.get_event_loop().time()

            while True:
                # 检查超时
                if asyncio.get_event_loop().time() - start_time > timeout:
                    print(f"[SSE] 记录 {record_id} 等待超时")
                    yield {"event": "timeout", "data": "{}"}
                    break

                # 非阻塞地检查队列
                try:
                    update_data = update_queue.get_nowait()
                    print(f"[SSE] 记录 {record_id} 收到 AI 更新，准备推送: {update_data}")
                    # 推送更新
                    yield {
                        "event": "ai_update",
                        "data": json.dumps(update_data, ensure_ascii=False)
                    }
                    # 推送完成，关闭连接
                    yield {"event": "done", "data": "{}"}
                    print(f"[SSE] 记录 {record_id} 推送完成，关闭连接")
                    break
                except queue.Empty:
                    # 队列为空，等待一会儿再检查
                    await asyncio.sleep(1)

        finally:
            # 清理队列
            if record_id in ai_update_queues:
                del ai_update_queues[record_id]
                print(f"[SSE] 已清理记录 {record_id} 的更新队列")

    return EventSourceResponse(event_generator())


@router.get("/api/video-records/export")
async def export_to_excel(sheet_id: str = "sheet1"):
    """导出当前工作表的视频记录为Excel文件"""
    try:
        from io import BytesIO
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        from fastapi.responses import StreamingResponse

        # 如果 sheet_id 是数字字符串，转换为整数
        try:
            sheet_id_value = int(sheet_id)
        except (ValueError, TypeError):
            sheet_id_value = sheet_id

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, video_url, video_time, category, product,
                       golden_3s_copy, transcript, video_copy, viral_analysis,
                       exposure, likes, comments, shares, collects, remarks
                FROM video_records
                WHERE sheet_id = ?
                ORDER BY id DESC
            """, (sheet_id_value,))
            records = cursor.fetchall()

        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "视频数据"

        # 设置表头（与前端表头一致，去掉"视频播放"和"操作"列）
        headers = ["序号", "视频链接", "视频时间", "品类", "产品",
                   "黄金三秒文案", "口播文案", "视频文案", "爆款分析",
                   "曝光量", "点赞量", "评论数", "分享数", "收藏数", "备注"]

        # 写入表头并设置样式
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")

        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # 写入数据
        for row_num, record in enumerate(records, 2):
            for col_num, value in enumerate(record, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        # 调整列宽（使用 get_column_letter 代替 chr）
        column_widths = [8, 50, 12, 15, 20, 30, 40, 40, 40, 12, 12, 12, 12, 12, 30]
        for col_num, width in enumerate(column_widths, 1):
            column_letter = get_column_letter(col_num)
            ws.column_dimensions[column_letter].width = width

        # 保存到内存
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # 返回文件
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=video_data_{sheet_id}.xlsx"}
        )
    except Exception as e:
        print(f"[导出Excel错误] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")

