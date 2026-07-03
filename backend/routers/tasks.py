"""
爬虫任务管理接口
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException

ROOT = Path(__file__).resolve().parent.parent.parent

router = APIRouter()

# 任务状态（内存中维护）
_task_state = {
    "status": "idle",       # idle / running
    "last_run": None,
    "last_result": None,
    "schedule": "0 9 * * *",
}


@router.get("")
def task_status():
    """查看当前任务状态"""
    return _task_state


@router.post("/start")
def start_crawl():
    """启动一次爬取"""
    if _task_state["status"] == "running":
        raise HTTPException(400, "爬取任务正在运行中")

    _task_state["status"] = "running"
    _task_state["last_run"] = datetime.now().isoformat()

    try:
        result = subprocess.run(
            [sys.executable, "scripts/daily_crawl.py"],
            capture_output=True, text=True,
            timeout=600, cwd=str(ROOT),
        )
        _task_state["last_result"] = {
            "returncode": result.returncode,
            "stdout": result.stdout[-500:],
            "stderr": result.stderr[-500:],
        }
        _task_state["status"] = "idle"
        return {"status": "completed", "code": result.returncode}
    except subprocess.TimeoutExpired:
        _task_state["status"] = "idle"
        raise HTTPException(504, "爬取超时")
    except Exception as e:
        _task_state["status"] = "idle"
        raise HTTPException(500, str(e))


@router.post("/stop")
def stop_crawl():
    """停止任务（标记停止，子进程不会立即中断）"""
    if _task_state["status"] == "idle":
        return {"status": "idle", "message": "当前无运行中的任务"}
    _task_state["status"] = "stopping"
    return {"status": "stopping", "message": "停止信号已发送"}
