"""
FastAPI 应用 — 爬虫数据服务

命令：
  python -m uvicorn backend.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# 确保项目根目录在路径中
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import repos, articles, stats, tasks

app = FastAPI(
    title="Crawler Data Service",
    description="多源爬虫数据查询服务 — GitHub Trending + SegmentFault",
    version="1.0.0",
)

# CORS（允许本地前端调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(repos.router, prefix="/api/repos", tags=["GitHub 仓库"])
app.include_router(articles.router, prefix="/api/articles", tags=["SegmentFault 文章"])
app.include_router(stats.router, prefix="/api/stats", tags=["统计"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["爬虫任务管理"])


@app.get("/")
def root():
    return {
        "service": "Crawler Data Service",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
