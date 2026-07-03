"""
爬虫项目 — 统一入口

支持网站：
  1. segmentfault  — 思否技术博客
  2. github        — GitHub Trending

命令：
  python crawl.py segmentfault                    # 爬取 SegmentFault 最新文章
  python crawl.py segmentfault --detail           # 爬取列表 + 详情
  python crawl.py segmentfault --stats            # 数据统计

  python crawl.py github                           # 爬取 GitHub Trending
  python crawl.py github --language python         # 只爬 Python
  python crawl.py github --stats                   # 数据统计
  python crawl.py github --export                  # 导出到 Excel/CSV/JSON
  python crawl.py github --export --format csv     # 指定格式

  python crawl.py github --analysis               # 数据分析 + 图表
  python crawl.py segmentfault --analysis          # SegmentFault 分析
"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from spider import github_spider, sf_spider  # 先 import 触发注册校验


def main():
    parser = argparse.ArgumentParser(
        description="统一爬虫入口 — 支持多个网站",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("site", type=str,
                        choices=["github", "segmentfault", "sf"],
                        help="目标网站")
    parser.add_argument("--language", type=str, default="",
                        help="GitHub 语言过滤")
    parser.add_argument("--since", type=str, default="daily",
                        choices=["daily", "weekly", "monthly"],
                        help="GitHub 时间范围")
    parser.add_argument("--detail", action="store_true",
                        help="抓取文章详情（SegmentFault）")
    parser.add_argument("--stats", action="store_true",
                        help="数据统计")
    parser.add_argument("--export", action="store_true",
                        help="导出数据")
    parser.add_argument("--format", type=str, default="xlsx",
                        choices=["xlsx", "csv", "json"],
                        help="导出格式")
    parser.add_argument("--analysis", action="store_true",
                        help="数据分析 + 图表")
    parser.add_argument("-i", "--incremental", action="store_true",
                        help="增量更新")

    args = parser.parse_args()

    site = args.site
    if site == "sf":
        site = "segmentfault"

    if site == "github":
        from scripts import github_runner
        github_runner.run(args)
    elif site == "segmentfault":
        from scripts import sf_runner
        sf_runner.run(args)


if __name__ == "__main__":
    main()
