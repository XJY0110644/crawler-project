"""测试: 布隆过滤器"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bloom_filter import BloomFilter


def test_init():
    bf = BloomFilter(capacity=100)
    assert bf.capacity == 100
    assert bf.hash_count > 0
    assert bf.bit_count > 0
    assert bf.inserted_count == 0
    print("  OK test_init")


def test_add_and_contains():
    bf = BloomFilter(capacity=100)
    items = ["a", "b", "c"]
    for item in items:
        bf.add(item)
    for item in items:
        assert item in bf
    print("  OK test_add_and_contains")


def test_not_contains():
    bf = BloomFilter(capacity=100)
    bf.add("existing")
    assert "not_existing" not in bf
    print("  OK test_not_contains")


def test_clear():
    bf = BloomFilter(capacity=100)
    bf.add("item")
    bf.clear()
    assert bf.inserted_count == 0
    assert "item" not in bf
    print("  OK test_clear")


def test_false_positive_rate():
    """验证误判率不超过预期值的 2 倍"""
    bf = BloomFilter(capacity=5000, error_rate=0.01)
    for i in range(5000):
        bf.add(f"item_{i}")
    false_positives = 0
    trials = 5000
    for i in range(5000, 10000):
        if bf.contains(f"item_{i}"):
            false_positives += 1
    rate = false_positives / trials
    assert rate < 0.02, f"误判率 {rate:.4%} 超过阈值 2%"
    print(f"  OK test_false_positive_rate: 实际 {rate:.4%}")


if __name__ == "__main__":
    print("BloomFilter 测试:")
    test_init()
    test_add_and_contains()
    test_not_contains()
    test_clear()
    test_false_positive_rate()
    print("全部通过")
