"""
新人日報コンディション見える化アプリ - 全パイプライン一括実行
Usage: python scripts/run_all.py
"""
import subprocess
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
PYTHON = sys.executable


def run_step(name, script):
    print(f"\n{'='*60}")
    print(f"  Step: {name}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(
        [PYTHON, os.path.join(SCRIPTS_DIR, script)],
        cwd=BASE_DIR,
        capture_output=False,
    )
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"  [FAILED] {name} (exit code {result.returncode}, {elapsed:.1f}s)")
        return False
    print(f"  [OK] {name} ({elapsed:.1f}s)")
    return True


def main():
    print("=" * 60)
    print("  新人日報コンディション見える化アプリ - Pipeline")
    print("=" * 60)

    steps = [
        ("1. Chatworkデータ取得", "fetch_reports.py"),
        ("2. 日報パース", "parse_reports.py"),
        ("3. AI分析", "analyze_reports.py"),
        ("4. ダッシュボード生成", "generate_dashboard.py"),
    ]

    for name, script in steps:
        if not run_step(name, script):
            print(f"\nPipeline stopped at: {name}")
            sys.exit(1)

    index_path = os.path.join(BASE_DIR, "index.html")
    print(f"\n{'='*60}")
    print(f"  Pipeline Complete!")
    print(f"  Dashboard: {index_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
