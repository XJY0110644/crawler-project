"""测试: SimHash"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.simhash import compute_fingerprint, hamming_distance, is_duplicate, SimHashIndex


def test_fingerprint_stable():
    """相同文本产生相同指纹"""
    t = "GitHub Trending 今日热门"
    assert compute_fingerprint(t) == compute_fingerprint(t)
    print("  OK test_fingerprint_stable")


def test_hamming_same():
    """相同指纹汉明距离为 0"""
    fp = compute_fingerprint("测试文本")
    assert hamming_distance(fp, fp) == 0
    print("  OK test_hamming_same")


def test_hamming_different():
    """不同文本汉明距离较大"""
    fp1 = compute_fingerprint("Python 爬虫入门教程")
    fp2 = compute_fingerprint("宇宙大爆炸理论简介")
    assert hamming_distance(fp1, fp2) > 5
    print("  OK test_hamming_different")


def test_simhash_index():
    index = SimHashIndex(threshold=3)
    fp1 = compute_fingerprint("Python 爬虫入门教程")
    fp2 = compute_fingerprint("Python爬虫指南（入门篇）")
    fp3 = compute_fingerprint("Docker 容器化部署")

    assert not index.is_duplicate(fp1)
    index.add(fp1)
    assert not index.is_duplicate(fp3)
    index.add(fp3)

    ok = index.is_duplicate(fp2)
    print(f"  OK test_simhash_index: 相似文本判定重复={ok}")


def test_simhash_index_empty():
    index = SimHashIndex()
    assert not index.is_duplicate(0)
    assert not index.is_duplicate(12345)
    print("  OK test_simhash_index_empty")


if __name__ == "__main__":
    print("SimHash 测试:")
    test_fingerprint_stable()
    test_hamming_same()
    test_hamming_different()
    test_simhash_index()
    test_simhash_index_empty()
    print("全部通过")
