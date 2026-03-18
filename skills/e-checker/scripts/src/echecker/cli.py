"""命令行接口"""

import sys
from pathlib import Path
from typing import Optional

import click

from echecker.core.engine_v2 import validate_excel
from echecker.rules.v2_parser import V2RuleParser
from echecker.reports.console_reporter import ConsoleReporter
from echecker.reports.excel_reporter import ExcelReporter
from echecker.reports.html_reporter import HtmlReporter


@click.group()
@click.version_option(version="2.0.0", prog_name="echecker")
def main():
    """Excel配置检查器 - 基于YAML规则的多维度校验工具"""
    pass


@main.command()
@click.option("--excel", "-e", type=click.Path(exists=True), required=True, help="Excel文件路径")
@click.option("--rules", "-r", type=click.Path(exists=True), required=True, help="规则文件路径")
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
@click.option("--format", "-f", "output_format", type=click.Choice(["console", "excel", "html"]),
              default="console", help="输出格式")
@click.option("--strict", is_flag=True, help="严格模式，警告也视为错误")
def check(excel, rules, output, output_format, strict):
    """执行Excel配置检查"""

    target_excel = Path(excel)
    rules_file = Path(rules)

    click.echo(f"🔍 正在检查: {target_excel}")
    click.echo(f"📋 规则文件: {rules_file}")

    # 执行校验
    try:
        report = validate_excel(target_excel, rules_file)
    except Exception as e:
        click.echo(f"❌ 校验执行失败: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    click.echo(f"📊 总规则数: {report.summary.total_rules}")
    click.echo(f"❌ 错误数: {report.summary.error_count}")
    click.echo(f"⚠️ 警告数: {report.summary.warning_count}")

    # 生成报告
    if output_format == "console":
        reporter = ConsoleReporter()
        reporter.generate(report)
    elif output_format == "excel":
        output_path = output or "validation_report.xlsx"
        reporter = ExcelReporter(target_excel)
        path = reporter.generate(report, output_path)
        click.echo(f"✅ Excel报告已生成: {path}")
    elif output_format == "html":
        output_path = output or "validation_report.html"
        reporter = HtmlReporter()
        path = reporter.generate(report, output_path)
        click.echo(f"✅ HTML报告已生成: {path}")

    # 退出码
    if report.has_errors() or (strict and report.warnings):
        sys.exit(1)
    sys.exit(0)


@main.command()
@click.option("--excel", "-e", type=click.Path(exists=True), required=True, help="Excel文件路径")
@click.option("--rules", "-r", type=click.Path(exists=True), required=True, help="规则文件路径")
def validate(excel, rules):
    """执行验证（validate.py脚本的CLI版本）"""
    target_excel = Path(excel)
    rules_file = Path(rules)

    click.echo(f"📁 Excel文件: {target_excel}")
    click.echo(f"📋 规则文件: {rules_file}")
    click.echo()

    try:
        report = validate_excel(target_excel, rules_file)
    except Exception as e:
        click.echo(f"❌ 验证失败: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 打印报告
    click.echo("=" * 60)
    click.echo("验证报告")
    click.echo("=" * 60)
    click.echo(f"总规则数: {report.summary.total_rules}")
    click.echo(f"错误数: {report.summary.error_count}")
    click.echo(f"警告数: {report.summary.warning_count}")
    click.echo(f"耗时: {report.summary.duration_seconds:.3f}秒")
    click.echo()

    if report.errors:
        click.echo("-" * 60)
        click.echo(f"错误详情 ({len(report.errors)}个):")
        click.echo("-" * 60)

        # 按错误类型分组
        errors_by_type = {}
        for error in report.errors:
            etype = error.error_type.name
            if etype not in errors_by_type:
                errors_by_type[etype] = []
            errors_by_type[etype].append(error)

        for etype, errors in errors_by_type.items():
            click.echo(f"\n[{etype}] ({len(errors)}个)")
            for error in errors:
                click.echo(f"  📍 {error.cell_ref}")
                click.echo(f"     消息: {error.message}")
        click.echo()

    if not report.has_errors():
        click.echo("✅ 所有验证通过！")
        sys.exit(0)
    else:
        click.echo(f"❌ 发现 {report.summary.error_count} 个错误")
        sys.exit(1)


def main_entry():
    """入口点"""
    main()


if __name__ == "__main__":
    main()
