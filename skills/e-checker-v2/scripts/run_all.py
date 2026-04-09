"""
批量执行 .e-checker/ 目录下的所有检查脚本，并汇总为一份完整报告。

用法:
    python scripts/run_all.py [--checker-dir <path>]

默认检查目录为当前工作目录下的 .e-checker。
报告统一保存在 .e-checker/reports/ 目录下，文件名格式: YYYY-MM-DD-HH:MM:SS.txt
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime


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

    # 清理旧的统一报告（保留最近 N 个）
    MAX_KEEP_REPORTS = 10
    old_reports = sorted(reports_dir.glob("????-??-??-??:??:??.txt"))
    if len(old_reports) > MAX_KEEP_REPORTS:
        for old in old_reports[:-MAX_KEEP_REPORTS]:
            old.unlink()

    print(f"找到 {len(scripts)} 个检查脚本\n")
    report_parts = []
    results = []

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_parts.append(f"{'=' * 60}")
    report_parts.append(f"统一检查报告")
    report_parts.append(f"{'=' * 60}")
    report_parts.append(f"检查时间: {timestamp}")
    report_parts.append(f"检查脚本数: {len(scripts)}")
    report_parts.append(f"{'=' * 60}")
    report_parts.append("")

    for script in scripts:
        report_parts.append(f"{'=' * 60}")
        report_parts.append(f"检查脚本: {script.name}")
        report_parts.append(f"{'=' * 60}")

        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.stdout:
                report_parts.append(result.stdout)
            if result.stderr:
                report_parts.append(f"[STDERR] {result.stderr}")
            status = "成功" if result.returncode == 0 else "失败"
            results.append((script.name, status))
        except subprocess.TimeoutExpired:
            report_parts.append("[超时] 脚本执行超时 (300s)")
            results.append((script.name, "超时"))
        except Exception as e:
            report_parts.append(f"[异常] {e}")
            results.append((script.name, "异常"))

        report_parts.append("")

    # 汇总统计
    report_parts.append(f"{'=' * 60}")
    report_parts.append(f"执行汇总")
    report_parts.append(f"{'=' * 60}")
    passed = 0
    for name, status in results:
        report_parts.append(f"  {name}: {status}")
        if status == "成功":
            passed += 1
    report_parts.append(f"\n总计: {passed}/{len(results)} 脚本执行成功")
    report_parts.append(f"{'=' * 60}")

    # 输出到控制台
    full_report = "\n".join(report_parts)
    print(full_report)

    # 保存统一报告
    report_filename = datetime.now().strftime("%Y-%m-%d-%H:%M:%S.txt")
    report_path = reports_dir / report_filename
    report_path.write_text(full_report, encoding="utf-8")
    print(f"\n报告已保存至: {report_path}")


if __name__ == "__main__":
    checker_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--checker-dir" and i + 1 < len(sys.argv):
            checker_dir = Path(sys.argv[i + 1])
    run_all_checks(checker_dir)
