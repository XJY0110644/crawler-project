"""
布隆过滤器
快速判断一个元素是否已见过。
只用一次，用完即弃。

原理：
  一个 m 位的 bit 数组 + k 个哈希函数。
  添加元素时，用 k 个哈希函数算出 k 个位置，对应 bit 置 1。
  查询元素时，检查 k 个位置是否全部为 1。
  如果有任意一位为 0，元素一定不在集合中。
  如果全部为 1，元素可能在集合中（有误判率）。

特点：
  - 占用内存极小（m 位 ≈ m/8 字节）
  - 查询/插入都是 O(k)
  - 不能删除元素
  - 有误判率（False Positive），没有漏判（False Negative）

本实现：
  - 用 Python 的 bytearray 做 bit 数组
  - 用内置的 hash() + 随机种子模拟 k 个哈希函数
  - 默认误判率 ~1%
"""

import math
import random


class BloomFilter:
    """布隆过滤器"""

    def __init__(self, capacity: int, error_rate: float = 0.01):
        """
        参数：
            capacity: 预期要存储的元素数量
            error_rate: 期望的误判率（0~1 之间，越小越精确但越费内存）
        """
        if capacity <= 0:
            raise ValueError("capacity 必须大于 0")
        if error_rate <= 0 or error_rate >= 1:
            raise ValueError("error_rate 必须在 0~1 之间")

        self.capacity = capacity
        self.error_rate = error_rate

        # 计算最优的 bit 数组大小 m 和哈希函数数量 k
        # 公式推导见：https://en.wikipedia.org/wiki/Bloom_filter
        self.bit_count = self._optimal_bit_count(capacity, error_rate)
        self.hash_count = self._optimal_hash_count(capacity, self.bit_count)

        # bit 数组。Python 的 bytearray 每个元素是 1 字节（8 位）
        self._bits = bytearray(math.ceil(self.bit_count / 8))
        self._inserted = 0  # 已插入元素计数

        # k 个哈希函数的随机种子（固定下来，保证一致性）
        random.seed(42)
        self._seeds = [random.randint(1, 2 ** 31) for _ in range(self.hash_count)]

    # ─── 内部 ───────────────────────────────────────────

    @staticmethod
    def _optimal_bit_count(n: int, p: float) -> int:
        """计算最优 bit 数组大小 m"""
        m = -n * math.log(p) / (math.log(2) ** 2)
        return max(1, math.ceil(m))

    @staticmethod
    def _optimal_hash_count(n: int, m: int) -> int:
        """计算最优哈希函数数量 k"""
        k = m / n * math.log(2)
        return max(1, math.ceil(k))

    def _hash(self, item: str, seed: int) -> int:
        """
        一个带种子的哈希函数

        用 Python 内置 hash()，但每次运行进程不同会变化。
        所以组合 hash() + 固定种子 + 取模，保证一致性。
        """
        # 用 hashlib 做稳定哈希（进程间一致）
        import hashlib
        h = hashlib.md5((str(seed) + item).encode("utf-8"))
        return int(h.hexdigest()[:8], 16) % self.bit_count

    def _get_bit(self, pos: int) -> bool:
        """读取第 pos 位的值"""
        byte_idx = pos // 8
        bit_idx = pos % 8
        return bool(self._bits[byte_idx] & (1 << bit_idx))

    def _set_bit(self, pos: int):
        """将第 pos 位置为 1"""
        byte_idx = pos // 8
        bit_idx = pos % 8
        self._bits[byte_idx] |= (1 << bit_idx)

    # ─── 公开接口 ───────────────────────────────────────

    def add(self, item: str):
        """
        添加一个元素

        item 会被自动转成字符串处理。
        """
        for seed in self._seeds:
            pos = self._hash(item, seed)
            self._set_bit(pos)
        self._inserted += 1

    def contains(self, item: str) -> bool:
        """
        判断元素是否可能已存在

        返回 True：  元素可能在集合中（有误判概率）
        返回 False： 元素一定不在集合中
        """
        for seed in self._seeds:
            pos = self._hash(item, seed)
            if not self._get_bit(pos):
                return False
        return True

    def __contains__(self, item: str) -> bool:
        return self.contains(item)

    def clear(self):
        """清空所有 bit（重置过滤器）"""
        self._bits = bytearray(math.ceil(self.bit_count / 8))
        self._inserted = 0

    @property
    def inserted_count(self) -> int:
        """已插入的元素数量"""
        return self._inserted

    @property
    def memory_usage(self) -> int:
        """占用内存，单位字节"""
        return len(self._bits)

    def __repr__(self) -> str:
        return (
            f"BloomFilter(capacity={self.capacity}, "
            f"error_rate={self.error_rate:.2%}, "
            f"bits={self.bit_count:,}, "
            f"hash_funcs={self.hash_count}, "
            f"inserted={self._inserted}, "
            f"memory={self.memory_usage:,} bytes)"
        )


# ─── 测试 ──────────────────────────────────────────────

def _test():
    """跑几个基本测试验证正确性"""
    bf = BloomFilter(capacity=1000, error_rate=0.01)
    print(bf)
    print()

    # 1. 插入并验证存在
    items = ["apple", "banana", "cherry", "date", "elderberry"]
    for item in items:
        bf.add(item)
    print(f"插入 {len(items)} 个元素")
    print(f"已插入计数: {bf.inserted_count}")

    # 2. 检查存在的元素
    print("\n检查已存在的元素:")
    for item in items:
        assert item in bf, f"{item} 应该存在但没有找到"
        print(f"  ✓ {item}")

    # 3. 检查不存在的元素
    print("\n检查不存在的元素:")
    not_in = ["fig", "grape", "honeydew", "kiwi", "lemon"]
    false_positives = 0
    for item in not_in:
        if item in bf:
            false_positives += 1
            print(f"  ⚠ {item} 误判为存在（False Positive）")
        else:
            print(f"  ✓ {item} 不存在（正确）")
    print(f"\n误判率: {false_positives}/{len(not_in)}")

    # 4. 清空
    bf.clear()
    print(f"\n清空后插入计数: {bf.inserted_count}")
    for item in items:
        assert item not in bf, f"{item} 不应该存在"
    print("清空后全部正确")

    # 5. 统计误判率（大量数据）
    print("\n大容量测试（10000 个元素，期望误判率 1%）...")
    bf2 = BloomFilter(capacity=10000, error_rate=0.01)
    for i in range(10000):
        bf2.add(f"item_{i}")
    false_count = 0
    for i in range(10000, 20000):
        if bf2.contains(f"item_{i}"):
            false_count += 1
    print(f"  实际误判率: {false_count/10000:.4%} ({false_count}/10000)")
    print(f"  内存占用: {bf2.memory_usage:,} bytes ({bf2.memory_usage/1024:.1f} KB)")
    print(f"  哈希函数数: {bf2.hash_count}")
    print()

    print("全部测试通过 ✓")


if __name__ == "__main__":
    _test()
