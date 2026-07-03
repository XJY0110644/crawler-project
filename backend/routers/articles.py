"""
SegmentFault 文章查询接口
"""

from fastapi import APIRouter, Query

from backend.database import query_articles, count_articles, find_similar_articles

router = APIRouter()


@router.get("")
def list_articles(
    sort_by: str = Query("views", description="排序: views / votes / comments"),
    keyword: str = Query("", description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """查询文章列表"""
    items = query_articles(
        sort_by=sort_by,
        limit=limit,
        offset=offset,
        keyword=keyword,
    )
    total = count_articles(keyword=keyword)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/{article_id}")
def get_article(article_id: int):
    """获取单篇文章"""
    items = query_articles(limit=1, offset=0)
    for item in items:
        if item["article_id"] == article_id:
            return item
    return {"error": "not found"}


@router.get("/{article_id}/similar")
def similar_articles(
    article_id: int,
    threshold: int = Query(10, ge=3, le=20, description="相似阈值：汉明距离 <= 此值判定为相似，越小越严格"),
    limit: int = Query(5, ge=1, le=20, description="返回条数"),
):
    """
    基于 SimHash 相似度推荐与本文相似的其他文章

    - threshold: 汉明距离阈值，默认 10（3=几乎重复，10=主题相关，15=宽松匹配）
    - limit: 返回条数，默认 5
    """
    results = find_similar_articles(article_id, threshold=threshold, limit=limit)
    return {"article_id": article_id, "threshold": threshold, "count": len(results), "items": results}
