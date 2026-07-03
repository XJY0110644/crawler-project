"""测试: 数据库操作"""
import sys, os, sqlite3, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.github_db import init_db, save_repos, get_statistics, find_new_repos


def _make_conn():
    tmp = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    return conn, tmp


def test_init_db():
    conn, path = _make_conn()
    init_db(conn)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {r["name"] for r in tables}
    assert "repos" in names
    assert "trending_history" in names
    conn.close()
    os.unlink(path)
    print("  OK test_init_db")


def test_save_and_query():
    conn, path = _make_conn()
    init_db(conn)

    repos = [
        {
            "repo_full_name": "owner/repo1",
            "repo_name": "repo1",
            "repo_owner": "owner",
            "repo_url": "https://github.com/owner/repo1",
            "description": "Test repo",
            "language": "Python",
            "stars": 100,
            "forks": 10,
            "stars_today": 5,
            "built_by": ["user1"],
            "simhash": "0",
        }
    ]
    result = save_repos(conn, repos)
    assert result["new"] == 1
    assert result["updated"] == 0

    stats = get_statistics(conn)
    assert stats["total_repos"] == 1

    conn.close()
    os.unlink(path)
    print("  OK test_save_and_query")


def test_save_twice_upsert():
    conn, path = _make_conn()
    init_db(conn)

    repo = {
        "repo_full_name": "owner/repo1",
        "repo_name": "repo1",
        "repo_owner": "owner",
        "repo_url": "https://github.com/owner/repo1",
        "description": "Test repo",
        "language": "Python",
        "stars": 100,
        "forks": 10,
        "stars_today": 5,
        "built_by": [],
        "simhash": "0",
    }
    save_repos(conn, [repo])
    repo["stars"] = 200
    repo["simhash"] = "12345"
    result = save_repos(conn, [repo])

    # upsert 不会新增行，总数保持 1
    stats = get_statistics(conn)
    assert stats["total_repos"] == 1

    conn.close()
    os.unlink(path)
    print("  OK test_save_twice_upsert")


def test_find_new():
    conn, path = _make_conn()
    init_db(conn)
    save_repos(conn, [
        {
            "repo_full_name": "old/repo",
            "repo_name": "repo",
            "repo_owner": "old",
            "repo_url": "",
            "built_by": [],
            "simhash": "0",
        }
    ])
    new_names = find_new_repos(conn, {"old/repo", "new/repo1", "new/repo2"})
    assert "old/repo" not in new_names
    assert "new/repo1" in new_names
    assert len(new_names) == 2
    conn.close()
    os.unlink(path)
    print("  OK test_find_new")


if __name__ == "__main__":
    print("Database 测试:")
    test_init_db()
    test_save_and_query()
    test_save_twice_upsert()
    test_find_new()
    print("全部通过")
