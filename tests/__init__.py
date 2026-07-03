"""
运行所有测试
用法: python tests/run_all.py
"""
import sys, os, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

tests = [
    ("tests/test_bloom_filter.py", "BloomFilter"),
    ("tests/test_simhash.py", "SimHash"),
    ("tests/test_db.py", "Database"),
]

passed = 0
failed = 0

for test_file, name in tests:
    print(f"\n{'='*40}")
    print(f"  {name}")
    print(f"{'='*40}")
    r = subprocess.run(
        [PYTHON, str(ROOT / test_file)],
        capture_output=True, text=True, timeout=30, cwd=str(ROOT),
    )
    out = r.stdout.strip()
    err = r.stderr.strip()
    if out:
        for line in out.splitlines():
            print(f"  {line}")
    if err:
        print(f"  [STDERR] {err[-200:]}")
    if r.returncode == 0:
        passed += 1
    else:
        failed += 1

print(f"\n{'='*40}")
print(f"  结果: {passed} 通过, {failed} 失败")
if failed:
    sys.exit(1)


def main():
    # 直接运行本文件时触发上面的逻辑
    pass


if __name__ == "__main__":
    main()
