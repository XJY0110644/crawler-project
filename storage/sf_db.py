"""
存储层 — SQLite 数据库模型 + CRUD 操作

SQLite 是 Python 内置的轻量级数据库，无需额外安装。
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 数据库文件路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "segmentfault" / "segmentfault.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """获取数据库连接"""
    if db_path is None:
        db_path = str(DEFAULT_DB_PATH)

    # 确保 data 目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 支持按列名访问
    conn.execute("PRAGMA journal_mode=WAL")  # 写入性能优化
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection = None, db_path: str = None):
    """
    初始化数据库，创建表结构

    包含两张表：
    - articles: 文章主表
    - crawl_log: 爬取日志，用于增量更新去重
    """
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                article_id   INTEGER PRIMARY KEY,
                title        TEXT NOT NULL,
                url          TEXT NOT NULL,
                created_at   TEXT,
                timestamp    INTEGER DEFAULT 0,
                votes        INTEGER DEFAULT 0,
                comments     INTEGER DEFAULT 0,
                views        INTEGER DEFAULT 0,
                author_name  TEXT DEFAULT '',
                author_url   TEXT DEFAULT '',
                author_avatar TEXT DEFAULT '',
                blog_name    TEXT DEFAULT '',
                blog_url     TEXT DEFAULT '',
                cover        TEXT DEFAULT '',
                summary      TEXT DEFAULT '',
                crawled_at   TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(article_id)
            );

            CREATE INDEX IF NOT EXISTS idx_articles_timestamp
                ON articles(timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_articles_views
                ON articles(views DESC);

            -- 文章详情表：正文 + 标签 + 作者详情
            CREATE TABLE IF NOT EXISTS article_details (
                article_id       INTEGER PRIMARY KEY,
                content_html     TEXT DEFAULT '',
                content_text     TEXT DEFAULT '',
                tags             TEXT DEFAULT '',       -- JSON 数组 ["tag1","tag2"]
                author_avatar    TEXT DEFAULT '',
                author_excerpt   TEXT DEFAULT '',
                author_followers INTEGER DEFAULT 0,
                author_articles  INTEGER DEFAULT 0,
                author_rank      INTEGER DEFAULT 0,
                crawled_at       TEXT DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (article_id) REFERENCES articles(article_id)
            );

            CREATE TABLE IF NOT EXISTS crawl_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time   TEXT NOT NULL,                   -- 爬取开始时间
                end_time     TEXT,                            -- 爬取结束时间
                pages        INTEGER DEFAULT 0,               -- 爬取页数
                total_found  INTEGER DEFAULT 0,               -- 发现文章数
                new_added    INTEGER DEFAULT 0,               -- 新增文章数
                status       TEXT DEFAULT 'running'            -- running / completed / failed
            );
        """)
        conn.commit()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        if close_later:
            conn.close()


def save_articles(conn: sqlite3.Connection, articles: list[dict]) -> int:
    """
    批量保存文章，自动去重

    返回：新增的文章数量
    """
    if not articles:
        return 0

    new_count = 0
    cursor = conn.cursor()

    for article in articles:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (
                    article_id, title, url, created_at, timestamp,
                    votes, comments, views, author_name, author_url,
                    author_avatar, blog_name, blog_url, cover, summary
                ) VALUES (
                    :article_id, :title, :url, :created_at, :timestamp,
                    :votes, :comments, :views, :author_name, :author_url,
                    :author_avatar, :blog_name, :blog_url, :cover, :summary
                )
            """, article)

            if cursor.rowcount > 0:
                new_count += 1
        except Exception as e:
            logger.warning(f"保存文章 {article.get('article_id')} 失败: {e}")
            continue

    conn.commit()
    logger.info(f"批量保存完成: 共 {len(articles)} 条, 新增 {new_count} 条")
    return new_count


def save_article_detail(conn: sqlite3.Connection, detail: dict) -> bool:
    """
    保存文章详情（正文、标签、作者信息）

    返回：是否成功写入
    """
    if not detail or not detail.get("article_id"):
        logger.warning("保存详情失败: 缺少 article_id")
        return False

    import json
    try:
        conn.execute("""
            INSERT OR REPLACE INTO article_details (
                article_id, content_html, content_text, tags,
                author_avatar, author_excerpt, author_followers,
                author_articles, author_rank
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detail["article_id"],
            detail.get("content_html", ""),
            detail.get("content_text", ""),
            json.dumps(detail.get("tags", []), ensure_ascii=False),
            detail.get("author_avatar", ""),
            detail.get("author_excerpt", ""),
            detail.get("author_followers", 0),
            detail.get("author_articles", 0),
            detail.get("author_rank", 0),
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"保存文章详情 {detail.get('article_id')} 失败: {e}")
        return False


def start_crawl_log(conn: sqlite3.Connection) -> int:
    """记录爬取开始，返回 log_id"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO crawl_log (start_time, status)
        VALUES (datetime('now','localtime'), 'running')
    """)
    conn.commit()
    return cursor.lastrowid


def finish_crawl_log(conn: sqlite3.Connection, log_id: int,
                     pages: int, total_found: int, new_added: int,
                     status: str = "completed"):
    """记录爬取完成"""
    conn.execute("""
        UPDATE crawl_log SET
            end_time = datetime('now','localtime'),
            pages = ?,
            total_found = ?,
            new_added = ?,
            status = ?
        WHERE id = ?
    """, (pages, total_found, new_added, status, log_id))
    conn.commit()


def get_statistics(conn: sqlite3.Connection = None, db_path: str = None) -> dict:
    """
    获取数据统计信息

    返回：
    {
        "total_articles": 总数,
        "total_authors": 作者数,
        "max_views": 最高阅读数,
        "max_votes": 最高点赞数,
        "last_crawl_time": 最后爬取时间,
        "latest_article": 最新文章时间
    }
    """
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT author_name) FROM articles WHERE author_name != ''")
        authors = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(views) FROM articles")
        max_views = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(votes) FROM articles")
        max_votes = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(crawled_at) FROM articles")
        last_crawl = cursor.fetchone()[0] or "N/A"

        cursor.execute("SELECT MAX(created_at) FROM articles")
        latest_article = cursor.fetchone()[0] or "N/A"

        return {
            "total_articles": total,
            "total_authors": authors,
            "max_views": max_views,
            "max_votes": max_votes,
            "last_crawl_time": last_crawl,
            "latest_article": latest_article,
        }
    finally:
        if close_later:
            conn.close()


def query_articles(conn: sqlite3.Connection = None, db_path: str = None,
                   order_by: str = "timestamp", limit: int = 20,
                   desc: bool = True) -> list[dict]:
    """查询文章列表，返回字段含 votes/comments"""
    close_later = False
    if conn is None:
        conn = get_connection(db_path)
        close_later = True

    allowed_orders = ["timestamp", "views", "votes", "comments"]
    if order_by not in allowed_orders:
        order_by = "timestamp"

    direction = "DESC" if desc else "ASC"

    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT article_id, title, url, created_at, votes, comments, views,
                   author_name, blog_name, crawled_at
            FROM articles
            ORDER BY {order_by} {direction}
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        if close_later:
            conn.close()
