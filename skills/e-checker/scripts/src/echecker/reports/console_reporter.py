"""控制台报告生成器"""

from pathlib import Path
from typing import Union

from echecker.types import ValidationReport, Severity
from echecker.reports.base import BaseReporter


class ConsoleReporter(BaseReporter):
    """控制台报告生成器"""

    def generate(self, report: ValidationReport, output_path: Union[str, Path] = None) -> str:
        """生成控制台报告"""
        lines = []

        # 标题
        lines.append("=" * 60)
        lines.append("Excel配置检查报告")
        lines.append("=" * 60)
        lines.append("")

        # 错误详情
        if report.errors:
            lines.append(f"❌ 发现 {len(report.errors)} 个问题:")
            lines.append("-" * 60)

            # 按Sheet分组
            errors_by_sheet = {}
            for error in report.errors:
                sheet = error.sheet_name or "未知Sheet"
                if sheet not in errors_by_sheet:
                    errors_by_sheet[sheet] = []
                errors_by_sheet[sheet].append(error)

            for sheet, errors in errors_by_sheet.items():
                lines.append(f"\n📄 {sheet}:")
                for error in errors:
                    severity_icon = "❌" if error.severity == Severity.ERROR else "⚠️"
                    lines.append(f"  {severity_icon} [{error.cell_ref}] {error.message}")
                    if error.expected is not None:
                        lines.append(f"     期望: {error.expected}")
                    if error.actual is not None:
                        lines.append(f"     实际: {error.actual}")
        else:
            lines.append("✅ 未发现任何问题!")

        lines.append("")
        lines.append("-" * 60)

        # 摘要
        summary = report.summary
        lines.append("📊 校验摘要:")
        lines.append(f"   总规则数: {summary.total_rules}")
        lines.append(f"   校验单元格: {summary.total_cells_checked}")
        lines.append(f"   ✅ 通过: {summary.passed_count}")
        lines.append(f"   ❌ 错误: {summary.error_count}")
        lines.append(f"   ⚠️ 警告: {summary.warning_count}")
        lines.append(f"   ⏱️ 耗时: {summary.duration_seconds:.2f}秒")

        lines.append("=" * 60)

        output = "\n".join(lines)
        print(output)
        return output
