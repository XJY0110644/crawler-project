"""
GitHub 仓库查询接口
"""

from fastapi import APIRouter, Query

from backend.database import query_repos, count_repos, get_repo_languages, find_similar_repos

router = APIRouter()


@router.get("")
def list_repos(
    language: str = Query("", description="按编程语言过滤"),
    sort_by: str = Query("stars_today", description="排序字段: stars / stars_today / forks"),
    keyword: str = Query("", description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """查询 GitHub 仓库列表"""
    items = query_repos(
        language=language,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        keyword=keyword,
    )
    total = count_repos(language=language, keyword=keyword)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/languages")
def repo_languages():
    """编程语言分布统计"""
    return {"items": get_repo_languages()}


@router.get("/{repo_id}")
def get_repo(repo_id: int):
    """获取单个仓库详情"""
    from backend.database import _connect_github
    conn = _connect_github()
    if conn is None:
        return {"error": "database not found"}
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM repos WHERE id = ?", (repo_id,))
        row = c.fetchone()
        if row:
            return dict(row)
        return {"error": "not found"}
    finally:
        conn.close()


@router.get("/{repo_id}/similar")
def similar_repos(
    repo_id: int,
    threshold: int = Query(15, ge=3, le=30, description="汉明距离阈值，越大越宽松"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    基于 SimHash 相似度推荐与该仓库描述相似的其他仓库
    """
    results = find_similar_repos(repo_id, threshold=threshold, limit=limit)
    return {"repo_id": repo_id, "threshold": threshold, "count": len(results), "items": results}
