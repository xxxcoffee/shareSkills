"""
批量执行 .e-checker/ 目录下的所有检查脚本。

用法:
    python scripts/run_all.py [--checker-dir <path>]

默认检查目录为当前工作目录下的 .e-checker。
"""
import sys
import subprocess
from pathlib import Path


def run_all_checks(checker_dir: Path | None = None) -> None:
    if checker_dir is None:
        checker_dir = Path(".e-checker")

    if not checker_dir.exists():
        print(f"[错误] 检查目录不存在: {checker_dir}")
        return

    scripts = sorted(checker_dir.glob("*.py"))
    if not scripts:
        print(f"[提示] {checker_dir} 下没有找到 Python 脚本")
        return

    # 确保 reports 目录存在
    reports_dir = checker_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(f"找到 {len(scripts)} 个检查脚本\n")
    results = []

    for script in scripts:
        print(f"\n{'=' * 60}")
        print(f"执行: {script}")
        print(f"{'=' * 60}")
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=False,
                text=True,
            )
            status = "成功" if result.returncode == 0 else "失败"
            results.append((script.name, status))
        except Exception as e:
            print(f"[异常] {e}")
            results.append((script.name, "异常"))

    # 汇总
    print(f"\n{'=' * 60}")
    print("执行汇总")
    print(f"{'=' * 60}")
    for name, status in results:
        print(f"  {name}: {status}")
    passed = sum(1 for _, s in results if s == "成功")
    print(f"\n总计: {passed}/{len(results)} 脚本执行成功")


if __name__ == "__main__":
    checker_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--checker-dir" and i + 1 < len(sys.argv):
            checker_dir = Path(sys.argv[i + 1])
    run_all_checks(checker_dir)
