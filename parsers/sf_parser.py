"""
解析层 — SegmentFault 文章解析

数据源：从 HTML 页面的 __NEXT_DATA__ JSON 提取
URL: https://segmentfault.com/blogs/newest

包含完整字段：标题、链接、时间、点赞、评论、阅读量、作者、专栏等
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def extract_next_data(html: str) -> Optional[dict]:
    """
    从 HTML 中提取 __NEXT_DATA__ JSON
    """
    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        logger.warning("未找到 __NEXT_DATA__")
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        return None


def parse_article_list(html: str) -> list[dict]:
    """
    从 HTML 页面解析文章列表，返回完整字段

    返回字段：
        article_id, title, url, created_at, timestamp,
        votes, comments, views,
        author_name, author_url, author_avatar,
        blog_name, blog_url, cover, summary
    """
    data = extract_next_data(html)
    if not data:
        return []

    try:
        articles_raw = data["props"]["pageProps"]["initialState"]["blogs"]["articles"]["rows"]
    except (KeyError, TypeError) as e:
        logger.error(f"提取文章列表失败: {e}")
        return []

    articles = []
    for item in articles_raw:
        try:
            article_id = item.get("id")
            title = (item.get("title") or "").strip()
            url_path = item.get("url") or ""
            url = f"https://segmentfault.com{url_path}" if url_path else ""

            # 时间
            ts = item.get("created", 0) or 0
            created_at = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""

            # 作者
            user = item.get("user") or {}
            author_name = (user.get("name") or "").strip()
            author_url_path = user.get("url") or ""
            author_url = f"https://segmentfault.com{author_url_path}" if author_url_path else ""
            author_avatar = user.get("avatar_url") or ""

            # 专栏
            blog = item.get("blog")
            blog_name = (blog.get("name") or "").strip() if blog else ""
            blog_url_path = blog.get("url") or "" if blog else ""
            blog_url = f"https://segmentfault.com{blog_url_path}" if blog_url_path else ""

            article = {
                "article_id": article_id,
                "title": title,
                "url": url,
                "created_at": created_at,
                "timestamp": ts,
                "votes": item.get("votes", 0) or 0,
                "comments": item.get("comments", 0) or 0,
                "views": item.get("real_views", 0) or 0,
                "author_name": author_name,
                "author_url": author_url,
                "author_avatar": author_avatar,
                "blog_name": blog_name,
                "blog_url": blog_url,
                "cover": item.get("cover") or "",
                "summary": "",
            }
            articles.append(article)

        except Exception as e:
            logger.warning(f"解析单篇文章失败: {e}")
            continue

    logger.info(f"解析到 {len(articles)} 篇文章")
    return articles
