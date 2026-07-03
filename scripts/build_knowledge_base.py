"""
知识库构建脚本 — 从 SQLite 爬虫数据写入 ChromaDB

用法：
  python scripts/build_knowledge_base.py                    # 全量构建
  python scripts/build_knowledge_base.py --force             # 清空重建
  python scripts/build_knowledge_base.py --source github     # 只构建 GitHub
  python scripts/build_knowledge_base.py --source segmentfault  # 只构建 SF
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import chromadb

# ── 路径 ───────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CHROMA_DIR = ROOT / "data" / "chroma"

# SQLite 数据库路径
GH_DB = DATA_DIR / "github" / "github_trending.db"
SF_DB = DATA_DIR / "segmentfault" / "segmentfault.db"


# ── Embedding 模型（全局共享单例）─────────────
_EMBEDDING_MODEL = None

def get_embedding(text: str) -> list[float]:
    """使用 BAAI/bge-small-zh-v1.5 语义 embedding 模型"""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        import os
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    vec = _EMBEDDING_MODEL.encode(text, normalize_embeddings=True)
    return vec.tolist()


def build_github_knowledge(client: chromadb.ClientAPI):
    """
    从 GitHub Trending 数据库构建知识库。
    如果新的 chromadb API 不支持 get_or_create_collection，
    就降级到常规的 create_collection / get_collection。
    """
    # 1. 建或获取集合
    try:
        collection = client.get_or_create_collection(
            name="github_trending",
            metadata={"description": "GitHub Trending 仓库信息"},
        )
    except AttributeError:
        # 旧版本 chromadb
        try:
            collection = client.get_collection("github_trending")
        except Exception:
            collection = client.create_collection(
                name="github_trending",
                metadata={"description": "GitHub Trending 仓库信息"},
            )

    db_path = str(GH_DB)
    if not Path(db_path).exists():
        print(f"  [跳过] GitHub 数据库不存在: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT repo_full_name, repo_url, description, language,
               stars, forks, stars_today, built_by, created_at
        FROM repos
        ORDER BY stars DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  [跳过] GitHub 数据库为空")
        return 0

    documents = []
    metadatas = []
    ids = []

    for row in rows:
        r = dict(row)
        built_by_list = json.loads(r.get("built_by", "[]"))

        # 组合成搜索文本
        text = f"""仓库: {r['repo_full_name']}
描述: {r.get('description', '')}
语言: {r.get('language', '')}
星数: {r['stars']}
Fork: {r['forks']}
今日新增: {r['stars_today']}
构建者: {', '.join(built_by_list)}
抓取时间: {r.get('created_at', '')}"""

        documents.append(text)
        metadatas.append({
            "repo": r["repo_full_name"],
            "url": r["repo_url"],
            "language": r.get("language", ""),
            "stars": r["stars"],
            "forks": r["forks"],
            "stars_today": r["stars_today"],
            "source": "github",
        })
        ids.append(f"github_{r['repo_full_name'].replace('/', '_')}")

    # 批量写入（一次最多 100 条）
    batch_size = 100
    total = len(documents)
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        try:
            collection.add(
                documents=documents[i:end],
                embeddings=[get_embedding(d) for d in documents[i:end]],
                metadatas=metadatas[i:end],
                ids=ids[i:end],
            )
        except Exception as e:
            print(f"  [错误] 写入批次 {i}-{end} 失败: {e}")

    print(f"  GitHub 知识库: {total} 条写入完成")
    return total


def build_segmentfault_knowledge(client: chromadb.ClientAPI):
    """
    从 SegmentFault 数据库构建知识库。
    """
    try:
        collection = client.get_or_create_collection(
            name="segmentfault",
            metadata={"description": "SegmentFault 技术文章"},
        )
    except AttributeError:
        try:
            collection = client.get_collection("segmentfault")
        except Exception:
            collection = client.create_collection(
                name="segmentfault",
                metadata={"description": "SegmentFault 技术文章"},
            )

    db_path = str(SF_DB)
    if not Path(db_path).exists():
        print(f"  [跳过] SegmentFault 数据库不存在: {db_path}")
        return 0

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.article_id, a.title, a.url, a.summary, a.votes, a.comments, a.views,
               a.author_name, a.created_at,
               d.content_text, d.tags
        FROM articles a
        LEFT JOIN article_details d ON a.article_id = d.article_id
        ORDER BY a.votes DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("  [跳过] SegmentFault 数据库为空")
        return 0

    documents = []
    metadatas = []
    ids = []

    for row in rows:
        r = dict(row)
        tags_list = json.loads(r.get("tags", "[]")) if r.get("tags") else []

        # 取正文前 500 字
        content = (r.get("content_text") or "")[:500]

        text = f"""标题: {r['title']}
作者: {r.get('author_name', '')}
标签: {', '.join(tags_list)}
摘要: {r.get('summary', '')}
正文: {content}
点赞: {r['votes']}  评论: {r['comments']}  阅读: {r['views']}
发布时间: {r.get('created_at', '')}
链接: {r['url']}"""

        documents.append(text)
        metadatas.append({
            "title": r["title"],
            "url": r["url"],
            "author": r.get("author_name", ""),
            "votes": r["votes"],
            "source": "segmentfault",
            "tags": ",".join(tags_list),
        })
        ids.append(f"sf_{r['article_id']}")

    batch_size = 100
    total = len(documents)
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        try:
            collection.add(
                documents=documents[i:end],
                embeddings=[get_embedding(d) for d in documents[i:end]],
                metadatas=metadatas[i:end],
                ids=ids[i:end],
            )
        except Exception as e:
            print(f"  [错误] 写入批次 {i}-{end} 失败: {e}")

    print(f"  SegmentFault 知识库: {total} 条写入完成")
    return total


def main():
    parser = argparse.ArgumentParser(description="构建 Hermes 知识库")
    parser.add_argument("--force", action="store_true", help="清空重建")
    parser.add_argument("--source", choices=["github", "segmentfault"],
                        help="只构建指定来源")
    args = parser.parse_args()

    # 初始化 ChromaDB (持久化模式)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if args.force:
        print("清空旧知识库...")
        for name in ["github_trending", "segmentfault"]:
            try:
                client.delete_collection(name)
                print(f"  已删除: {name}")
            except Exception:
                pass

    print("开始构建知识库...")
    total = 0

    if args.source in (None, "github"):
        print("[GitHub Trending]")
        total += build_github_knowledge(client)

    if args.source in (None, "segmentfault"):
        print("[SegmentFault]")
        total += build_segmentfault_knowledge(client)

    print(f"\n完成！共写入 {total} 条到 ChromaDB ({CHROMA_DIR})")


if __name__ == "__main__":
    main()
