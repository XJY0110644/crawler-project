"""
知识库查询脚本 — Hermes Skill 调用的后端

用法：
  python scripts/query_knowledge.py "查询内容" [--source github|segmentfault|all] [--top-k 5]
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import chromadb

CHROMA_DIR = ROOT / "data" / "chroma"

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


def query(question: str, source: str = "all", top_k: int = 5) -> list[dict]:
    """查询知识库，返回匹配结果列表"""
    chroma_dir = str(CHROMA_DIR)
    if not Path(chroma_dir).exists():
        return [{"error": f"知识库目录不存在: {chroma_dir}\n请先运行 `python scripts/build_knowledge_base.py` 构建知识库"}]

    client = chromadb.PersistentClient(path=chroma_dir)

    collection_names = []
    if source in ("all", "github"):
        collection_names.append("github_trending")
    if source in ("all", "segmentfault"):
        collection_names.append("segmentfault")

    embedding = get_embedding(question)
    results = []

    for name in collection_names:
        try:
            collection = client.get_collection(name)
        except Exception:
            continue

        try:
            qr = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
            )
        except Exception as e:
            results.append({"error": f"查询 {name} 失败: {e}"})
            continue

        if not qr.get("ids") or not qr["ids"][0]:
            continue

        for i in range(len(qr["ids"][0])):
            doc_id = qr["ids"][0][i]
            metadata = qr["metadatas"][0][i] if qr.get("metadatas") else {}
            distance = qr["distances"][0][i] if qr.get("distances") else 0
            document = qr["documents"][0][i] if qr.get("documents") else ""

            results.append({
                "id": doc_id,
                "score": round(1.0 - distance, 4),
                "metadata": metadata,
                "document": document,
                "collection": name,
            })

    # 按分数排序
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]


def main():
    parser = argparse.ArgumentParser(description="查询知识库")
    parser.add_argument("question", help="查询内容")
    parser.add_argument("--source", choices=["github", "segmentfault", "all"],
                        default="all", help="查询来源")
    parser.add_argument("--top-k", type=int, default=5, help="返回结果数")
    args = parser.parse_args()

    results = query(args.question, args.source, args.top_k)

    if not results:
        print("没有找到匹配结果")
        return

    for i, r in enumerate(results, 1):
        if "error" in r:
            print(f"[{i}] 错误: {r['error']}")
            continue

        meta = r["metadata"]
        source_name = "GitHub" if r["collection"] == "github_trending" else "SegmentFault"
        score = r.get("score", 0)

        print(f"[{i}] {source_name} (相似度: {score})")
        if meta.get("repo"):
            print(f"    仓库: {meta['repo']}")
            print(f"    链接: {meta.get('url', '')}")
            print(f"    语言: {meta.get('language', '')}")
            print(f"    星数: {meta.get('stars', '')} (今日 +{meta.get('stars_today', 0)})")
        if meta.get("title"):
            print(f"    标题: {meta['title']}")
            print(f"    链接: {meta.get('url', '')}")
            print(f"    作者: {meta.get('author', '')}")
        print(f"    评分/热度: {meta.get('votes', meta.get('stars', 'N/A'))}")
        print()

    print(f"--- 共 {len(results)} 条结果 ---")


if __name__ == "__main__":
    main()
