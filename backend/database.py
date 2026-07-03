"""
数据库查询工具 — 封装 SQLite 读取操作
"""

import sqlite3
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

GITHUB_DB = ROOT / "data" / "github" / "github_trending.db"
SF_DB = ROOT / "data" / "segmentfault" / "segmentfault.db"


def _connect_github() -> Optional[sqlite3.Connection]:
    if not GITHUB_DB.exists():
        return None
    conn = sqlite3.connect(str(GITHUB_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _connect_sf() -> Optional[sqlite3.Connection]:
    if not SF_DB.exists():
        return None
    conn = sqlite3.connect(str(SF_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ─── GitHub ────────────────────────────────────────────


def query_repos(
    language: str = "",
    sort_by: str = "stars_today",
    limit: int = 20,
    offset: int = 0,
    keyword: str = "",
) -> list[dict]:
    conn = _connect_github()
    if conn is None:
        return []
    try:
        conditions = []
        params = []
        if language:
            conditions.append("language = ?")
            params.append(language)
        if keyword:
            conditions.append("(description LIKE ? OR repo_full_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        allowed_sort = {
            "stars": "stars DESC",
            "stars_today": "stars_today DESC",
            "forks": "forks DESC",
            "created_at": "created_at DESC",
        }
        order = allowed_sort.get(sort_by, "stars_today DESC")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        c = conn.cursor()
        c.execute(
            f"SELECT * FROM repos {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def count_repos(language: str = "", keyword: str = "") -> int:
    conn = _connect_github()
    if conn is None:
        return 0
    try:
        conditions = []
        params = []
        if language:
            conditions.append("language = ?")
            params.append(language)
        if keyword:
            conditions.append("(description LIKE ? OR repo_full_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        c = conn.cursor()
        c.execute(f"SELECT COUNT(*) FROM repos {where}", params)
        return c.fetchone()[0]
    finally:
        conn.close()


def get_repo_languages() -> list[dict]:
    conn = _connect_github()
    if conn is None:
        return []
    try:
        c = conn.cursor()
        c.execute("""
            SELECT language, COUNT(*) as count, SUM(stars) as total_stars
            FROM repos WHERE language != ''
            GROUP BY language ORDER BY count DESC
        """)
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def get_repo_statistics() -> dict:
    conn = _connect_github()
    if conn is None:
        return {}
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM repos")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT language) FROM repos WHERE language != ''")
        langs = c.fetchone()[0]
        c.execute("SELECT SUM(stars) FROM repos")
        all_stars = c.fetchone()[0] or 0
        c.execute("SELECT SUM(stars_today) FROM repos")
        today_stars = c.fetchone()[0] or 0
        c.execute("SELECT repo_full_name, stars_today FROM repos ORDER BY stars_today DESC LIMIT 1")
        hottest = c.fetchone()
        return {
            "total_repos": total,
            "languages": langs,
            "total_stars": all_stars,
            "today_stars": today_stars,
            "hottest_repo": dict(hottest) if hottest else None,
        }
    finally:
        conn.close()


# ─── 相似推荐（SimHash — GitHub）─────────────────────────


def _compute_repo_fingerprint(repo: dict) -> int:
    """对仓库名称+描述计算 SimHash 指纹"""
    from core.simhash import compute_fingerprint
    text = f"{repo.get('repo_name', '')} {repo.get('description', '')}"
    return compute_fingerprint(text)


def find_similar_repos(
    repo_id: int,
    threshold: int = 15,
    limit: int = 5,
) -> list[dict]:
    """根据 SimHash 相似度查找与指定仓库相似的其他仓库"""
    from core.simhash import hamming_distance

    conn = _connect_github()
    if conn is None:
        return []

    try:
        c = conn.cursor()
        c.execute("SELECT * FROM repos WHERE id = ?", (repo_id,))
        row = c.fetchone()
        if not row:
            return []
        target = dict(row)

        c.execute("SELECT * FROM repos WHERE id != ?", (repo_id,))
        candidates = [dict(r) for r in c.fetchall()]

        if not candidates:
            return []

        target_fp = _compute_repo_fingerprint(target)

        similarities = []
        for repo in candidates:
            fp = _compute_repo_fingerprint(repo)
            dist = hamming_distance(target_fp, fp)
            if dist <= threshold:
                similarities.append({
                    "id": repo["id"],
                    "repo_full_name": repo["repo_full_name"],
                    "description": repo["description"],
                    "language": repo["language"],
                    "stars": repo["stars"],
                    "stars_today": repo["stars_today"],
                    "hamming_distance": dist,
                    "similarity_score": max(0, 1.0 - dist / 64.0),
                })

        similarities.sort(key=lambda x: x["hamming_distance"])
        return similarities[:limit]
    finally:
        conn.close()


# ─── 相似推荐（SimHash — SF）────────────────────────────


def _compute_article_fingerprint(article: dict) -> int:
    """对文章标题+摘要合并计算 SimHash 指纹"""
    from core.simhash import compute_fingerprint
    text = f"{article.get('title', '')} {article.get('summary', '')}"
    return compute_fingerprint(text)


def find_similar_articles(
    article_id: int,
    threshold: int = 10,
    limit: int = 5,
) -> list[dict]:
    """
    根据 SimHash 相似度查找与指定文章最相似的其他文章

    算法：
      1. 取出目标文章，计算其 SimHash 指纹
      2. 取出所有其他文章，逐个计算指纹
      3. 比较汉明距离，返回 <= threshold 的结果，按距离升序

    threshold 越小越严格（3=几乎重复，10=主题相关）
    """
    from core.simhash import hamming_distance

    conn = _connect_sf()
    if conn is None:
        return []

    try:
        # 取出目标文章
        c = conn.cursor()
        c.execute("SELECT * FROM articles WHERE article_id = ?", (article_id,))
        row = c.fetchone()
        if not row:
            return []
        target = dict(row)

        # 取出所有其他文章（排除自己）
        c.execute(
            "SELECT * FROM articles WHERE article_id != ?",
            (article_id,),
        )
        candidates = [dict(r) for r in c.fetchall()]

        if not candidates:
            return []

        target_fp = _compute_article_fingerprint(target)

        similarities = []
        for article in candidates:
            fp = _compute_article_fingerprint(article)
            dist = hamming_distance(target_fp, fp)
            if dist <= threshold:
                similarities.append({
                    "article_id": article["article_id"],
                    "title": article["title"],
                    "url": article["url"],
                    "author_name": article["author_name"],
                    "views": article["views"],
                    "votes": article["votes"],
                    "hamming_distance": dist,
                    "similarity_score": max(0, 1.0 - dist / 64.0),
                })

        # 按汉明距离升序，取前 limit 条
        similarities.sort(key=lambda x: x["hamming_distance"])
        return similarities[:limit]
    finally:
        conn.close()


# ─── SegmentFault ──────────────────────────────────────


def query_articles(
    sort_by: str = "views",
    limit: int = 20,
    offset: int = 0,
    keyword: str = "",
) -> list[dict]:
    conn = _connect_sf()
    if conn is None:
        return []
    try:
        conditions = []
        params = []
        if keyword:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        allowed_sort = {
            "views": "views DESC",
            "votes": "votes DESC",
            "comments": "comments DESC",
            "timestamp": "timestamp DESC",
        }
        order = allowed_sort.get(sort_by, "views DESC")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        c = conn.cursor()
        c.execute(
            f"SELECT * FROM articles {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def count_articles(keyword: str = "") -> int:
    conn = _connect_sf()
    if conn is None:
        return 0
    try:
        if keyword:
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM articles WHERE title LIKE ? OR summary LIKE ?",
                [f"%{keyword}%", f"%{keyword}%"],
            )
            return c.fetchone()[0]
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM articles")
        return c.fetchone()[0]
    finally:
        conn.close()


def get_article_statistics() -> dict:
    conn = _connect_sf()
    if conn is None:
        return {}
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM articles")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT author_name) FROM articles WHERE author_name != ''")
        authors = c.fetchone()[0]
        c.execute("SELECT MAX(views) FROM articles")
        max_views = c.fetchone()[0] or 0
        c.execute("SELECT MAX(votes) FROM articles")
        max_votes = c.fetchone()[0] or 0
        c.execute("SELECT MAX(created_at) FROM articles")
        latest = c.fetchone()[0] or ""
        return {
            "total_articles": total,
            "total_authors": authors,
            "max_views": max_views,
            "max_votes": max_votes,
            "latest_article_date": latest,
        }
    finally:
        conn.close()
