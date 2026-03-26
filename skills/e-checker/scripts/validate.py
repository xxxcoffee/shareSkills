#!/usr/bin/env python3
"""Excel配置验证脚本 (V3 Pipeline版本)

使用示例:
    # 使用指定规则文件验证
    python validate.py rules.yaml

    # 显示详细信息（包括期望/实际值）
    python validate.py rules.yaml -v

    # 显示所有支持的操作符
    python validate.py --list-operators

支持的Pipeline操作符:
    SOURCE:
    • source        - 从指定列获取源值
    • as            - 为值设置别名（变量存储）
    • use           - 使用变量作为输入

    TRANSFORM:
    • split         - 字符串分割
    • extract       - 复合值提取（如从"id:count"提取id）
    • map           - 对列表元素执行映射操作
    • unique        - 列表去重
    • flatten       - 嵌套列表扁平化
    • union         - 多个列表合并（去重）
    • intersect     - 多个列表交集

    LOOKUP:
    • lookup        - 在外部数据源中查找值
    • where         - 根据条件过滤数据
    • get           - 获取指定列的值

    AGGREGATE:
    • collect       - 跨行收集数据

    VALIDATE:
    • sequential    - 验证ID按顺序累加
    • previous      - 验证当前行等于上一行指定列
    • attribute_match - 验证关联元素属性匹配
    • sheet_exists  - 验证Sheet是否存在
    • exists        - 验证值是否存在
    • exists_in     - 验证值是否存在于集合中
    • all_exist_in  - 验证所有值都存在于目标列
    • range_check   - 验证数值范围
    • validate      - 通用值验证
    • eq            - 验证值等于预期值
    • in            - 验证值在指定集合中
    • regex_match   - 正则表达式验证

变量引用:
    @value          - 当前单元格原始值
    @row.X          - 同行第X列的值（X为列字母）
    @var_name       - 通过"as"存储的变量值

YAML规则文件格式:
    version: "3.0"
    refs:
      data_source:
        file: "data.xlsx"
        sheet: "Sheet1"
        columns:
          id: "A"
          name: "B"
    rules:
      - target: "file.xlsx:Sheet1.A1:C10"  # 文件:Sheet.范围 格式
        id: "rule1"
        validations:
          - pipeline:
              - split: "|"
              - lookup: "data_source[id].name"
              - eq: 1

Target格式说明:
    - "file.xlsx:Sheet1.A1:C10"  # 完整格式：包含.xlsx扩展名
    - "file:Sheet1.A1:C10"       # 简写格式：自动补全.xlsx
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# 确保可以导入echecker
sys.path.insert(0, str(Path(__file__).parent / "src"))

from echecker.core.engine_v3 import validate_excel, V3ValidationEngine
from echecker.operators.registry import OperatorRegistry
from echecker.operators.base import OperatorType
from echecker.rules.v3_parser import V3RuleParser, V3Rule
from echecker.types import ValidationReport


def parse_target(target: str) -> Tuple[str, str]:
    """解析 target 为 (file, sheet_range)

    支持格式:
    - "passNew.xlsx:PassNewList.H5:*" -> ("passNew.xlsx", "PassNewList.H5:*")
    - "passNew:PassNewList.H5:*" -> ("passNew.xlsx", "PassNewList.H5:*")

    旧格式(无文件前缀)给出清晰错误提示

    Args:
        target: target字符串

    Returns:
        Tuple[str, str]: (文件路径, sheet_range)

    Raises:
        ValueError: 格式错误时抛出
    """
    if ":" not in target:
        raise ValueError(
            f"target格式错误，应为 'file.xlsx:Sheet.range': {target}\n"
            f"提示: 旧格式需要添加文件前缀，例如 'passNew.xlsx:{target}'"
        )

    file_part, sheet_range = target.split(":", 1)

    # 检测旧格式：file_part 看起来像 Sheet.Column 格式（例如 PassNewList.H5）
    # 旧格式特征：包含点号，且点号后是大写字母+数字
    import re
    if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\.[A-Z]\d', file_part):
        raise ValueError(
            f"target格式错误，检测到旧格式（缺少文件前缀）: {target}\n"
            f"应为 'file.xlsx:{target}' 或 'file:{target}'"
        )

    # 自动补全 .xlsx
    if not file_part.endswith('.xlsx'):
        file_part += '.xlsx'

    return file_part, sheet_range


def group_rules_by_file(rules: List[V3Rule]) -> Dict[str, List[V3Rule]]:
    """按文件分组规则，优化执行

    Args:
        rules: 规则列表

    Returns:
        Dict[str, List[V3Rule]]: 按文件路径分组的规则字典
    """
    groups = defaultdict(list)
    for rule in rules:
        file_path, _ = parse_target(rule.target)
        groups[file_path].append(rule)
    return dict(groups)


def print_report(report, verbose=False):
    """打印验证报告"""
    print("=" * 70)
    print("📊 验证报告")
    print("=" * 70)
    print(f"  总规则数: {report.summary.total_rules}")
    print(f"  错误数: {report.summary.error_count}")
    print(f"  警告数: {report.summary.warning_count}")
    print(f"  耗时: {report.summary.duration_seconds:.3f}秒")
    print()

    if report.errors:
        print("-" * 70)
        print(f"❌ 错误详情 ({len(report.errors)}个):")
        print("-" * 70)

        # 按规则ID分组
        errors_by_rule = {}
        for error in report.errors:
            rule_id = error.rule_id or "未知规则"
            if rule_id not in errors_by_rule:
                errors_by_rule[rule_id] = []
            errors_by_rule[rule_id].append(error)

        # 按规则ID排序输出
        for rule_id in sorted(errors_by_rule.keys()):
            errors = errors_by_rule[rule_id]
            print(f"\n【规则: {rule_id}】 ({len(errors)}个错误)")

            # 按Sheet和单元格排序
            sorted_errors = sorted(errors, key=lambda e: (e.sheet_name or "", e.cell_ref or ""))

            for error in sorted_errors:
                # 解析单元格位置
                cell = error.cell_ref or "未知位置"
                sheet = error.sheet_name or ""

                # 显示错误位置和消息
                print(f"  📍 {cell}")
                print(f"     错误: {error.message}")

                if verbose:
                    if error.expected is not None:
                        print(f"     期望: {format_value(error.expected)}")
                    if error.actual is not None:
                        print(f"     实际: {format_value(error.actual)}")
                print()

    if report.warnings:
        print("-" * 70)
        print(f"⚠️  警告详情 ({len(report.warnings)}个):")
        print("-" * 70)

        # 按规则ID分组
        warnings_by_rule = {}
        for warning in report.warnings:
            rule_id = warning.rule_id or "未知规则"
            if rule_id not in warnings_by_rule:
                warnings_by_rule[rule_id] = []
            warnings_by_rule[rule_id].append(warning)

        for rule_id in sorted(warnings_by_rule.keys()):
            warnings = warnings_by_rule[rule_id]
            print(f"\n【规则: {rule_id}】 ({len(warnings)}个警告)")
            for warning in warnings:
                cell = warning.cell_ref or "未知位置"
                print(f"  📍 {cell}: {warning.message}")
        print()

    print("=" * 70)
    if not report.has_errors():
        print("✅ 所有验证通过！")
    else:
        print(f"❌ 发现 {report.summary.error_count} 个错误，请查看上方详情")
    print("=" * 70)


def format_value(value, max_length=80):
    """格式化值显示"""
    if value is None:
        return "(空)"

    # 处理列表
    if isinstance(value, list):
        items = [str(v) for v in value]
        text = "[" + ", ".join(items) + "]"
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        return text

    # 处理字符串
    text = str(value)
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    return text


def list_operators():
    """列出所有可用的Pipeline操作符"""
    print("=" * 60)
    print("可用的Pipeline操作符 (V3)")
    print("=" * 60)
    print()

    operators = OperatorRegistry.list_all()
    if not operators:
        print("未找到操作符")
        return

    # 按类型分组
    by_type = {}
    for info in operators:
        op_type = info.operator_type.name if info.operator_type else "OTHER"
        if op_type not in by_type:
            by_type[op_type] = []
        by_type[op_type].append(info)

    type_order = ["SOURCE", "TRANSFORM", "LOOKUP", "COLLECTION", "AGGREGATE", "VALIDATE", "OTHER"]

    for op_type in type_order:
        if op_type not in by_type:
            continue
        items = by_type[op_type]
        print(f"\n【{op_type}】")
        for info in items:
            print(f"  • {info.name} (v{info.version})")
            print(f"    {info.description}")
    print()


def validate_single_file(
    file_path: Path,
    rules: List[V3Rule],
    parser: V3RuleParser,
    ruleset_base_path: Path
) -> ValidationReport:
    """验证单个文件的一组规则

    Args:
        file_path: Excel文件路径
        rules: 该文件的规则列表
        parser: 规则解析器
        ruleset_base_path: 规则文件所在目录（用于解析相对路径）

    Returns:
        ValidationReport: 验证报告
    """
    print(f"📁 验证文件: {file_path.absolute()}")
    print(f"   规则数: {len(rules)}")
    print()

    # 检查文件是否存在
    if not file_path.exists():
        # 尝试基于规则文件目录解析相对路径
        if not file_path.is_absolute():
            file_path = ruleset_base_path / file_path

    if not file_path.exists():
        # 创建错误报告
        from echecker.types import ValidationReport, ValidationError, ErrorType, Severity, ReportSummary
        error = ValidationError(
            rule_id="file_check",
            cell_ref="",
            error_type=ErrorType.CONFIG_ERROR,
            severity=Severity.ERROR,
            message=f"文件不存在: {file_path}",
            sheet_name=""
        )
        return ValidationReport(
            errors=[error],
            summary=ReportSummary(
                total_rules=len(rules),
                error_count=1,
                warning_count=0
            )
        )

    # 创建新的规则集，只包含当前文件的规则
    # 需要修改target为旧格式（去掉文件前缀）以便引擎处理
    from dataclasses import replace

    modified_rules = []
    for rule in rules:
        _, sheet_range = parse_target(rule.target)
        # 创建修改后的规则，target只包含sheet_range
        modified_rule = replace(rule, target=sheet_range)
        modified_rules.append(modified_rule)

    # 创建临时规则集
    temp_ruleset = replace(
        parser._ruleset,
        rules=modified_rules
    )

    # 执行验证
    engine = V3ValidationEngine()
    return engine.validate(file_path, temp_ruleset)


def merge_reports(reports: List[ValidationReport]) -> ValidationReport:
    """合并多个验证报告

    Args:
        reports: 验证报告列表

    Returns:
        ValidationReport: 合并后的报告
    """
    all_errors = []
    all_warnings = []
    total_rules = 0
    total_error_count = 0
    total_warning_count = 0
    total_duration = 0.0

    for report in reports:
        all_errors.extend(report.errors)
        all_warnings.extend(report.warnings)
        total_rules += report.summary.total_rules
        total_error_count += report.summary.error_count
        total_warning_count += report.summary.warning_count
        total_duration += report.summary.duration_seconds

    from echecker.types import ReportSummary
    summary = ReportSummary(
        total_rules=total_rules,
        error_count=total_error_count,
        warning_count=total_warning_count,
        duration_seconds=total_duration
    )

    return ValidationReport(
        errors=all_errors,
        warnings=all_warnings,
        summary=summary
    )


def main():
    parser = argparse.ArgumentParser(
        description="Excel配置验证工具 (V3 Pipeline版本)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python validate.py rules.yaml              # 使用规则文件验证
  python validate.py rules.yaml -v           # 显示详细信息
  python validate.py --list-operators        # 查看所有操作符

Target格式:
  规则文件中的target字段应使用以下格式:
    "file.xlsx:Sheet.range"   # 完整格式，包含.xlsx扩展名
    "file:Sheet.range"        # 简写格式，自动补全.xlsx

  示例:
    - "passNew.xlsx:PassNewList.H5:*"  # 验证passNew.xlsx的PassNewList表H5列
    - "elementPassNew.xlsx:element(PassNew).A5:*"  # 验证外部数据源

常用Pipeline组合:
  # 简单条件验证
  - split: "|"
  - lookup: "ref[id].level"
  - eq: 1

  # 派生集合验证
  - source: "@row.H"
  - split: "|"
  - lookup: "ref[id].series"
  - as: "series_h"
  - union: ["@series_h", "@series_i"]
  - unique
  - eq: "@expected"

  # 顺序ID验证
  - collect: "ids"
  - sequential:
      prefix: "eventpass"
      start_from: 1
        """
    )

    parser.add_argument(
        "rules_file",
        nargs="?",
        help="规则文件路径 (YAML格式)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息（包括期望/实际值）"
    )

    parser.add_argument(
        "--list-operators",
        action="store_true",
        help="列出所有可用的Pipeline操作符"
    )

    args = parser.parse_args()

    if args.list_operators:
        list_operators()
        return 0

    if not args.rules_file:
        print("❌ 错误: 请提供规则文件路径")
        print("用法: python validate.py <rules_file>")
        print("      python validate.py --list-operators")
        return 1

    rules_path = Path(args.rules_file)

    # 检查规则文件是否存在
    if not rules_path.exists():
        print(f"❌ 错误: 规则文件不存在: {rules_path}")
        return 1

    print(f"📋 规则文件: {rules_path.absolute()}")
    print()

    try:
        # 解析规则文件
        parser = V3RuleParser()
        ruleset = parser.parse_file(rules_path)

        # 按文件分组规则
        rules_by_file = group_rules_by_file(ruleset.rules)

        if not rules_by_file:
            print("⚠️ 警告: 没有找到需要验证的规则")
            return 0

        print(f"📊 发现 {len(rules_by_file)} 个文件需要验证:")
        for file_path, rules in rules_by_file.items():
            print(f"  - {file_path}: {len(rules)} 条规则")
        print()

        # 逐个文件执行验证
        reports = []
        ruleset_base_path = rules_path.parent

        for file_path, rules in rules_by_file.items():
            report = validate_single_file(
                Path(file_path),
                rules,
                parser,
                ruleset_base_path
            )
            reports.append(report)

        # 合并报告
        merged_report = merge_reports(reports)

        # 打印报告
        print_report(merged_report, verbose=args.verbose)

        return 0 if not merged_report.has_errors() else 1

    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
