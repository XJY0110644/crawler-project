"""
GitHub Trending 数据分析 + 可视化

分析内容：
1. 编程语言分布 — 饼图
2. 今日最热仓库 TOP 10 — 条形图
3. 总星数 TOP 10 — 条形图
4. 星数与今日新增的关系 — 散点图
5. 多语言对比分析 — 分组条形图
6. 汇总报告 — 文本

图表保存在 data/charts/ 目录下
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 无界面模式，不弹窗
import matplotlib.pyplot as plt
import pandas as pd

# 让 matplotlib 支持中文
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# 路径
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "github" / "github_trending.db"
CHART_DIR = BASE_DIR / "data" / "charts"

# 颜色方案
COLORS = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
          "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"]


def load_data() -> pd.DataFrame:
    """从 SQLite 加载数据"""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql("""
        SELECT repo_full_name, repo_name, repo_owner, language,
               stars, forks, stars_today, built_by, created_at
        FROM repos
        ORDER BY stars DESC
    """, conn)
    conn.close()
    return df


def chart_language_distribution(df: pd.DataFrame):
    """图1：编程语言分布 — 饼图"""
    lang_counts = df[df["language"] != ""]["language"].value_counts()
    others = lang_counts[lang_counts <= 1]
    if len(others) > 0:
        lang_counts = lang_counts[lang_counts > 1].copy()
        lang_counts["其他"] = others.sum()

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        lang_counts.values,
        labels=lang_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=COLORS[:len(lang_counts)],
        textprops={"fontsize": 11},
    )
    ax.set_title("GitHub Trending 编程语言分布", fontsize=16, fontweight="bold", pad=20)

    total = lang_counts.sum()
    ax.text(0, -1.3, f"共 {total} 个仓库", ha="center", fontsize=11, color="gray")

    plt.tight_layout()
    path = CHART_DIR / "01_语言分布.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK {path.name}")
    return path


def chart_today_top10(df: pd.DataFrame):
    """图2：今日最热 TOP 10 — 横向条形图"""
    top = df.nlargest(10, "stars_today")

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(range(len(top)), top["stars_today"].values,
                   color=COLORS[:len(top)], height=0.6)

    for i, (_, row) in enumerate(top.iterrows()):
        label = f"{row['stars_today']:,}★"
        ax.text(row["stars_today"] + 50, i, label,
                va="center", fontsize=9, color="#333")

    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top["repo_full_name"].values, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("今日新增星数", fontsize=11)
    ax.set_title("今日最热仓库 TOP 10", fontsize=16, fontweight="bold", pad=15)

    # 在条形上显示语言标签
    for i, (_, row) in enumerate(top.iterrows()):
        if row.get("language"):
            ax.text(row["stars_today"] * 0.02, i - 0.25,
                    f"({row['language']})", va="top", fontsize=8,
                    color="gray", alpha=0.8)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = CHART_DIR / "02_今日最热TOP10.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK {path.name}")
    return path


def chart_total_stars_top10(df: pd.DataFrame):
    """图3：总星数 TOP 10"""
    top = df.nlargest(10, "stars")

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(top)), top["stars"].values,
                  color=COLORS[:len(top)], width=0.6)

    for i, (_, row) in enumerate(top.iterrows()):
        label = f"{row['stars']:,}"
        ax.text(i, row["stars"] + 2000, label,
                ha="center", fontsize=9, color="#333", rotation=0)

    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top["repo_full_name"].values, fontsize=8, rotation=20, ha="right")
    ax.set_ylabel("总星数", fontsize=11)
    ax.set_title("总星数 TOP 10 仓库", fontsize=16, fontweight="bold", pad=15)

    # 标注语言
    for i, (_, row) in enumerate(top.iterrows()):
        if row.get("language"):
            ax.text(i, row["stars"] * 0.02, row["language"],
                    ha="center", fontsize=8, color="white", fontweight="bold")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = CHART_DIR / "03_总星数TOP10.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK {path.name}")
    return path


def chart_stars_vs_today(df: pd.DataFrame):
    """图4：总星数 vs 今日新增 — 散点图"""
    fig, ax = plt.subplots(figsize=(10, 7))

    # 按编程语言着色
    languages = df[df["language"] != ""]["language"].unique()
    color_map = {lang: COLORS[i % len(COLORS)] for i, lang in enumerate(languages)}

    for lang in languages:
        subset = df[df["language"] == lang]
        ax.scatter(subset["stars"], subset["stars_today"],
                   label=lang, s=subset["stars_today"] * 2 + 30,
                   color=color_map[lang], alpha=0.7, edgecolors="white", linewidth=0.5)

    # 标注仓库名
    for _, row in df.iterrows():
        ax.annotate(
            row["repo_full_name"].split("/")[1] if "/" in row["repo_full_name"] else row["repo_full_name"],
            (row["stars"], row["stars_today"]),
            fontsize=7, alpha=0.7,
            xytext=(5, 5), textcoords="offset points",
        )

    ax.set_xlabel("总星数", fontsize=11)
    ax.set_ylabel("今日新增星数", fontsize=11)
    ax.set_title("总星数 vs 今日热度", fontsize=16, fontweight="bold", pad=15)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # 格式化成 k 单位
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1000:.0f}k"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1000:.1f}k"))

    plt.tight_layout()
    path = CHART_DIR / "04_星数vs热度分布.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK {path.name}")
    return path


def chart_language_stars(df: pd.DataFrame):
    """图5：各语言总星数对比 — 聚合条形图"""
    lang_stats = df[df["language"] != ""].groupby("language").agg({
        "stars": "sum",
        "stars_today": "sum",
        "repo_full_name": "count",
    }).sort_values("stars", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    y_pos = range(len(lang_stats))
    height = 0.35

    bars1 = ax.barh([y + height / 2 for y in y_pos], lang_stats["stars"].values,
                    height, label="总星数", color="#4ECDC4", alpha=0.8)
    bars2 = ax.barh([y - height / 2 for y in y_pos], lang_stats["stars_today"].values,
                    height, label="今日新增", color="#FF6B6B", alpha=0.8)

    # 数量标注
    for i, (_, row) in enumerate(lang_stats.iterrows()):
        count = int(row["repo_full_name"])
        ax.text(row["stars"] + 2000, i + height / 2,
                f"{int(row['stars']):,}", va="center", fontsize=8, color="#333")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(lang_stats.index, fontsize=10)
    ax.set_xlabel("星数", fontsize=11)
    ax.set_title("各编程语言星数对比", fontsize=16, fontweight="bold", pad=15)
    ax.legend(fontsize=10, loc="lower right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = CHART_DIR / "05_语言星数对比.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK {path.name}")
    return path


def generate_text_report(df: pd.DataFrame) -> str:
    """生成文本汇总报告"""
    total_repos = len(df)
    total_stars = df["stars"].sum()
    total_today = df["stars_today"].sum()
    languages = df[df["language"] != ""]["language"].nunique()

    # 最热仓库
    hottest = df.loc[df["stars_today"].idxmax()]
    most_starred = df.loc[df["stars"].idxmax()]

    # 语言统计
    lang_counts = df[df["language"] != ""]["language"].value_counts()

    lines = []
    lines.append("=" * 55)
    lines.append("   GitHub Trending 数据分析报告")
    lines.append(f"   生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 55)
    lines.append("")
    lines.append(f"  📊 概览")
    lines.append(f"     仓库总数:    {total_repos}")
    lines.append(f"     编程语言数:  {languages}")
    lines.append(f"     累计总星数:  {total_stars:,}")
    lines.append(f"     今日新增星:  {total_today:,}")
    lines.append("")
    lines.append(f"  🔥 今日最热")
    lines.append(f"     {hottest['repo_full_name']}")
    lines.append(f"     今日 +{hottest['stars_today']:,} 星 | 总 {hottest['stars']:,} 星")
    if hottest.get("language"):
        lines.append(f"     语言: {hottest['language']}")
    if hottest.get("description"):
        desc = hottest["description"][:80]
        lines.append(f"     {desc}")
    lines.append("")
    lines.append(f"  ⭐ 总星数最高")
    lines.append(f"     {most_starred['repo_full_name']}")
    lines.append(f"     {most_starred['stars']:,} 星")
    lines.append("")
    lines.append(f"  🗂️ 语言分布")
    for lang, count in lang_counts.items():
        pct = count / total_repos * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"     {lang:<12} {bar} {count:>2} ({pct:.0f}%)")
    lines.append("")
    lines.append(f"  🖼️ 图表已保存到 data/charts/ 目录")
    lines.append("=" * 55)

    return "\n".join(lines)


def main():
    print("GitHub Trending 数据分析")
    print("=" * 40)

    # 准备目录
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    # 加载数据
    print("\n[1/6] 加载数据...")
    df = load_data()
    print(f"      {len(df)} 个仓库, {df['language'].nunique()} 种语言")

    # 生成图表
    print("\n[2/6] 语言分布饼图...")
    chart_language_distribution(df)

    print("[3/6] 今日最热 TOP 10...")
    chart_today_top10(df)

    print("[4/6] 总星数 TOP 10...")
    chart_total_stars_top10(df)

    print("[5/6] 星数 vs 热度散点图...")
    chart_stars_vs_today(df)

    print("[6/6] 语言对比图...")
    chart_language_stars(df)

    # 生成文本报告
    report = generate_text_report(df)
    report_path = CHART_DIR.parent / "report.txt"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n  ✓ report.txt")

    print("\n" + "=" * 40)
    print(f"完成！图表保存在: {CHART_DIR}")
    print(f"报告: {report_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
