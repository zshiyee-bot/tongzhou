"""压缩队列管理器 - 限制并发压缩数量，避免资源竞争"""

import threading
from queue import Queue
from typing import Callable, Any
import time


class CompressionQueue:
    """压缩队列管理器，限制同时进行的压缩任务数量"""

    def __init__(self, max_workers: int = 2):
        """
        初始化压缩队列

        Args:
            max_workers: 最大并发压缩数量（默认2个）
        """
        self.max_workers = max_workers
        self.queue = Queue()
        self.active_tasks = 0
        self.lock = threading.Lock()
        self.workers = []

        # 启动工作线程
        for _ in range(max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

    def _worker(self):
        """工作线程，从队列中取任务并执行"""
        while True:
            try:
                task_func, args, kwargs, callback = self.queue.get()

                with self.lock:
                    self.active_tasks += 1

                print(f"[压缩队列] 开始执行压缩任务（当前活跃: {self.active_tasks}/{self.max_workers}）", flush=True)

                try:
                    result = task_func(*args, **kwargs)
                    if callback:
                        callback(result)
                except Exception as e:
                    print(f"[压缩队列] 任务执行失败: {e}", flush=True)
                    if callback:
                        callback(None)
                finally:
                    with self.lock:
                        self.active_tasks -= 1
                    self.queue.task_done()
                    print(f"[压缩队列] 任务完成（当前活跃: {self.active_tasks}/{self.max_workers}）", flush=True)

            except Exception as e:
                print(f"[压缩队列] 工作线程异常: {e}", flush=True)

    def submit(self, task_func: Callable, *args, callback: Callable = None, **kwargs):
        """
        提交压缩任务到队列

        Args:
            task_func: 要执行的函数
            *args: 函数参数
            callback: 完成后的回调函数
            **kwargs: 函数关键字参数
        """
        queue_size = self.queue.qsize()
        print(f"[压缩队列] 提交新任务（队列长度: {queue_size}）", flush=True)
        self.queue.put((task_func, args, kwargs, callback))

    def wait_all(self):
        """等待所有任务完成"""
        self.queue.join()


# 全局压缩队列实例（限制同时2个压缩任务）
compression_queue = CompressionQueue(max_workers=2)
