"""
SegmentFault 入口模块

被 crawl.py 调用，也可独立运行：
  python -m scripts.sf_runner --stats
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from spider.base_spider import fetch_page
from parsers.sf_parser import parse_article_list
from parsers.sf_detail_parser import parse_article_detail
from storage.sf_db import (
    get_connection, init_db, save_articles, save_article_detail,
    start_crawl_log, finish_crawl_log, get_statistics, query_articles
)
from core.logger import Metrics

logger = logging.getLogger(__name__)

BLOG_URL = "https://segmentfault.com/blogs/newest"


def run_crawl(incremental=False, db_path=None):
    Metrics.incr("crawl.attempt")
    conn = get_connection(db_path)
    init_db(conn)
    log_id = start_crawl_log(conn)

    html = fetch_page(BLOG_URL, timeout=30, min_delay=0.5, max_delay=1.5)
    if html is None:
        logger.error("抓取失败")
        finish_crawl_log(conn, log_id, 1, 0, 0, status="failed")
        conn.close()
        Metrics.incr("crawl.failure")
        return {"found": 0, "new": 0}

    articles = parse_article_list(html)
    new_added = save_articles(conn, articles)
    finish_crawl_log(conn, log_id, 1, len(articles), new_added)

    Metrics.gauge("articles.stored", len(articles))
    Metrics.incr("crawl.success")

    conn.close()
    logger.info(f"完成: {len(articles)} 篇, 新增 {new_added} 篇")
    return {"found": len(articles), "new": new_added}


def run_detail(db_path=None):
    conn = get_connection(db_path)
    init_db(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.article_id, a.title, a.url
        FROM articles a LEFT JOIN article_details d ON a.article_id = d.article_id
        WHERE d.article_id IS NULL
        ORDER BY a.timestamp DESC
    """)
    rows = cursor.fetchall()
    total = len(rows)
    if total == 0:
        logger.info("所有文章已有详情")
        conn.close()
        return

    logger.info(f"待抓取详情: {total} 篇")
    success = 0
    for i, row in enumerate(rows, 1):
        logger.info(f"[{i}/{total}] {row['title'][:40]}...")
        html = fetch_page(row["url"], timeout=30, min_delay=0.3, max_delay=0.8)
        if html is None:
            continue
        detail = parse_article_detail(html)
        detail["article_id"] = row["article_id"]
        if save_article_detail(conn, detail):
            success += 1
            logger.info(f"  ✓ {len(detail.get('content_text',''))}字, 标签:{detail.get('tags')}")
        if i < total:
            time.sleep(0.5)
    conn.close()
    logger.info(f"完成: {success}/{total}")


def run_stats(db_path=None):
    stats = get_statistics(db_path)
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM article_details")
    detail_count = c.fetchone()[0]
    c.execute("SELECT SUM(LENGTH(content_text)) FROM article_details")
    total_chars = c.fetchone()[0] or 0
    conn.close()

    print("\n" + "=" * 50)
    print("              SegmentFault 数据统计")
    print("=" * 50)
    print(f"  文章总数:      {stats['total_articles']}")
    print(f"  作者总数:      {stats['total_authors']}")
    print(f"  最高阅读数:    {stats['max_views']}")
    print(f"  最高点赞数:    {stats['max_votes']}")
    print(f"  已抓详情:      {detail_count} 篇")
    print(f"  正文总量:      {total_chars:,} 字")
    print(f"  最新文章:      {stats['latest_article']}")
    print("=" * 50)

    articles = query_articles(db_path=db_path, limit=10, order_by="views")
    if articles:
        print(f"\n  {'ID':<20} {'标题':<45} {'阅读':>8} {'点赞':>5} {'评论':>4} {'作者'}")
        print(f"  {'-'*20} {'-'*45} {'-'*8} {'-'*5} {'-'*4} {'-'*20}")
        for a in articles:
            t = a['title'][:43] + ".." if len(a['title']) > 45 else a['title']
            print(f"  {a['article_id']:<20} {t:<45} {a['views']:>8} {a.get('votes',0):>5} {a.get('comments',0):>4} {a['author_name'] or 'N/A'}")


def run(args):
    if args.stats:
        run_stats()
        return
    if args.detail:
        run_detail()
        return
    start = time.time()
    run_crawl(incremental=args.incremental)
    logger.info(f"耗时: {time.time()-start:.1f}s")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--detail", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("-i", "--incremental", action="store_true")
    run(p.parse_args())
