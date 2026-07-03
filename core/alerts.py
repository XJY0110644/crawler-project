"""
异常告警模块

监控爬虫指标，当超过阈值时生成告警报告。

检查项：
  1. 爬取失败率 > 20%
  2. 连续 N 次爬取无新增数据
  3. 数据量骤降（相比上次 < 50%）

用法：
  from core.alerts import check_alerts
  alerts = check_alerts(metrics_summary)
  if alerts:
      print("\\n".join(alerts))
"""

import json
import os
from pathlib import Path

ALERT_STATE_FILE = Path(__file__).parent.parent / "data" / "logs" / "alert_state.json"


def _load_state() -> dict:
    """加载历史告警状态"""
    if ALERT_STATE_FILE.exists():
        try:
            return json.loads(ALERT_STATE_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {
        "last_success_count": 0,
        "consecutive_empty": 0,
        "last_alert_time": "",
    }


def _save_state(state: dict):
    ALERT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ALERT_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def check_alerts(metrics: dict) -> list[str]:
    """
    检查指标并返回告警列表

    metrics 格式参考 Metrics.summary() 的输出：
    {
        "counters": {"crawl.attempt": 2, "crawl.success": 1, ...},
        "gauges": {"repos.stored": 42},
        "derived": {"success_rate": "50.0%", "failure_rate": "50.0%"},
    }
    """
    alerts = []
    state = _load_state()

    counters = metrics.get("counters", {})
    gauges = metrics.get("gauges", {})
    derived = metrics.get("derived", {})

    # ── 1. 失败率检查 ──────────────────────────────────
    failure_rate_str = derived.get("failure_rate", "0.0%")
    failure_rate = float(failure_rate_str.strip("%"))
    if failure_rate > 20:
        alerts.append(
            f"[告警] 爬取失败率 {failure_rate_str}，超过阈值 20%。"
            f" 尝试 {counters.get('crawl.attempt', 0)} 次，"
            f"成功 {counters.get('crawl.success', 0)} 次"
        )

    # ── 2. 连续空数据检查（仅当确实 0 入库且 0 已存在时才告警） ──
    new_count = gauges.get("repos.stored", 0)
    new_articles = gauges.get("articles.stored", 0)
    if new_count == 0 and new_articles == 0:
        state["consecutive_empty"] = state.get("consecutive_empty", 0) + 1
    else:
        state["consecutive_empty"] = 0

    if state["consecutive_empty"] >= 3:
        alerts.append(
            f"[告警] 连续 {state['consecutive_empty']} 次爬取无新增数据，"
            f"可能数据源变更或网络异常"
        )

    # ── 3. 数据量骤降检查 ──────────────────────────────
    last_count = state.get("last_success_count", 0)
    if last_count > 0 and new_count > 0:
        ratio = new_count / last_count
        if ratio < 0.5:
            alerts.append(
                f"[告警] 数据量骤降: 上次 {last_count} 条 → 本次 {new_count} 条 "
                f"(仅上次的 {ratio:.0%})"
            )

    # ── 4. 更新状态 ────────────────────────────────────
    if new_count > 0:
        state["last_success_count"] = new_count
    if alerts:
        state["last_alert_time"] = metrics.get("timestamp", "")
    _save_state(state)

    return alerts


def clear_state():
    """重置告警状态"""
    if ALERT_STATE_FILE.exists():
        ALERT_STATE_FILE.unlink()
