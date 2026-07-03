"""
知识库查询 Hermes 工具 — 供 /query 命令调用
"""
import os, sys
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from pathlib import Path
ROOT = Path("C:/Users/xjy11/Documents/crawler-project")
CHROMA_DIR = ROOT / "data" / "chroma"

import chromadb
from sentence_transformers import SentenceTransformer

# 全局模型
_MODEL = None
def get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    return _MODEL

def kb_query(question, source="all", top_k=5):
    """语义查询知识库"""
    if not CHROMA_DIR.exists():
        return [{"error": "知识库不存在，请先运行 build_knowledge_base.py"}]
    
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    sources = []
    if source in ("all", "github"): sources.append("github_trending")
    if source in ("all", "segmentfault"): sources.append("segmentfault")
    
    model = get_model()
    vec = model.encode(question, normalize_embeddings=True).tolist()
    
    results = []
    for name in sources:
        try:
            collection = client.get_collection(name)
        except:
            continue
        qr = collection.query(query_embeddings=[vec], n_results=top_k)
        if not qr.get("ids") or not qr["ids"][0]:
            continue
        for i in range(len(qr["ids"][0])):
            meta = qr["metadatas"][0][i] or {}
            dist = qr["distances"][0][i] if qr.get("distances") else 0
            results.append({
                "score": round(1.0 - dist, 4),
                "metadata": meta,
                "source": "GitHub" if name == "github_trending" else "SegmentFault",
            })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

def format_results(results):
    """美化输出"""
    lines = []
    if not results:
        return "没有找到匹配结果"
    
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        header = f"{i}. [{r['source']}] (匹配度: {r['score']})"
        lines.append(header)
        if meta.get("repo"):
            lines.append(f"   仓库: {meta['repo']}")
            lines.append(f"   语言: {meta.get('language', '')}  |  星数: {meta.get('stars', '')} (今日+{meta.get('stars_today', 0)})")
            lines.append(f"   链接: {meta.get('url', '')}")
        if meta.get("title"):
            lines.append(f"   标题: {meta['title']}")
            lines.append(f"   作者: {meta.get('author', '')}")
            lines.append(f"   链接: {meta.get('url', '')}")
        if meta.get("description"):
            lines.append(f"   描述: {meta['description'][:100]}")
        lines.append("")
    
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python kb_tool.py <查询内容> [--source github|segmentfault|all] [--top-k N]")
        sys.exit(1)
    
    question = sys.argv[1]
    source = "all"
    top_k = 5
    
    for i, a in enumerate(sys.argv[2:]):
        if a == "--source" and i+1 < len(sys.argv[2:]): source = sys.argv[2:][i+1]
        if a == "--top-k" and i+1 < len(sys.argv[2:]): top_k = int(sys.argv[2:][i+1])
    
    r = kb_query(question, source, top_k)
    print(format_results(r))
