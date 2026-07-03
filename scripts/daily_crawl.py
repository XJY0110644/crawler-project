"""
每日自动爬取 + 分析报告
直接导入模块调用，不走子进程。
"""

import sys
import os
from pathlib import Path

# 确保项目根目录在路径中
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows cmd gbk 编码处理
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def run_crawl():
    print("=== 爬取 GitHub Trending ===")
    from scripts.github_runner import run_crawl as _crawl
    r = _crawl()
    print(f"  {r['found']} 个入库, 已存在 {r.get('skipped_existing',0)}, 布隆去重 {r.get('skipped_bloom',0)}")
    print("  [成功]")
    return True


def run_sf():
    print("=== 爬取 SegmentFault ===")
    from scripts.sf_runner import run_crawl as _sf
    r = _sf()
    print(f"  {r['found']} 篇, 新增 {r['new']}")
    print("  [成功]")
    return True


def run_analysis():
    print("=== GitHub 分析图表 ===")
    from scripts.analysis import main as _analysis
    _analysis()
    print("  [成功]")
    return True


def main():
    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 50)
    print("  每日爬取 + 分析报告")
    print(f"  时间: {now}")
    print("=" * 50)

    from core.logger import Metrics

    results = []
    results.append(("GitHub Trending", run_crawl()))
    results.append(("SegmentFault", run_sf()))
    results.append(("分析报告", run_analysis()))

    # 读取报告
    report_path = ROOT / "data" / "report.txt"
    report_text = ""
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")

    print()
    print("=" * 50)
    print("  执行汇总")
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  {status} {name}")
    print(f"  完成: {sum(1 for _, ok in results if ok)}/{len(results)}")
    print("=" * 50)

    # 保存指标
    Metrics.save()
    print()

    # 异常告警检查
    from core.alerts import check_alerts
    alerts = check_alerts(Metrics.summary())
    if alerts:
        print("⚠️  告警:")
        for a in alerts:
            print(f"  {a}")
        print()

    if report_text:
        print(report_text)


if __name__ == "__main__":
    main()
