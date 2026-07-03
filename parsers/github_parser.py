"""
GitHub Trending 解析器

从 GitHub Trending 页面的 HTML 中提取仓库信息。
"""

import re
import logging
from datetime import datetime

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_trending(html: str) -> list[dict]:
    """
    解析 GitHub Trending 首页

    返回字段：
        repo_full_name: "owner/repo"
        repo_name: "repo"
        repo_owner: "owner"
        repo_url: 完整 URL
        description: 描述
        language: 主要编程语言
        stars: 总星数（整数）
        forks: fork 数（整数）
        stars_today: 今日新增星数（整数）
        built_by: 贡献者列表 ["user1", "user2"]
    """
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article.Box-row")

    if not articles:
        logger.warning("未找到仓库列表，页面结构可能已变化")
        return []

    repos = []
    for article in articles:
        try:
            # 仓库名（格式：owner/repo）
            h2 = article.select_one("h2")
            if not h2 or not h2.a:
                continue

            full_name = h2.get_text(strip=True).replace(" ", "")
            href = h2.a.get("href", "")
            repo_url = f"https://github.com{href}" if href else ""

            parts = full_name.split("/")
            repo_owner = parts[0] if len(parts) > 0 else ""
            repo_name = parts[1] if len(parts) > 1 else ""

            # 描述
            p_tag = article.select_one("p")
            description = p_tag.get_text(strip=True) if p_tag else ""

            # 编程语言
            lang_span = article.select_one('span[itemprop="programmingLanguage"]')
            language = lang_span.get_text(strip=True) if lang_span else ""

            # 星数、fork（都在 a.Link--muted 里）
            links = article.select("a.Link--muted")
            stars = 0
            forks = 0
            for link in links:
                text = link.get_text(strip=True)
                if not text:
                    continue
                # 有可能只有一个数字，也可能有"stars"或"forks"字样
                num = _parse_count(text)
                if "fork" in text.lower():
                    forks = num
                elif stars == 0:
                    stars = num

            # 今日 star
            today_el = article.select_one(".d-inline-block.float-sm-right")
            if not today_el:
                today_el = article.select_one(".float-sm-right")
            if today_el:
                today_text = today_el.get_text(strip=True)
                # 格式: "3,191 stars today"
                stars_today = _parse_count(today_text)
            else:
                stars_today = 0

            # 贡献者 (Built by)
            built_by = []
            for avatar in article.select("a[data-hovercard-type='user']"):
                user_href = avatar.get("href", "")
                if user_href:
                    user_name = user_href.strip("/").split("/")[-1]
                    if user_name:
                        built_by.append(user_name)

            repo = {
                "repo_full_name": f"{repo_owner}/{repo_name}",
                "repo_name": repo_name,
                "repo_owner": repo_owner,
                "repo_url": repo_url,
                "description": description,
                "language": language,
                "stars": stars,
                "forks": forks,
                "stars_today": stars_today,
                "built_by": built_by,
            }
            repos.append(repo)

        except Exception as e:
            logger.warning(f"解析仓库失败: {e}")
            continue

    logger.info(f"解析到 {len(repos)} 个仓库")
    return repos


def _parse_count(text: str) -> int:
    """
    解析数字字符串为整数

    例子：
        "3,191 stars today" -> 3191
        "37,934" -> 37934
        "1.2k stars" -> 1200
    """
    if not text:
        return 0

    # 提取数字部分（去掉字母和标点，保留 . 和 k/m）
    text = text.strip()

    # 处理 k/m 后缀
    multiplier = 1
    text_lower = text.lower()
    if "k" in text_lower:
        multiplier = 1000
    elif "m" in text_lower:
        multiplier = 1000000

    # 提取纯数字（可能有逗号或点）
    nums = re.findall(r"[\d,.]+", text)
    if not nums:
        return 0

    try:
        num_str = nums[0].replace(",", "")
        if "." in num_str:
            num = float(num_str)
        else:
            num = int(num_str)
        return int(num * multiplier)
    except (ValueError, IndexError):
        return 0
