"""
通用爬虫核心 — 网络请求 + 反爬处理

所有爬虫共享的底层模块。包含：
- 随机 User-Agent 池
- 请求间隔
- 自动重试（429/5xx）
- Session 连接池复用
- 代理轮换预留接口
"""

import random
import time
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def random_ua() -> str:
    return random.choice(USER_AGENTS)


def build_headers(referer: str = "https://github.com") -> dict:
    """构建完整请求头"""
    headers = HEADERS_TEMPLATE.copy()
    headers["User-Agent"] = random_ua()
    headers["Referer"] = referer
    return headers


def create_session() -> requests.Session:
    """创建带重试机制的 Session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_page(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: int = 15,
    min_delay: float = 1.5,
    max_delay: float = 3.0,
    max_retries: int = 3,
) -> Optional[str]:
    """
    抓取页面内容

    参数：
        url: 目标 URL
        session: 可复用的 Session
        timeout: 超时秒数
        min_delay / max_delay: 请求间隔随机范围
        max_retries: 最大重试次数

    返回：页面 HTML 文本，失败返回 None
    """
    own_session = False
    if session is None:
        session = create_session()
        own_session = True

    headers = build_headers()

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                delay = random.uniform(min_delay * 2, max_delay * 2)
                logger.info(f"  第 {attempt} 次重试，等待 {delay:.1f}s...")
                time.sleep(delay)
            else:
                delay = random.uniform(min_delay, max_delay)
                time.sleep(delay)

            logger.info(f"[{attempt}/{max_retries}] GET {url}")
            resp = session.get(url, headers=headers, timeout=timeout)

            if resp.status_code == 200:
                content = resp.text
                if len(content) < 500:
                    logger.warning(f"  内容过短 (len={len(content)})，可能被反爬")
                    if attempt < max_retries:
                        headers = build_headers()
                        time.sleep(random.uniform(3, 5))
                        continue
                    return None
                return content

            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                logger.warning(f"  429 限流，等待 {retry_after}s")
                time.sleep(int(retry_after) + random.uniform(1, 3))
                continue

            elif resp.status_code == 403:
                logger.warning("  403 禁止，换 UA")
                headers = build_headers()
                time.sleep(random.uniform(3, 5))
                continue

            else:
                logger.warning(f"  状态码 {resp.status_code}")
                time.sleep(random.uniform(2, 4))

        except requests.exceptions.Timeout:
            logger.warning(f"  超时 (attempt {attempt})")
            time.sleep(random.uniform(3, 5))
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"  连接错误: {e}")
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            logger.error(f"  未知错误: {e}")
            time.sleep(3)

    logger.error(f"  所有重试均失败: {url}")
    return None
