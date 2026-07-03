"""
crawler 日志系统

分层日志 + 监控指标，统一入口。

用法：
  from core.logger import get_logger, Metrics

  logger = get_logger("github_spider")
  logger.info("开始爬取")

  Metrics.incr("crawl.attempt")
  Metrics.incr("crawl.success")
  Metrics.incr("crawl.dedup.bloom")
  Metrics.gauge("repos.stored", 42)
  Metrics.summary()
"""

import logging
import logging.handlers
import os
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# ─── 日志配置 ───────────────────────────────────────────

LOG_DIR = Path(__file__).parent.parent / "data" / "logs"
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def _ensure_log_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    获取一个分层 logger

    日志文件按天轮转，保留 7 天。
    每个 logger 写两份：
      - data/logs/crawler.log       (INFO+, 所有模块汇总)
      - data/logs/<name>.log        (DEBUG+, 模块专属)
    """
    _ensure_log_dir()
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # 避免重复添加 handler

    logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. 总日志（INFO+）
    all_handler = logging.handlers.TimedRotatingFileHandler(
        str(LOG_DIR / "crawler.log"),
        when="midnight", interval=1, backupCount=7, encoding="utf-8",
    )
    all_handler.setLevel(logging.INFO)
    all_handler.setFormatter(formatter)
    logger.addHandler(all_handler)

    # 2. 模块专属日志（DEBUG+）
    mod_handler = logging.handlers.TimedRotatingFileHandler(
        str(LOG_DIR / f"{name}.log"),
        when="midnight", interval=1, backupCount=7, encoding="utf-8",
    )
    mod_handler.setLevel(logging.DEBUG)
    mod_handler.setFormatter(formatter)
    logger.addHandler(mod_handler)

    # 3. 控制台（INFO+）
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


# ─── 监控指标 ───────────────────────────────────────────


class _Metrics:
    """
    轻量指标收集器

    用法：
      Metrics.incr("crawl.attempt")
      Metrics.incr("crawl.success")
      Metrics.gauge("repos.stored", 42)
      Metrics.timing("crawl.duration", 12.5)

    指标类型：
      counter: 计数（incr）
      gauge:   瞬时值（gauge）
      timing:  耗时（timing）

    通过 Metrics.summary() 输出当前会话的统计。
    通过 Metrics.save() 持久化到 JSON 文件。
    """

    def __init__(self):
        self._counters = defaultdict(int)
        self._gauges = {}
        self._timings = defaultdict(list)
        self._start_time = time.time()

    # ─── 计数器 ────────────────────────────────────────

    def incr(self, key: str, value: int = 1):
        """增加计数器"""
        self._counters[key] += value

    def counter(self, key: str) -> int:
        """读取计数器值"""
        return self._counters.get(key, 0)

    # ─── 瞬时值 ────────────────────────────────────────

    def gauge(self, key: str, value):
        """设置瞬时值"""
        self._gauges[key] = value

    def get_gauge(self, key: str):
        return self._gauges.get(key)

    # ─── 耗时 ──────────────────────────────────────────

    def timing(self, key: str, seconds: float):
        """记录一次耗时"""
        self._timings[key].append(seconds)

    def timing_avg(self, key: str) -> float:
        vals = self._timings.get(key, [])
        return sum(vals) / len(vals) if vals else 0.0

    # ─── 输出 ──────────────────────────────────────────

    def summary(self) -> dict:
        """生成当前会话的指标快照"""
        elapsed = time.time() - self._start_time
        data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round(elapsed, 1),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "timings": {
                k: {
                    "count": len(v),
                    "avg": round(sum(v) / len(v), 2) if v else 0,
                    "max": round(max(v), 2) if v else 0,
                }
                for k, v in self._timings.items()
            },
        }

        # 计算衍生指标
        attempts = self._counters.get("crawl.attempt", 0)
        success = self._counters.get("crawl.success", 0)
        if attempts > 0:
            data["derived"] = {
                "success_rate": f"{success / attempts * 100:.1f}%",
                "failure_rate": f"{(attempts - success) / attempts * 100:.1f}%",
            }

        return data

    def print_summary(self):
        """打印可读的指标摘要"""
        s = self.summary()
        lines = [
            "=" * 45,
            "  爬虫监控指标",
            f"  时间: {s['timestamp']}",
            f"  运行时长: {s['elapsed_seconds']}s",
            "=" * 45,
        ]

        if s["counters"]:
            lines.append("  [计数器]")
            for k, v in sorted(s["counters"].items()):
                lines.append(f"    {k:<30} {v:>8}")
        if s["gauges"]:
            lines.append("  [瞬时值]")
            for k, v in sorted(s["gauges"].items()):
                lines.append(f"    {k:<30} {v}")
        if s["timings"]:
            lines.append("  [耗时]")
            for k, v in sorted(s["timings"].items()):
                lines.append(f"    {k:<30} {v['count']}次 均值{v['avg']}s 最大{v['max']}s")
        if "derived" in s:
            lines.append("  [衍生指标]")
            for k, v in s["derived"].items():
                lines.append(f"    {k:<30} {v}")

        lines.append("=" * 45)
        print("\n".join(lines))

    def save(self, path=None):
        """保存指标到 JSON 文件"""
        if path is None:
            path = LOG_DIR / "metrics.json"
        else:
            path = Path(path)
        _ensure_log_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.summary(), f, ensure_ascii=False, indent=2)
        return path

    def reset(self):
        """重置所有指标"""
        self._counters.clear()
        self._gauges.clear()
        self._timings.clear()
        self._start_time = time.time()


# 全局单例
Metrics = _Metrics()


# ─── 快速初始化 ─────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    """一键初始化根日志"""
    get_logger("root", level)
    logging.getLogger("root").info(f"日志系统初始化完成, level={level}, dir={LOG_DIR}")
