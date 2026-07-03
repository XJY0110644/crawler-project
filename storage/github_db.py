"""
GitHub Trending 存储层 — SQLite

和 SegmentFault 是独立的数据库文件，各自独立管理。
"""

import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "github" / "github_trending.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(conn: sqlite3.Connection = None, db_path: str = None):
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS repos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_full_name  TEXT NOT NULL,       -- "owner/repo"
                repo_name       TEXT NOT NULL,       -- "repo"
                repo_owner      TEXT NOT NULL,       -- "owner"
                repo_url        TEXT NOT NULL,
                description     TEXT DEFAULT '',
                language        TEXT DEFAULT '',
                stars           INTEGER DEFAULT 0,
                forks           INTEGER DEFAULT 0,
                stars_today     INTEGER DEFAULT 0,
                built_by        TEXT DEFAULT '[]',   -- JSON 数组
                simhash         TEXT DEFAULT '0',   -- SimHash 指纹（64位整数转字符串）
                created_at      TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(repo_full_name)
            );

            CREATE INDEX IF NOT EXISTS idx_repos_stars
                ON repos(stars DESC);

            CREATE INDEX IF NOT EXISTS idx_repos_language
                ON repos(language);

            CREATE TABLE IF NOT EXISTS trending_history (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id  INTEGER,
                stars    INTEGER DEFAULT 0,
                forks    INTEGER DEFAULT 0,
                stars_today INTEGER DEFAULT 0,
                rank     INTEGER DEFAULT 0,
                date     TEXT DEFAULT (date('now','localtime')),
                FOREIGN KEY (repo_id) REFERENCES repos(id)
            );

            CREATE INDEX IF NOT EXISTS idx_history_date
                ON trending_history(date);
        """)
        conn.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        if close_later:
            conn.close()


def save_repos(conn: sqlite3.Connection, repos: list[dict]) -> dict:
    """
    批量保存仓库，自动去重。
    返回 {"new": 新增数, "updated": 更新数}
    """
    result = {"new": 0, "updated": 0}
    if not repos:
        return result

    cursor = conn.cursor()

    for repo in repos:
        try:
            cursor.execute("""
                INSERT INTO repos (
                    repo_full_name, repo_name, repo_owner, repo_url,
                    description, language, stars, forks, stars_today, built_by, simhash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_full_name) DO UPDATE SET
                    stars = excluded.stars,
                    forks = excluded.forks,
                    stars_today = excluded.stars_today,
                    description = excluded.description,
                    language = excluded.language,
                    built_by = excluded.built_by,
                    simhash = excluded.simhash
            """, (
                repo["repo_full_name"],
                repo["repo_name"],
                repo["repo_owner"],
                repo["repo_url"],
                repo.get("description", ""),
                repo.get("language", ""),
                repo.get("stars", 0),
                repo.get("forks", 0),
                repo.get("stars_today", 0),
                json.dumps(repo.get("built_by", []), ensure_ascii=False),
                repo.get("simhash", "0"),
            ))

            if cursor.rowcount == 1:
                result["new"] += 1
            else:
                result["updated"] += 1

            # 写入历史记录
            cursor.execute("""
                INSERT INTO trending_history (repo_id, stars, forks, stars_today)
                VALUES (
                    (SELECT id FROM repos WHERE repo_full_name = ?),
                    ?, ?, ?
                )
            """, (
                repo["repo_full_name"],
                repo.get("stars", 0),
                repo.get("forks", 0),
                repo.get("stars_today", 0),
            ))

        except Exception as e:
            logger.warning(f"保存 {repo.get('repo_full_name')} 失败: {e}")
            continue

    conn.commit()
    logger.info(f"保存完成: 新增 {result['new']}, 更新 {result['updated']}")
    return result


def get_statistics(conn: sqlite3.Connection = None, db_path: str = None) -> dict:
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM repos")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(DISTINCT language) FROM repos WHERE language != ''")
        languages = c.fetchone()[0]

        c.execute("SELECT MAX(stars) FROM repos")
        max_stars = c.fetchone()[0] or 0

        c.execute("SELECT MAX(stars_today) FROM repos")
        max_today = c.fetchone()[0] or 0

        c.execute("SELECT COUNT(DISTINCT date) FROM trending_history")
        history_days = c.fetchone()[0]

        c.execute("SELECT MAX(created_at) FROM repos")
        last_crawl = c.fetchone()[0] or "N/A"

        c.execute("""
            SELECT repo_full_name, stars, stars_today
            FROM repos ORDER BY stars_today DESC LIMIT 1
        """)
        hottest = c.fetchone()
        hottest_str = f"{hottest['repo_full_name']} (+{hottest['stars_today']}/d)" if hottest else "N/A"

        return {
            "total_repos": total,
            "languages": languages,
            "max_stars": max_stars,
            "max_stars_today": max_today,
            "history_days": history_days,
            "last_crawl": last_crawl,
            "hottest_today": hottest_str,
            "db_path": str(DEFAULT_DB_PATH),
        }
    finally:
        if close_later:
            conn.close()


def query_repos(conn=None, db_path=None, order_by="stars_today", limit=15) -> list[dict]:
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    allowed = ["stars", "stars_today", "forks"]
    if order_by not in allowed:
        order_by = "stars_today"

    try:
        c = conn.cursor()
        c.execute(f"""
            SELECT repo_full_name, repo_url, description, language,
                   stars, forks, stars_today
            FROM repos
            ORDER BY {order_by} DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in c.fetchall()]
    finally:
        if close_later:
            conn.close()


def find_new_repos(
    conn: sqlite3.Connection, current_names: set
) -> list[str]:
    """
    给定本次爬到的 repo_full_name 集合，返回数据库中不存在的新 repo 列表

    用于增量更新时判断哪些是真正的新仓库。
    """
    if not current_names:
        return []
    c = conn.cursor()
    placeholders = ",".join("?" for _ in current_names)
    c.execute(f"""
        SELECT repo_full_name FROM repos
        WHERE repo_full_name IN ({placeholders})
    """, tuple(current_names))
    existing = {row["repo_full_name"] for row in c.fetchall()}
    return list(current_names - existing)


def get_all_fingerprints(conn: sqlite3.Connection) -> list[int]:
    """
    获取数据库中所有非零的 SimHash 指纹

    用于内容级去重：新文本算指纹后和这些比汉明距离。
    """
    c = conn.cursor()
    c.execute("SELECT simhash FROM repos WHERE simhash != '0'")
    result = []
    for row in c.fetchall():
        try:
            result.append(int(row["simhash"]))
        except (ValueError, TypeError):
            continue
    return result


def get_repo_names(conn: sqlite3.Connection) -> set:
    """获取数据库中所有 repo 名"""
    c = conn.cursor()
    c.execute("SELECT repo_full_name FROM repos")
    return {row["repo_full_name"] for row in c.fetchall()}
