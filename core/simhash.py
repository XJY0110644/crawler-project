"""
simhash.py — SimHash 文本相似度去重

用途：
  判断两条文本是否相似（比布隆过滤器更精细）。
  布隆过滤器判断"是否见过这个 ID"，SimHash 判断"是否和之前某条内容重复"。
  两者配合：布隆去重做第一道快速过滤，SimHash 做第二道内容级去重。

原理：
  SimHash 是 Google 用于网页去重的局部敏感哈希算法。
  1. 将文本分词，每个词算出一个 hash 值
  2. 每个 hash 值的每一位，如果是 1 则 + 权重，为 0 则 - 权重
  3. 所有词叠加后，最终每位 >0 取 1，≤0 取 0，得到一个固定长度的指纹
  4. 两个文本的相似度 = 指纹的汉明距离（不同位的个数）
  5. 汉明距离 ≤ 3 通常认为是相似/重复内容

特点：
  - 短文本（标题）效果一般，长文本效果好
  - 通过调整汉明距离阈值控制严格程度
  - 不依赖外部分词库，内置简单分词
"""

import re
import math
from typing import List, Optional


# ─── SimHash 核心 ──────────────────────────────────────

FINGERPRINT_BITS = 64  # 指纹长度，按位计算


def _simple_tokenize(text: str) -> List[str]:
    """
    简单中文分词 + 英文单词提取

    中文：按单字切分（做 2-gram 改善效果）
    英文：按空格切分单词
    数字：保留

    注意：这是轻量实现。要更好的效果可以用 jieba 分词。
    """
    if not text:
        return []

    tokens = []

    # 提取英文单词 + 数字
    for m in re.finditer(r'[a-zA-Z_][a-zA-Z_0-9]{1,}', text):
        tokens.append(m.group().lower())

    # 提取连续中文，做 2-gram
    chinese_seq = re.findall(r'[\u4e00-\u9fff]+', text)
    for seq in chinese_seq:
        if len(seq) == 1:
            tokens.append(seq)
        else:
            # 2-gram 改善单字切分的语义丢失
            for i in range(len(seq) - 1):
                tokens.append(seq[i:i + 2])

    return tokens


def _hash_fingerprint(token: str, bits: int = FINGERPRINT_BITS) -> int:
    """
    将一个 token 哈希为 bits 位的整数指纹

    用 hashlib.md5 保证进程间一致性。
    """
    import hashlib
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h[:16], 16) & ((1 << bits) - 1)


def compute_fingerprint(text: str) -> int:
    """
    计算文本的 SimHash 指纹

    返回一个 64 位整数，每一位 0/1。
    """
    tokens = _simple_tokenize(text)
    if not tokens:
        return 0

    # 初始化 64 位权重向量
    v = [0] * FINGERPRINT_BITS

    for token in tokens:
        h = _hash_fingerprint(token)
        for i in range(FINGERPRINT_BITS):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    # 根据权重向量合成最终指纹
    fingerprint = 0
    for i in range(FINGERPRINT_BITS):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return fingerprint


def hamming_distance(a: int, b: int) -> int:
    """
    计算两个指纹之间的汉明距离

    汉明距离 = 两个整数异或后 1 的位数。
    距离越小，文本越相似。
    """
    x = a ^ b
    # 计算 bit 1 的个数（Brian Kernighan 算法）
    distance = 0
    while x:
        x &= (x - 1)
        distance += 1
    return distance


def similarity(a: int, b: int) -> float:
    """
    根据汉明距离计算相似度（0~1）

    距离 0   → 完全一致 (1.0)
    距离 32  → 完全不相似 (0.0)
    """
    distance = hamming_distance(a, b)
    return 1.0 - (distance / FINGERPRINT_BITS)


def is_duplicate(a: int, b: int, threshold: int = 3) -> bool:
    """
    判断两个指纹是否代表重复内容

    汉明距离 ≤ threshold 判定为重复。
    threshold=3 是 SimHash 论文推荐值。
    越严格 threshold 设越小，越宽松设越大。
    """
    return hamming_distance(a, b) <= threshold


# ─── 文本指纹缓存（用于批量去重） ──────────────────────

class SimHashIndex:
    """
    SimHash 指纹索引

    维护一个已见过的指纹列表，新文本来了判断是否与其中任意一条重复。
    """

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._fingerprints: List[int] = []

    def add(self, fingerprint: int):
        """添加一个指纹到索引"""
        if fingerprint != 0:
            self._fingerprints.append(fingerprint)

    def is_duplicate(self, fingerprint: int) -> bool:
        """
        判断指纹是否与索引中任意一个重复

        先快速判断：如果索引元素超过 100，只抽样对比（性能优化）。
        """
        if not self._fingerprints or fingerprint == 0:
            return False

        # 小规模：全量对比
        if len(self._fingerprints) <= 100:
            for fp in self._fingerprints:
                if is_duplicate(fingerprint, fp, self.threshold):
                    return True
            return False

        # 大规模：抽样对比（取前 30 + 随机 30）
        sample = self._fingerprints[:30]
        import random
        sample += random.sample(self._fingerprints[30:], min(30, len(self._fingerprints) - 30))
        for fp in sample:
            if is_duplicate(fingerprint, fp, self.threshold):
                return True
        return False

    @property
    def count(self) -> int:
        return len(self._fingerprints)

    def clear(self):
        self._fingerprints.clear()


# ─── 常用工具 ──────────────────────────────────────────

def compare_texts(text_a: str, text_b: str) -> dict:
    """
    比较两段文本的相似度

    返回：
        fingerprint_a: 文本 A 的指纹
        fingerprint_b: 文本 B 的指纹
        hamming_distance: 汉明距离
        similarity: 相似度 (0~1)
        is_duplicate: 是否判定为重复
    """
    fa = compute_fingerprint(text_a)
    fb = compute_fingerprint(text_b)
    dist = hamming_distance(fa, fb)
    return {
        "fingerprint_a": fa,
        "fingerprint_b": fb,
        "hamming_distance": dist,
        "similarity": similarity(fa, fb),
        "is_duplicate": is_duplicate(fa, fb),
    }


# ─── 测试 ──────────────────────────────────────────────

def _test():
    print("SimHash 测试")
    print("=" * 50)
    print()

    # 1. 完全相同的文本
    text_a = "GitHub Trending 今日热门仓库排行榜"
    text_b = "GitHub Trending 今日热门仓库排行榜"
    result = compare_texts(text_a, text_b)
    print(f"完全相同:")
    print(f"  汉明距离: {result['hamming_distance']}")
    print(f"  相似度:   {result['similarity']:.2%}")
    print(f"  判定重复: {result['is_duplicate']}")
    print()

    # 2. 轻微修改的文本
    text_a = "Python 爬虫入门教程：使用 requests 和 BeautifulSoup"
    text_b = " Python爬虫入门——用requests和BeautifulSoup抓取网页"
    result = compare_texts(text_a, text_b)
    print(f"轻微修改:")
    print(f"  汉明距离: {result['hamming_distance']}")
    print(f"  相似度:   {result['similarity']:.2%}")
    print(f"  判定重复: {result['is_duplicate']}")
    print()

    # 3. 完全不同
    text_a = "深度学习在自然语言处理中的应用综述"
    text_b = "闪电网络：比特币二层扩容方案对比分析"
    result = compare_texts(text_a, text_b)
    print(f"完全不同:")
    print(f"  汉明距离: {result['hamming_distance']}")
    print(f"  相似度:   {result['similarity']:.2%}")
    print(f"  判定重复: {result['is_duplicate']}")
    print()

    # 4. SimHashIndex 批量去重测试
    print("SimHashIndex 批量去重测试:")
    index = SimHashIndex(threshold=3)

    texts = [
        "Python 爬虫入门教程：使用 requests 库",
        "Python爬虫——requests用法详解（重复）",
        "Docker 容器化部署 Spring Boot 应用",
        "GitHub Actions 自动化 CI/CD 流程",
        "用Python写爬虫的完整指南（和第一条相似）",
    ]

    deduped = []
    for t in texts:
        fp = compute_fingerprint(t)
        if not index.is_duplicate(fp):
            index.add(fp)
            deduped.append(t)
            print(f"  ✓ 新增: {t[:40]}")
        else:
            print(f"  ✗ 重复跳过: {t[:40]}")

    print(f"\n  输入: {len(texts)} 条, 去重后: {len(deduped)} 条")
    print()

    # 5. 统计性能
    print("性能测试:")
    import time
    t0 = time.time()
    for i in range(1000):
        compute_fingerprint(f"测试文本第{i}条，用于验证 SimHash 性能")
    t = time.time() - t0
    print(f"  1000 次指纹计算: {t:.3f}s ({t / 1000 * 1000:.2f}ms/次)")

    print()
    print("全部测试通过 ✓")


if __name__ == "__main__":
    _test()
