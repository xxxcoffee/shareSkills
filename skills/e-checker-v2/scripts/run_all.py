"""
批量执行 .e-checker/ 目录下的所有检查脚本，并汇总为一份完整报告。

用法:
    python scripts/run_all.py [--checker-dir <path>]

默认检查目录为当前工作目录下的 .e-checker。
报告统一保存在 .e-checker/reports/ 目录下，文件名格式: YYYY-MM-DD-HH:MM:SS.txt
"""
import sys
import json
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

    # 收集所有检查结果
    all_results = []  # list of (script_name, json_results_list_or_error)

    for script in scripts:
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    json_data = json.loads(result.stdout.strip())
                    all_results.append((script.name, json_data, None))
                except json.JSONDecodeError:
                    all_results.append((script.name, None, f"JSON 解析失败:\n{result.stdout}"))
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                all_results.append((script.name, None, error_msg or "无输出"))
        except subprocess.TimeoutExpired:
            all_results.append((script.name, None, "脚本执行超时 (300s)"))
        except Exception as e:
            all_results.append((script.name, None, str(e)))

    # 按模块分组
    modules = {}  # module_name -> list of (script_name, check_result)
    for script_name, json_data, error in all_results:
        if error:
            # 脚本执行失败，归入 "未分类"
            if "未分类" not in modules:
                modules["未分类"] = []
            modules["未分类"].append((script_name, {"status": "error", "error": error}))
        elif json_data:
            for item in json_data:
                module = item.get("module", "未分类")
                if module not in modules:
                    modules[module] = []
                modules[module].append((script_name, item))

    # 生成报告
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []

    # 报告头
    lines.append("=" * 60)
    lines.append("检查报告")
    lines.append("=" * 60)
    lines.append(f"检查时间: {timestamp}")
    lines.append(f"检查脚本: {len(scripts)} 个")
    lines.append(f"检查模块: {len(modules)} 个")
    lines.append("=" * 60)
    lines.append("")

    # 统计
    total_checks = 0
    total_pass = 0
    total_fail = 0

    # 按模块输出
    for module_name, checks in modules.items():
        lines.append(f"## {module_name}")
        lines.append("-" * 60)

        # 收集该模块涉及的所有文件
        all_files = set()
        for _, item in checks:
            if "files" in item:
                all_files.update(item["files"])

        if all_files:
            lines.append(f"涉及文件: {', '.join(sorted(all_files))}")
            lines.append("")

        for _, item in checks:
            if item.get("status") == "error":
                lines.append(f"  [{item.get('check', '未知检查')}]")
                lines.append(f"    状态: 执行错误")
                lines.append(f"    原因: {item.get('error', '未知错误')}")
                lines.append("")
                total_checks += 1
                total_fail += 1
                continue

            check_name = item.get("check", "未知检查")
            status = item.get("status", "unknown")
            files = item.get("files", [])
            details = item.get("details", [])

            total_checks += 1
            if status == "pass":
                total_pass += 1
                lines.append(f"  [{check_name}]")
                lines.append(f"    状态: 通过")
                lines.append("")
            else:
                total_fail += 1
                lines.append(f"  [{check_name}]")
                lines.append(f"    状态: 失败")
                if files:
                    lines.append(f"    涉及文件: {', '.join(files)}")
                if details:
                    lines.append(f"    失败详情:")
                    for d in details:
                        loc_parts = []
                        if d.get("file"):
                            loc_parts.append(d["file"])
                        if d.get("sheet"):
                            loc_parts.append(d["sheet"])
                        if d.get("row"):
                            loc_parts.append(f"行{d['row']}")
                        if d.get("column"):
                            loc_parts.append(d["column"])
                        loc = " -> ".join(loc_parts) if loc_parts else "未知位置"

                        lines.append(f"      - {loc}")
                        if d.get("reason"):
                            lines.append(f"        原因: {d['reason']}")
                        if d.get("actual") is not None:
                            lines.append(f"        实际值: {d['actual']}")
                        if d.get("expected") is not None:
                            lines.append(f"        期望: {d['expected']}")
                lines.append("")

    # 汇总
    lines.append("=" * 60)
    lines.append("汇总")
    lines.append("=" * 60)
    lines.append(f"  总检查数: {total_checks}")
    lines.append(f"  通过: {total_pass}")
    lines.append(f"  失败: {total_fail}")
    if total_checks > 0:
        pass_rate = total_pass / total_checks * 100
        lines.append(f"  通过率: {pass_rate:.1f}%")
    lines.append("=" * 60)

    full_report = "\n".join(lines)
    print(full_report)

    # 保存报告
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
