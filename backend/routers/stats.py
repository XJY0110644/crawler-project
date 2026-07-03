"""
统计接口
"""

from fastapi import APIRouter

from backend.database import (
    get_repo_statistics,
    get_article_statistics,
    get_repo_languages,
)

router = APIRouter()


@router.get("/overview")
def stats_overview():
    """总览统计"""
    return {
        "github": get_repo_statistics(),
        "segmentfault": get_article_statistics(),
    }


@router.get("/languages")
def stats_languages():
    """编程语言排行"""
    return {"items": get_repo_languages()}


@router.get("/trending")
def stats_trending():
    """最热仓库今日排行"""
    from backend.database import query_repos
    repos = query_repos(sort_by="stars_today", limit=10)
    return {
        "date": __import__("datetime").date.today().isoformat(),
        "items": repos,
    }
