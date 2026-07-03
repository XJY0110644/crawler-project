"""
详情页解析器 — 从文章详情页提取：
1. 正文内容（HTML + 纯文本）
2. 标签列表
3. 作者详细信息
"""

import re
import json
import logging
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_next_data(html: str) -> Optional[dict]:
    """从 HTML 中提取 __NEXT_DATA__ JSON"""
    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def parse_article_detail(html: str) -> dict:
    """
    解析文章详情页，返回完整信息

    返回字段：
    {
        "article_id": int,
        "content_html": "正文 HTML",
        "content_text": "正文纯文本",
        "tags": ["标签1", "标签2"],
        "author_name": "作者名",
        "author_avatar": "头像URL",
        "author_excerpt": "作者简介",
        "author_followers": 粉丝数,
        "author_articles": 文章数,
        "author_rank": 排名,
    }
    """
    result = {}
    data = extract_next_data(html)

    if data:
        try:
            art_detail = data["props"]["pageProps"]["initialState"]["articleDetail"]["artDetail"]
            article_id = list(art_detail.keys())[0]
            detail = art_detail[article_id]

            article = detail.get("article", {})
            result["article_id"] = article.get("id")

            # 标签
            tags_raw = article.get("tags", [])
            result["tags"] = [t.get("name", "") for t in tags_raw if isinstance(t, dict)]

            # 作者信息（来自 __NEXT_DATA__）
            user = article.get("user", {})
            if isinstance(user, dict):
                result["author_name"] = user.get("name", "")
                result["author_avatar"] = user.get("avatar_url", "")
                result["author_excerpt"] = _strip_html(user.get("excerpt", ""))
                result["author_followers"] = user.get("followers", 0)
                result["author_articles"] = user.get("articles", 0)
                result["author_rank"] = user.get("rank", 0)
            else:
                result["author_name"] = ""
                result["author_avatar"] = ""
                result["author_excerpt"] = ""
                result["author_followers"] = 0
                result["author_articles"] = 0
                result["author_rank"] = 0

        except (KeyError, TypeError, IndexError) as e:
            logger.warning(f"从 __NEXT_DATA__ 提取部分字段失败: {e}")
            result.setdefault("tags", [])
            result.setdefault("author_name", "")
            result.setdefault("author_avatar", "")
            result.setdefault("author_excerpt", "")
            result.setdefault("author_followers", 0)
            result.setdefault("author_articles", 0)
            result.setdefault("author_rank", 0)

    # 正文内容：从 HTML 中提取（不在 __NEXT_DATA__ 里）
    soup = BeautifulSoup(html, "lxml")
    article_tag = soup.find("article", class_=re.compile(r"\barticle\b.*\bfmt\b"))
    if not article_tag:
        # 备选：找任意 article 标签
        article_tag = soup.find("article", class_=re.compile(r"(article|content|fmt)"))

    if article_tag:
        result["content_html"] = str(article_tag)
        result["content_text"] = article_tag.get_text(separator="\n", strip=True)
    else:
        logger.warning("未找到文章正文 HTML")
        result["content_html"] = ""
        result["content_text"] = ""

    # 如果从 __NEXT_DATA__ 没取到 article_id，从 URL 提取
    if not result.get("article_id"):
        m = re.search(r"/a/(\d+)", html)
        if m:
            result["article_id"] = int(m.group(1))

    # 补默认值
    result.setdefault("tags", [])
    for key in ["author_name", "author_avatar", "author_excerpt"]:
        result.setdefault(key, "")
    for key in ["author_followers", "author_articles", "author_rank"]:
        result.setdefault(key, 0)

    return result


def _strip_html(text: str) -> str:
    """去除 HTML 标签"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_detail_batch(html_list: list[str]) -> list[dict]:
    """批量解析详情页"""
    return [parse_article_detail(html) for html in html_list]
