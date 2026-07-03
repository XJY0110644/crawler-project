"""
GitHub Trending 入口模块

被 crawl.py 调用，也可独立运行：
  python -m scripts.github_runner --stats
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from spider.base_spider import fetch_page
from parsers.github_parser import parse_trending
from storage.github_db import (
    get_connection, init_db, save_repos, get_statistics, query_repos,
    find_new_repos, get_repo_names
)
from core.bloom_filter import BloomFilter
from core.logger import Metrics

logger = logging.getLogger(__name__)

BASE_URL = "https://github.com/trending"
CHART_DIR = ROOT / "data" / "charts"


def build_url(language="", since="daily"):
    url = BASE_URL
    if language:
        url += f"/{language}"
    if since != "daily":
        url += f"?since={since}"
    return url


def run_crawl(language="", since="daily", db_path=None):
    Metrics.incr("crawl.attempt")

    conn = get_connection(db_path)
    init_db(conn)

    url = build_url(language, since)
    logger.info(f"目标: {url}")
    html = fetch_page(url, timeout=30, min_delay=0.5, max_delay=1.5)
    if html is None:
        logger.error("抓取失败")
        conn.close()
        Metrics.incr("crawl.failure")
        return {"found": 0, "new": 0, "skipped_bloom": 0, "skipped_simhash": 0}

    repos = parse_trending(html)
    logger.info(f"页面解析到 {len(repos)} 个仓库")

    Metrics.gauge("page.repo_count", len(repos))

    # ── 第 0 道去重：根据 repo_full_name 排除库里已有的 ──
    existing_names = get_repo_names(conn)

    # ── 第 1 道去重：布隆过滤器（本次爬取内同一 repo 不重复入库） ──
    bloom = BloomFilter(capacity=len(repos) + 50)

    passed_bloom = 0
    skipped_existing = 0
    final_repos = []

    for repo in repos:
        name = repo["repo_full_name"]

        # 库里已有则跳过
        if name in existing_names:
            skipped_existing += 1
            Metrics.incr("dedup.existing")
            continue

        # 布隆过滤：本次已见过则跳过
        if name in bloom:
            Metrics.incr("dedup.bloom")
            continue
        bloom.add(name)
        passed_bloom += 1

        # SimHash 指纹（仅存储，不用于去重）
        desc = repo.get("description", "")
        if desc and len(desc) > 10:
            from core.simhash import compute_fingerprint
            repo["simhash"] = str(compute_fingerprint(desc))
        final_repos.append(repo)

    # 批量入库（upsert 自动处理 ID 重复）
    skipped_bloom = len(repos) - passed_bloom - skipped_existing
    result = save_repos(conn, final_repos)

    Metrics.gauge("repos.stored", len(final_repos))
    Metrics.incr("crawl.success")

    logger.info(
        f"完成: 解析{len(repos)}个, "
        f"已存在{skipped_existing}个, "
        f"布隆去重{skipped_bloom}个, "
        f"入库{len(final_repos)}个 "
        f"(新增{result['new']}, 更新{result['updated']})"
    )
    conn.close()
    return {
        "found": len(final_repos),
        "skipped_existing": skipped_existing,
        "skipped_bloom": skipped_bloom,
        **result,
    }


def run_export(export_format="xlsx", db_path=None):
    import csv, json
    try:
        import pandas
    except ImportError:
        logger.error("导出 Excel 需要: pip install pandas openpyxl")
        return

    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT repo_full_name, repo_name, repo_owner, repo_url,
               description, language, stars, forks, stars_today
        FROM repos ORDER BY stars_today DESC
    """)
    columns = [d[0] for d in c.description]
    rows = c.fetchall()
    conn.close()
    if not rows:
        logger.error("数据库为空")
        return

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = ROOT / "data" / "github"
    data_dir.mkdir(exist_ok=True)

    if export_format == "xlsx":
        import pandas as pd
        path = data_dir / f"github_trending_{now}.xlsx"
        pd.DataFrame(rows, columns=columns).to_excel(path, index=False)
    elif export_format == "csv":
        path = data_dir / f"github_trending_{now}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(columns)
            w.writerows(rows)
    elif export_format == "json":
        path = data_dir / f"github_trending_{now}.json"
        data = [dict(zip(columns, r)) for r in rows]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"导出完成: {path} ({len(rows)} 条)")


def run_stats(db_path=None):
    stats = get_statistics(db_path)
    print("\n" + "=" * 50)
    print("              GitHub Trending 数据统计")
    print("=" * 50)
    print(f"  累计收录仓库:  {stats['total_repos']}")
    print(f"  编程语言种类:  {stats['languages']}")
    print(f"  最高星数:      {stats['max_stars']:,}")
    print(f"  最高日增星:    {stats['max_stars_today']:,}")
    print(f"  今日最热:      {stats['hottest_today']}")
    print(f"  历史记录天数:  {stats['history_days']}")
    print(f"  最后爬取:      {stats['last_crawl']}")
    print("=" * 50)
    repos = query_repos(db_path=db_path, order_by="stars_today")
    if repos:
        print(f"\n  今日趋势 TOP 15:")
        print(f"  {'仓库':<35} {'语言':<12} {'总星':>8} {'今日':>8} {'描述'}")
        print(f"  {'-'*35} {'-'*12} {'-'*8} {'-'*8} {'-'*30}")
        for r in repos:
            desc = (r['description'] or '')[:28]
            if len(desc) > 28: desc += '..'
            print(f"  {r['repo_full_name']:<35} {r['language'] or '-':<12} {r['stars']:>8,} {r['stars_today']:>6,}★ {desc}")


def run_analysis(db_path=None):
    """直接导入 analysis 模块并运行"""
    sys.path.insert(0, str(ROOT))
    from scripts.analysis import main as analysis_main
    # 临时覆写 DB_PATH
    import scripts.analysis as ana
    if db_path:
        ana.DB_PATH = Path(db_path)
    ana.main()


def run(args):
    if args.stats:
        run_stats()
        return
    if args.export:
        run_export(args.format)
        return
    if args.analysis:
        run_analysis()
        return
    start = time.time()
    run_crawl(language=args.language, since=args.since)
    logger.info(f"耗时: {time.time()-start:.1f}s")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--language", default="")
    p.add_argument("--since", default="daily")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--export", action="store_true")
    p.add_argument("--format", default="xlsx")
    p.add_argument("--analysis", action="store_true")
    run(p.parse_args())
