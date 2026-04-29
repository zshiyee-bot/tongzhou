"""应用启动入口。"""

import sys
import uvicorn

# 禁用输出缓冲，确保日志和SSE事件立即输出
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=1018,
        reload=True
    )
