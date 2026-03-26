"""V3校验引擎

使用pipeline操作符语法的校验引擎。
"""

import time
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable

from echecker.types import ValidationReport, ValidationError, ErrorType, Severity
from echecker.rules.v3_parser import V3RuleSet, V3Rule, V3ValidationConfig, PipelineValidation, PipelineStep
from echecker.core.context import RowContext
from echecker.excel.external_data import ExternalDataManager, ExternalDataSource
from echecker.excel.provider import ExcelProvider
from echecker.excel.cell_ref import CellRef, CellRange
from echecker.expression.template import TemplateExpr
from echecker.expression.context import EvalContext


# 辅助函数：解析配置值，支持 TemplateExpr 表达式求值
def _resolve_config_value(
    value: Any,
    row_context: Any,
    pipeline_vars: Dict,
    cell_value: Any = None
) -> Any:
    """解析配置值，支持字符串引用和 TemplateExpr 表达式

    Args:
        value: 配置值（可能是字符串、TemplateExpr 或其他类型）
        row_context: 行执行上下文，用于获取行数据
        pipeline_vars: Pipeline 变量字典
        cell_value: 当前单元格值（用于 @value 引用）

    Returns:
        Any: 解析后的值
    """
    # 如果是 TemplateExpr，进行表达式求值
    if isinstance(value, TemplateExpr):
        row_data = row_context._row_data if row_context else {}
        context = EvalContext(
            cell_value=cell_value,
            row_data=row_data,
            variables=pipeline_vars
        )
        return value.evaluate(context)

    # 如果是字符串，按原有逻辑处理
    if not isinstance(value, str):
        return value

    if value.startswith('@row.'):
        if row_context:
            return row_context.get_row_value(value[5:])
        return None
    elif value.startswith('@'):
        var_name = value[1:]
        return pipeline_vars.get(var_name, value)

    return value


class OperatorResult:
    """操作符执行结果"""

    def __init__(
        self,
        value: Any,
        is_valid: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict] = None,
        expected: Any = None,
        actual: Any = None
    ):
        self.value = value
        self.is_valid = is_valid
        self.error_message = error_message
        self.metadata = metadata or {}
        self.expected = expected
        self.actual = actual


class Operator:
    """操作符基类"""

    name: str = ""
    description: str = ""

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        """执行操作符

        Args:
            input_value: 输入值
            config: 操作符配置
            context: 执行上下文（包含external_data, row_data等）

        Returns:
            OperatorResult: 执行结果
        """
        raise NotImplementedError()


class SplitOperator(Operator):
    """拆分操作符

    将字符串按分隔符分割成列表。如果输入是列表，对每个元素分割后扁平化。
    """

    name = "split"
    description = "按分隔符拆分字符串为列表"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        separator = config.get('value', config.get('by', '|'))

        if input_value is None:
            return OperatorResult(value=[])

        # 如果是字符串，直接分割
        if isinstance(input_value, str):
            s = input_value.strip()
            if not s:
                return OperatorResult(value=[])
            result = [x.strip() for x in s.split(separator) if x.strip()]
            return OperatorResult(value=result)

        # 如果是列表，对每个元素分割后扁平化
        if isinstance(input_value, list):
            result = []
            for item in input_value:
                if isinstance(item, str):
                    if item.strip():
                        result.extend(x.strip() for x in item.split(separator) if x.strip())
                elif item is not None:
                    result.append(str(item))
            return OperatorResult(value=result)

        # 其他类型转为字符串处理
        return OperatorResult(value=[str(input_value)])


class CountOperator(Operator):
    """计数操作符 - 将列表或字符串转换为元素个数

    示例:
        - count                    # 计算列表长度
        - count: "|"              # 按 | 分割字符串后计数
    """

    name = "count"
    description = "计算列表元素个数或字符串分割后的数量"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        delimiter = config.get('value') or config.get('delimiter') or '|'

        if input_value is None:
            return OperatorResult(value=0)

        # 如果是字符串，按分隔符分割后计数
        if isinstance(input_value, str):
            if not input_value.strip():
                return OperatorResult(value=0)
            parts = input_value.split(delimiter)
            # 过滤空字符串
            count = len([p for p in parts if p.strip()])
            return OperatorResult(value=count)

        # 如果是列表，返回长度
        if isinstance(input_value, list):
            return OperatorResult(value=len(input_value))

        # 其他类型视为单元素
        return OperatorResult(value=1)


class ExtractOperator(Operator):
    """提取操作符 - 从复合值中提取部分

    支持两种模式：
    1. 从字符串按分隔符提取："a:b:c" + extract 1 -> "b"
    2. 从列表按索引提取：["a", "b", "c"] + extract 1 -> "b"
    """

    name = "extract"
    description = "按分隔符或索引提取部分值"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        # 支持格式: ":0" 或 {by: ":", index: 0} 或 {index: 0}
        if isinstance(config.get('value'), str) and ':' in str(config.get('value')):
            parts = config['value'].split(':')
            separator = parts[0] if parts[0] else ':'
            index = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        else:
            separator = config.get('by', config.get('separator', config.get('delimiter')))
            index = config.get('index', config.get('value', 0))
            if isinstance(index, str):
                index = int(index)

        if isinstance(input_value, list):
            # 如果没有指定分隔符(by/separator)，直接按索引取列表元素
            if separator is None:
                if 0 <= index < len(input_value):
                    return OperatorResult(value=input_value[index])
                else:
                    return OperatorResult(value=None)
            # 有分隔符时，对每个元素分割后提取
            result = []
            for item in input_value:
                if item is None:
                    continue
                parts = str(item).split(separator)
                if 0 <= index < len(parts):
                    result.append(parts[index].strip())
            return OperatorResult(value=result)
        else:
            if input_value is None:
                return OperatorResult(value=None)
            parts = str(input_value).split(separator)
            if 0 <= index < len(parts):
                return OperatorResult(value=parts[index].strip())
            return OperatorResult(value=input_value)


class LookupOperator(Operator):
    """查找操作符"""

    name = "lookup"
    description = "在外部数据源中查找值"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        external_data = context.get('external_data')
        if not external_data:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message="外部数据管理器未配置"
            )

        # 解析lookup语法: "ref_source[match_column].return_column"
        lookup_str = config.get('value', '')
        if isinstance(lookup_str, dict):
            # 对象格式: {ref: "...", match: "...", return: "..."}
            ref_source = lookup_str.get('ref')
            match_column = lookup_str.get('match', 'id')
            return_column = lookup_str.get('return')
        else:
            # 字符串格式: "ref_source[match_column].return_column"
            ref_source, match_column, return_column = self._parse_lookup_string(str(lookup_str))

        if not ref_source:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message="lookup操作符需要指定ref_source"
            )

        def lookup_single(value):
            record = external_data.lookup(ref_source, match_column, value)
            if record is None:
                return None
            if return_column:
                return record.get(return_column)
            return record

        if isinstance(input_value, list):
            result = [lookup_single(v) for v in input_value if v is not None]
            result = [r for r in result if r is not None]
            return OperatorResult(value=result)
        else:
            result = lookup_single(input_value)
            return OperatorResult(value=result)

    def _parse_lookup_string(self, lookup_str: str) -> tuple:
        """解析lookup字符串

        格式: "ref_source[match_column].return_column"
        或: "ref_source.return_column" (默认match_column为id)
        """
        if '[' in lookup_str:
            # 有match_column
            match = re.match(r'^(\w+)\[(\w+)\](?:\.(\w+))?$', lookup_str)
            if match:
                ref_source = match.group(1)
                match_column = match.group(2)
                return_column = match.group(3)
                return ref_source, match_column, return_column
        else:
            # 无match_column，默认id
            if '.' in lookup_str:
                parts = lookup_str.split('.')
                return parts[0], 'id', parts[1]
            else:
                return lookup_str, 'id', None

        return lookup_str, 'id', None


class ExistsOperator(Operator):
    """存在性验证操作符"""

    name = "exists"
    description = "验证值是否存在"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        expected = config.get('value', True)

        if isinstance(input_value, list):
            exists = len(input_value) > 0 and all(v is not None for v in input_value)
        else:
            exists = input_value is not None and str(input_value).strip() != ''

        is_valid = exists == expected
        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"存在性验证失败: 期望{expected}, 实际{exists}"
        )


class ExistsInOperator(Operator):
    """存在于外部数据源操作符

    验证值是否存在于外部数据源的指定列中。
    空值（None 或空列表）被视为有效（无需验证）。
    """

    name = "exists_in"
    description = "验证值是否存在于外部数据源"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        external_data = context.get('external_data')
        if not external_data:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message="外部数据管理器未配置"
            )

        # 解析语法: "ref_source.column"
        lookup_str = str(config.get('value', ''))
        if '.' in lookup_str:
            ref_source, column = lookup_str.split('.', 1)
        else:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message=f"exists_in语法错误，应为 'ref_source.column': {lookup_str}"
            )

        # 空值视为有效（没有值需要验证）
        if input_value is None:
            return OperatorResult(value=input_value, is_valid=True)

        if isinstance(input_value, list):
            # 过滤空值后检查
            non_empty_values = [v for v in input_value if v is not None and str(v).strip() != '']
            if not non_empty_values:
                return OperatorResult(value=input_value, is_valid=True)

            all_exist = all(external_data.exists(ref_source, column, v) for v in non_empty_values)
        else:
            # 字符串空值检查
            if isinstance(input_value, str) and input_value.strip() == '':
                return OperatorResult(value=input_value, is_valid=True)
            all_exist = external_data.exists(ref_source, column, input_value)

        return OperatorResult(
            value=input_value,
            is_valid=all_exist,
            error_message=None if all_exist else f"值不存在于 {lookup_str}"
        )


class WhereOperator(Operator):
    """条件过滤操作符"""

    name = "where"
    description = "根据条件过滤值"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        external_data = context.get('external_data')
        if not external_data:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message="外部数据管理器未配置"
            )

        # 解析条件语法: "ref_source[match_column].condition_column == value"
        condition_str = str(config.get('value', ''))

        # 简化实现：支持 "ref_source[match_column].column == value" 格式
        match = re.match(r'^(\w+)\[(\w+)\]\.(\w+)\s*==?\s*(.+)$', condition_str)
        if not match:
            return OperatorResult(
                value=input_value,
                is_valid=True,
                error_message=None  # 条件格式不支持时，默认通过
            )

        ref_source = match.group(1)
        match_column = match.group(2)
        cond_column = match.group(3)
        cond_value = match.group(4).strip().strip('"\'')

        # 尝试转换条件值为数值
        try:
            cond_value = int(cond_value)
        except ValueError:
            try:
                cond_value = float(cond_value)
            except ValueError:
                pass

        def check_condition(value):
            record = external_data.lookup(ref_source, match_column, value)
            if record is None:
                return False
            actual_value = record.get(cond_column)
            return actual_value == cond_value

        if isinstance(input_value, list):
            result = [v for v in input_value if check_condition(v)]
            return OperatorResult(value=result)
        else:
            is_valid = check_condition(input_value)
            return OperatorResult(
                value=input_value if is_valid else None,
                is_valid=True,  # where操作符本身不报错，只是过滤
                error_message=None
            )


class AllExistInOperator(Operator):
    """所有元素都存在操作符"""

    name = "all_exist_in"
    description = "验证所有元素都存在于目标列"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        external_data = context.get('external_data')

        # 解析目标: 可能是 "@row.X" 或 "ref_source.column"
        target_str = str(config.get('value', ''))

        if target_str.startswith('@row.'):
            # 同行列引用
            if not plugin_context:
                return OperatorResult(
                    value=None,
                    is_valid=False,
                    error_message="RowContext未配置"
                )
            col = target_str[5:]
            target_value = plugin_context.get_row_value(col)
        elif '.' in target_str:
            # 外部数据源引用
            if not external_data:
                return OperatorResult(
                    value=None,
                    is_valid=False,
                    error_message="外部数据管理器未配置"
                )
            ref_source, column = target_str.split('.', 1)
            target_values = external_data.get_values(ref_source, column, unique=True)
            target_value = target_values
        else:
            target_value = target_str

        # 解析目标值为集合
        if isinstance(target_value, str):
            target_set = set(target_value.split('|'))
        elif isinstance(target_value, list):
            target_set = set(str(v) for v in target_value)
        else:
            target_set = set([str(target_value)])

        # 检查输入值
        if not isinstance(input_value, list):
            input_value = [input_value]

        all_exist = all(str(v) in target_set for v in input_value if v is not None)

        return OperatorResult(
            value=input_value,
            is_valid=all_exist,
            error_message=None if all_exist else f"不是所有元素都存在于目标中"
        )


class UnionOperator(Operator):
    """并集操作符

    支持两种用法:
    1. union: "@row.H" - 与输入值取并集
    2. union: ["@var1", "@var2"] - 合并多个变量
    """

    name = "union"
    description = "与另一个集合取并集"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        union_ref = config.get('value', [])
        result_set: set = set()

        # 解析值引用
        def resolve_value(ref: Any) -> Any:
            if not isinstance(ref, str):
                return ref
            if ref.startswith('@row.'):
                if plugin_context:
                    return plugin_context.get_row_value(ref[5:])
                return None
            elif ref.startswith('@'):
                var_name = ref[1:]
                return pipeline_vars.get(var_name, ref)
            return ref

        # 如果配置是列表，合并所有元素
        if isinstance(union_ref, list):
            for ref in union_ref:
                value = resolve_value(ref)
                if isinstance(value, list):
                    result_set.update(str(v) for v in value if v is not None)
                elif isinstance(value, str):
                    result_set.update(v.strip() for v in value.split('|') if v.strip())
                elif value is not None:
                    result_set.add(str(value))
        else:
            # 单个值引用
            value = resolve_value(union_ref)
            if isinstance(value, list):
                result_set.update(str(v) for v in value if v is not None)
            elif isinstance(value, str):
                result_set.update(v.strip() for v in value.split('|') if v.strip())
            elif value is not None:
                result_set.add(str(value))

        # 添加输入值到并集
        if isinstance(input_value, list):
            result_set.update(str(v) for v in input_value if v is not None)
        elif isinstance(input_value, str):
            result_set.update(v.strip() for v in input_value.split('|') if v.strip())
        elif input_value is not None:
            result_set.add(str(input_value))

        return OperatorResult(value=list(result_set))


class UniqueOperator(Operator):
    """去重操作符

    移除列表中的重复项，保持顺序。
    """

    name = "unique"
    description = "去重"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        if input_value is None:
            return OperatorResult(value=[])

        if not isinstance(input_value, list):
            # 非列表转为单元素列表
            return OperatorResult(value=[input_value])

        seen = set()
        result = []
        for item in input_value:
            if item is not None:
                key = str(item)
                if key not in seen:
                    seen.add(key)
                    result.append(item)

        return OperatorResult(value=result)


class EqOperator(Operator):
    """等于验证操作符"""

    name = "eq"
    description = "验证等于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 处理列表比较 - 将列表转换为集合进行比较（忽略顺序）
        input_set = self._to_set(input_value)
        expected_set = self._to_set(expected)

        is_valid = input_set == expected_set

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值不匹配",
            expected=expected,
            actual=input_value
        )

    def _to_set(self, value: Any) -> set:
        """将值转换为字符串集合进行比较"""
        if value is None:
            return set()
        if isinstance(value, list):
            return set(str(v).strip() for v in value if v is not None)
        if isinstance(value, str):
            # 如果是 | 分隔的字符串，分割后转换
            return set(v.strip() for v in value.split('|') if v.strip())
        return set([str(value)])


class CountEqOperator(Operator):
    """数量相等验证操作符"""

    name = "count_eq"
    description = "验证数量相等"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')

        expected_ref = config.get('value')
        if isinstance(expected_ref, str) and expected_ref.startswith('@row.'):
            if plugin_context:
                expected_value = plugin_context.get_row_value(expected_ref[5:])
            else:
                expected_value = None
        else:
            expected_value = expected_ref

        input_count = len(input_value) if isinstance(input_value, list) else (1 if input_value else 0)

        if isinstance(expected_value, str):
            expected_count = len(expected_value.split('|'))
        elif isinstance(expected_value, list):
            expected_count = len(expected_value)
        else:
            expected_count = 1 if expected_value else 0

        is_valid = input_count == expected_count

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"数量不匹配: 期望 {expected_count}, 实际 {input_count}"
        )


class SumOperator(Operator):
    """求和操作符

    将列表中的数字求和。如果元素是字符串，尝试转换为数字。

    示例:
        - sum                    # 对列表求和
    """

    name = "sum"
    description = "将列表中的数字求和"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        if input_value is None:
            return OperatorResult(value=0)

        if isinstance(input_value, list):
            total = 0
            for item in input_value:
                if item is None:
                    continue
                try:
                    # 尝试转换为数字
                    num = float(str(item))
                    total += num
                except (ValueError, TypeError):
                    # 无法转换的值视为0
                    pass
            # 如果结果是整数，返回int类型
            if total == int(total):
                total = int(total)
            return OperatorResult(value=total)

        # 单值情况，尝试转换
        try:
            val = float(str(input_value))
            # 如果结果是整数，返回int类型
            if val == int(val):
                val = int(val)
            return OperatorResult(value=val)
        except (ValueError, TypeError):
            return OperatorResult(value=0)


class LessThanEqOperator(Operator):
    """小于等于验证操作符

    验证输入值是否小于等于期望值。
    支持 @row.X 同行列引用和 @var 变量引用。

    示例:
        - lte: 10                  # 值 <= 10
        - lte: "@row.D"            # 值 <= D列的值
        - lte: "@max_value"        # 值 <= 变量max_value
    """

    name = "lte"
    description = "验证小于等于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 转换为数字
        input_num = self._to_number(input_value)
        expected_num = self._to_number(expected)

        is_valid = input_num <= expected_num

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值 {input_num} 超过了最大值 {expected_num}",
            expected=f"<= {expected_num}",
            actual=input_num
        )

    def _to_number(self, value: Any) -> float:
        """将值转换为数字"""
        if value is None:
            return 0
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0


class GreaterThanEqOperator(Operator):
    """大于等于验证操作符

    验证输入值是否大于等于期望值。
    支持 @row.X 同行列引用和 @var 变量引用。

    示例:
        - gte: 10                  # 值 >= 10
        - gte: "@row.D"            # 值 >= D列的值
        - gte: "@min_value"        # 值 >= 变量min_value
    """

    name = "gte"
    description = "验证大于等于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 转换为数字
        input_num = self._to_number(input_value)
        expected_num = self._to_number(expected)

        is_valid = input_num >= expected_num

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值 {input_num} 小于最小值 {expected_num}",
            expected=f">= {expected_num}",
            actual=input_num
        )

    def _to_number(self, value: Any) -> float:
        """将值转换为数字"""
        if value is None:
            return 0
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0


class GreaterThanOperator(Operator):
    """大于验证操作符

    验证输入值是否大于期望值。
    支持 @row.X 同行列引用和 @var 变量引用。

    示例:
        - gt: 10                   # 值 > 10
        - gt: "@row.D"             # 值 > D列的值
        - gt: "@threshold"         # 值 > 变量threshold
    """

    name = "gt"
    description = "验证大于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 转换为数字
        input_num = self._to_number(input_value)
        expected_num = self._to_number(expected)

        is_valid = input_num > expected_num

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值 {input_num} 不大于 {expected_num}",
            expected=f"> {expected_num}",
            actual=input_num
        )

    def _to_number(self, value: Any) -> float:
        """将值转换为数字"""
        if value is None:
            return 0
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0


class LessThanOperator(Operator):
    """小于验证操作符

    验证输入值是否小于期望值。
    支持 @row.X 同行列引用和 @var 变量引用。

    示例:
        - lt: 10                   # 值 < 10
        - lt: "@row.D"             # 值 < D列的值
        - lt: "@threshold"         # 值 < 变量threshold
    """

    name = "lt"
    description = "验证小于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 转换为数字
        input_num = self._to_number(input_value)
        expected_num = self._to_number(expected)

        is_valid = input_num < expected_num

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值 {input_num} 不小于 {expected_num}",
            expected=f"< {expected_num}",
            actual=input_num
        )

    def _to_number(self, value: Any) -> float:
        """将值转换为数字"""
        if value is None:
            return 0
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return 0


class NotEqOperator(Operator):
    """不等于验证操作符

    验证输入值是否不等于期望值。
    支持 @row.X 同行列引用和 @var 变量引用。

    示例:
        - ne: 0                    # 值 != 0
        - ne: "@row.D"             # 值 != D列的值
        - ne: "@forbidden_value"   # 值 != 变量forbidden_value
    """

    name = "ne"
    description = "验证不等于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')
        expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)

        # 处理列表比较 - 将列表转换为集合进行比较（忽略顺序）
        input_set = self._to_set(input_value)
        expected_set = self._to_set(expected)

        is_valid = input_set != expected_set

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值不应该等于 {expected}",
            expected=f"!= {expected}",
            actual=input_value
        )

    def _to_set(self, value: Any) -> set:
        """将值转换为字符串集合进行比较"""
        if value is None:
            return set()
        if isinstance(value, list):
            return set(str(v).strip() for v in value if v is not None)
        if isinstance(value, str):
            # 如果是 | 分隔的字符串，分割后转换
            return set(v.strip() for v in value.split('|') if v.strip())
        return set([str(value)])


class AndOperator(Operator):
    """逻辑与操作符

    验证输入值是否为真（用于组合多个验证条件）。
    通常用于在pipeline中作为最后一个逻辑校验步骤。

    示例:
        - and: true                # 验证值为真（非空、非零、非False）
    """

    name = "and"
    description = "逻辑与验证"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        # 支持配置值或者直接使用输入值
        check_value = config.get('value', input_value)

        # 解析输入值
        is_valid = self._is_truthy(input_value) and self._is_truthy(check_value)

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else "逻辑与验证失败",
            expected="true",
            actual=input_value
        )

    def _is_truthy(self, value: Any) -> bool:
        """判断值是否为真"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip() != '' and value.strip().lower() not in ('false', '0', 'no', 'n')
        if isinstance(value, list):
            return len(value) > 0
        return True


class OrOperator(Operator):
    """逻辑或操作符

    验证输入值或期望值至少有一个为真。

    示例:
        - or: "@row.B"             # 验证值或B列的值至少一个为真
        - or: ["@var1", "@var2"]   # 验证值或变量至少一个为真
    """

    name = "or"
    description = "逻辑或验证"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')

        # 检查输入值
        input_truthy = self._is_truthy(input_value)

        # 解析并检查期望值
        if isinstance(expected_ref, list):
            expected_truthy = any(
                self._is_truthy(_resolve_config_value(ref, plugin_context, pipeline_vars, input_value))
                for ref in expected_ref
            )
        else:
            expected = _resolve_config_value(expected_ref, plugin_context, pipeline_vars, input_value)
            expected_truthy = self._is_truthy(expected)

        is_valid = input_truthy or expected_truthy

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else "逻辑或验证失败：所有值都为假",
            expected="至少一个为true",
            actual=input_value
        )

    def _is_truthy(self, value: Any) -> bool:
        """判断值是否为真"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip() != '' and value.strip().lower() not in ('false', '0', 'no', 'n')
        if isinstance(value, list):
            return len(value) > 0
        return True


class SameOperator(Operator):
    """Same操作符 - 验证两个值的真假性相同

    检查当前值与目标值的真假性（是否为空）是否一致。
    常用于处理字段间的互斥依赖关系。

    示例:
        # 验证当前值与I列的真假性相同
        - same: "@row.I"

        # 完整配置
        - same:
            target: "@row.I"
            message: "两个字段必须同时有值或同时为空"
    """

    name = "same"
    description = "验证两个值的真假性相同"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        # 解析配置
        if isinstance(config, str):
            target_ref = config
        elif isinstance(config, dict):
            if 'value' in config:
                target_ref = config['value']
            else:
                target_ref = config.get('target')
        else:
            target_ref = None

        if not target_ref:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message="same操作符需要指定目标值"
            )

        # 解析目标值
        target_value = _resolve_config_value(target_ref, plugin_context, pipeline_vars, input_value)

        # 判断真假性
        input_truthy = self._is_truthy(input_value)
        target_truthy = self._is_truthy(target_value)

        is_valid = input_truthy == target_truthy

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"字段依赖错误：当前值与{target_ref}必须同时有值或同时为空",
            expected=f"与{target_ref}一致性",
            actual=f"当前={'有值' if input_truthy else '为空'}, {target_ref}={'有值' if target_truthy else '为空'}"
        )

    def _is_truthy(self, value: Any) -> bool:
        """判断值是否为真（不为空）"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip() != '' and value.strip().lower() not in ('false', '0', 'no', 'n', 'null', 'none')
        if isinstance(value, list):
            return len(value) > 0
        return True


class MathOperator(Operator):
    """数学运算操作符

    对当前值执行基本四则运算。

    配置:
        op (str): 运算类型，支持 "add", "sub", "mul", "div"
        value (number|str): 运算数，可以是数字或变量引用

    示例:
        - math:
            op: "add"
            value: 1          # 当前值 + 1
        - math:
            op: "sub"
            value: "@offset"  # 当前值 - @offset变量
    """

    name = "math"
    description = "数学运算（加、减、乘、除）"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        # 解析配置
        if isinstance(config, dict):
            op = config.get('op')
            operand = config.get('value')
        else:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message="math操作符需要配置对象"
            )

        if not op:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message="math操作符需要指定op运算类型"
            )

        # 解析变量引用（支持 TemplateExpr）
        operand = _resolve_config_value(operand, plugin_context, pipeline_vars, input_value)

        # 转换为数字
        try:
            left = self._to_number(input_value)
            right = self._to_number(operand)
        except (TypeError, ValueError) as e:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"math操作符: {e}"
            )

        # 执行运算
        try:
            if op == "add":
                result = left + right
            elif op == "sub":
                result = left - right
            elif op == "mul":
                result = left * right
            elif op == "div":
                if right == 0:
                    return OperatorResult(
                        value=input_value,
                        is_valid=False,
                        error_message="除零错误"
                    )
                result = left / right
            else:
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=f"不支持的运算类型: {op}"
                )
        except Exception as e:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"运算错误: {e}"
            )

        return OperatorResult(value=result, is_valid=True)

    def _to_number(self, value: Any) -> Union[int, float]:
        """将值转换为数字"""
        if value is None:
            raise TypeError("不支持空值")
        if isinstance(value, bool):
            raise TypeError("不支持布尔值")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise TypeError("不支持空字符串")
            try:
                if '.' in value or 'e' in value.lower():
                    return float(value)
                return int(value)
            except ValueError:
                raise TypeError(f"无法将字符串'{value}'转换为数字")
        raise TypeError(f"无法将{type(value).__name__}转换为数字")


class RoundOperator(Operator):
    """四舍五入操作符

    对当前值进行四舍五入到指定小数位。

    配置:
        decimals (int): 保留小数位数，默认为 0

    示例:
        - round: 2          # 保留2位小数
        - round: 0          # 整数
    """

    name = "round"
    description = "四舍五入"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        if isinstance(config, dict):
            decimals = config.get('decimals', 0)
        elif isinstance(config, int):
            decimals = config
        else:
            decimals = 0

        try:
            value = self._to_number(input_value)
            result = round(value, decimals)
            return OperatorResult(value=result, is_valid=True)
        except (TypeError, ValueError) as e:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"round操作符: {e}"
            )

    def _to_number(self, value: Any) -> Union[int, float]:
        """将值转换为数字"""
        if value is None:
            raise TypeError("不支持空值")
        if isinstance(value, bool):
            raise TypeError("不支持布尔值")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise TypeError("不支持空字符串")
            try:
                if '.' in value or 'e' in value.lower():
                    return float(value)
                return int(value)
            except ValueError:
                raise TypeError(f"无法将字符串'{value}'转换为数字")
        raise TypeError(f"无法将{type(value).__name__}转换为数字")


class FloorOperator(Operator):
    """向下取整操作符

    返回不大于当前值的最大整数。
    """

    name = "floor"
    description = "向下取整"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        import math
        try:
            value = self._to_number(input_value)
            result = math.floor(value)
            return OperatorResult(value=result, is_valid=True)
        except (TypeError, ValueError) as e:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"floor操作符: {e}"
            )

    def _to_number(self, value: Any) -> Union[int, float]:
        """将值转换为数字"""
        if value is None:
            raise TypeError("不支持空值")
        if isinstance(value, bool):
            raise TypeError("不支持布尔值")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise TypeError("不支持空字符串")
            try:
                if '.' in value or 'e' in value.lower():
                    return float(value)
                return int(value)
            except ValueError:
                raise TypeError(f"无法将字符串'{value}'转换为数字")
        raise TypeError(f"无法将{type(value).__name__}转换为数字")


class CeilOperator(Operator):
    """向上取整操作符

    返回不小于当前值的最小整数。
    """

    name = "ceil"
    description = "向上取整"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        import math
        try:
            value = self._to_number(input_value)
            result = math.ceil(value)
            return OperatorResult(value=result, is_valid=True)
        except (TypeError, ValueError) as e:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"ceil操作符: {e}"
            )

    def _to_number(self, value: Any) -> Union[int, float]:
        """将值转换为数字"""
        if value is None:
            raise TypeError("不支持空值")
        if isinstance(value, bool):
            raise TypeError("不支持布尔值")
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise TypeError("不支持空字符串")
            try:
                if '.' in value or 'e' in value.lower():
                    return float(value)
                return int(value)
            except ValueError:
                raise TypeError(f"无法将字符串'{value}'转换为数字")
        raise TypeError(f"无法将{type(value).__name__}转换为数字")


class MapOperator(Operator):
    """Map操作符 - 对列表每个元素执行子操作符管道

    对输入列表的每个元素执行指定的子操作符管道，返回处理后的列表。
    不自动扁平化结果，保持嵌套结构。

    示例:
        - map:
            - split: ":"
            - extract: 1

    配置:
        pipeline: 子操作符步骤列表，每个步骤包含 operator 和 config
    """

    name = "map"
    description = "对列表每个元素执行子操作符管道"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        # 支持两种配置格式:
        # 1. pipeline: [...] - 显式指定
        # 2. value: [...] - 从YAML解析的简写格式
        pipeline_steps = config.get('pipeline') or config.get('value', [])
        if not pipeline_steps:
            return OperatorResult(value=input_value, is_valid=True)

        # 确保输入是列表
        if input_value is None:
            items = []
        elif isinstance(input_value, list):
            items = input_value
        else:
            items = [input_value]

        # 获取操作符管理器
        operator_manager = context.get('operator_manager')
        if not operator_manager:
            # 创建临时管理器
            operator_manager = OperatorManager()

        # 获取 pipeline_vars 用于状态传递
        pipeline_vars = context.get('pipeline_vars', {})

        results = []
        all_valid = True
        errors = []

        for idx, item in enumerate(items):
            current_value = item

            for step_config in pipeline_steps:
                # 转换简写格式为标准格式
                # 简写: {'split': ':'} -> 标准: {'operator': 'split', 'config': {'value': ':'}}
                if isinstance(step_config, dict):
                    if 'operator' in step_config and 'config' in step_config:
                        # 已经是标准格式
                        op_name = step_config['operator']
                        op_config = step_config['config']
                    else:
                        # 简写格式，第一个键是操作符名
                        op_name = list(step_config.keys())[0]
                        op_value = step_config[op_name]
                        # 标准化配置
                        if op_value is None:
                            op_config = {}
                        elif not isinstance(op_value, dict):
                            op_config = {'value': op_value}
                        else:
                            op_config = op_value
                else:
                    # 字符串格式
                    op_name = str(step_config)
                    op_config = {}

                # 创建执行上下文
                step_context = {
                    **context,
                    'pipeline_vars': pipeline_vars.copy(),
                    'operator_manager': operator_manager
                }

                result = operator_manager.execute(op_name, current_value, op_config, step_context)

                if not result.is_valid:
                    all_valid = False
                    errors.append(f"Item {idx}: {result.error_message}")
                    break

                current_value = result.value

            results.append(current_value)

        return OperatorResult(
            value=results,
            is_valid=all_valid,
            error_message="; ".join(errors) if errors else None
        )


class FlattenOperator(Operator):
    """扁平化操作符 - 将嵌套列表扁平化一层

    示例:
        - flatten                    # [["a","b"], ["c"]] → ["a","b","c"]

    配置:
        depth: 扁平化深度（默认1，当前只支持1层）
    """

    name = "flatten"
    description = "将嵌套列表扁平化一层"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        if input_value is None:
            return OperatorResult(value=[])

        if not isinstance(input_value, list):
            return OperatorResult(value=[input_value])

        result = []
        for item in input_value:
            if isinstance(item, list):
                result.extend(item)
            else:
                result.append(item)

        return OperatorResult(value=result)


class SliceOperator(Operator):
    """切片操作符 - 提取列表/字符串的子集

    支持按起始索引和结束索引切片，适用于取前N个元素等场景。

    示例:
        - slice: 3                    # 取前3个元素 [1,2,3,4,5] → [1,2,3]
        - slice: {start: 1, end: 4}   # 取第2到第4个 [1,2,3,4,5] → [2,3,4]
        - slice: {end: -1}            # 排除最后一个 [1,2,3,4] → [1,2,3]

    配置格式:
        - 数字N: 等同于 {start: 0, end: N}
        - {start: M, end: N}: 从索引M（含）到索引N（不含）
        - {end: N}: 从开头到索引N
        - {start: M}: 从索引M到末尾
    """

    name = "slice"
    description = "提取列表/字符串的子集"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        # 解析配置
        if isinstance(config, dict):
            if 'value' in config:
                cfg = config['value']
            else:
                cfg = config
        else:
            cfg = config

        # 简写格式: slice: 3 表示取前3个
        if isinstance(cfg, int):
            start, end = 0, cfg
        elif isinstance(cfg, dict):
            start = cfg.get('start', 0)
            end = cfg.get('end', None)
        else:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message="slice配置必须是整数或{start, end}对象"
            )

        # 处理列表
        if isinstance(input_value, list):
            if end is None:
                result = input_value[start:]
            else:
                result = input_value[start:end]
            return OperatorResult(value=result)

        # 处理字符串
        if isinstance(input_value, str):
            if end is None:
                result = input_value[start:]
            else:
                result = input_value[start:end]
            return OperatorResult(value=result)

        # 其他类型转为列表
        return OperatorResult(value=[input_value])


class TrimOperator(Operator):
    """Trim操作符 - 去除字符串（或列表中字符串）的首尾空格

    示例:
        - trim                       # "  hello  " → "hello"
        - trim                       # [" a ", " b "] → ["a", "b"]

    支持嵌套列表递归处理。
    """

    name = "trim"
    description = "去除字符串首尾空格"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        result = self._trim_recursive(input_value)
        return OperatorResult(value=result)

    def _trim_recursive(self, value: Any) -> Any:
        """递归处理值"""
        if value is None:
            return None

        if isinstance(value, str):
            return value.strip()

        if isinstance(value, list):
            return [self._trim_recursive(item) for item in value]

        # 非字符串非列表，原样返回
        return value


class ToNumberOperator(Operator):
    """转数字操作符 - 将字符串（或列表中字符串）转换为数字

    示例:
        - to_number                  # "123" → 123
        - to_number                  # ["1", "2"] → [1, 2]

    转换失败返回0，支持递归处理嵌套列表。
    """

    name = "to_number"
    description = "将字符串转换为数字"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        result = self._to_number_recursive(input_value)
        return OperatorResult(value=result)

    def _to_number_recursive(self, value: Any) -> Any:
        """递归处理值"""
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            try:
                s = value.strip()
                if '.' in s:
                    return float(s)
                return int(s)
            except (ValueError, TypeError):
                return 0

        if isinstance(value, list):
            return [self._to_number_recursive(item) for item in value]

        return 0


class AllOperator(Operator):
    """All操作符 - 验证列表中所有元素都满足指定条件

    对列表每个元素执行验证操作符管道，所有元素通过则整体通过。

    示例:
        - all:
            - lt: 10                   # 所有元素 < 10
        - all:
            - lt: "@row.D"             # 所有元素 < D列值

    配置:
        pipeline: 验证操作符步骤列表
    """

    name = "all"
    description = "验证列表所有元素满足条件"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        # 支持两种配置格式
        pipeline_steps = config.get('pipeline') or config.get('value', [])

        # 确保输入是列表
        if input_value is None:
            return OperatorResult(value=[], is_valid=True)

        if not isinstance(input_value, list):
            items = [input_value]
        else:
            items = input_value

        # 空列表视为通过
        if not items:
            return OperatorResult(value=[], is_valid=True)

        # 获取操作符管理器
        operator_manager = context.get('operator_manager')
        if not operator_manager:
            operator_manager = OperatorManager()

        pipeline_vars = context.get('pipeline_vars', {})
        errors = []

        for idx, item in enumerate(items):
            for step_config in pipeline_steps:
                # 转换简写格式为标准格式
                if isinstance(step_config, dict):
                    if 'operator' in step_config and 'config' in step_config:
                        op_name = step_config['operator']
                        op_config = step_config['config']
                    else:
                        op_name = list(step_config.keys())[0]
                        op_value = step_config[op_name]
                        if op_value is None:
                            op_config = {}
                        elif not isinstance(op_value, dict):
                            op_config = {'value': op_value}
                        else:
                            op_config = op_value
                else:
                    op_name = str(step_config)
                    op_config = {}

                step_context = {
                    **context,
                    'pipeline_vars': pipeline_vars.copy(),
                    'operator_manager': operator_manager
                }

                result = operator_manager.execute(op_name, item, op_config, step_context)

                if not result.is_valid:
                    errors.append(f"Item {idx} ({item}): {result.error_message}")
                    break

        is_valid = len(errors) == 0

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message="; ".join(errors) if errors else None,
            expected="所有元素满足条件",
            actual=f"{len(errors)}个元素不满足" if errors else "全部满足"
        )


class NotOperator(Operator):
    """逻辑非操作符

    验证输入值为假（空、零、False等）。

    示例:
        - not: true                # 验证值为假
        - not: "@row.B"            # 验证值不等于B列的值
    """

    name = "not"
    description = "逻辑非验证"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        expected_ref = config.get('value')

        if expected_ref is not None:
            # 如果提供了期望值，比较两者是否不相等
            expected = self._resolve_value(expected_ref, plugin_context, pipeline_vars)

            # 处理列表比较
            input_set = self._to_set(input_value)
            expected_set = self._to_set(expected)

            is_valid = input_set != expected_set
        else:
            # 否则检查输入值是否为假
            is_valid = not self._is_truthy(input_value)

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else "逻辑非验证失败：值应该为假或与期望值不同",
            expected="false或不同",
            actual=input_value
        )

    def _resolve_value(self, ref: Any, plugin_context: Any, pipeline_vars: Dict) -> Any:
        """解析值引用"""
        if not isinstance(ref, str):
            return ref

        if ref.startswith('@row.'):
            if plugin_context:
                return plugin_context.get_row_value(ref[5:])
            return None
        elif ref.startswith('@'):
            var_name = ref[1:]
            return pipeline_vars.get(var_name, ref)
        return ref

    def _to_set(self, value: Any) -> set:
        """将值转换为字符串集合进行比较"""
        if value is None:
            return set()
        if isinstance(value, list):
            return set(str(v).strip() for v in value if v is not None)
        if isinstance(value, str):
            return set(v.strip() for v in value.split('|') if v.strip())
        return set([str(value)])

    def _is_truthy(self, value: Any) -> bool:
        """判断值是否为真"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip() != '' and value.strip().lower() not in ('false', '0', 'no', 'n')
        if isinstance(value, list):
            return len(value) > 0
        return True


class InOperator(Operator):
    """包含于验证操作符

    验证输入值是否存在于指定的集合中。
    支持 @row.X 同行列引用和 @var 变量引用。
    """

    name = "in"
    description = "验证包含于"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        pipeline_vars = context.get('pipeline_vars', {})

        container_ref = config.get('value')
        container = self._resolve_container(container_ref, plugin_context, pipeline_vars)

        # 构建容器集合
        container_set = self._to_set(container)

        # 检查输入值
        if isinstance(input_value, list):
            is_valid = all(str(v) in container_set for v in input_value if v is not None)
        else:
            is_valid = str(input_value) in container_set

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"值不在允许的集合中",
            expected=list(container_set) if isinstance(container, (list, str)) else container,
            actual=input_value
        )

    def _resolve_container(self, ref: Any, plugin_context: Any, pipeline_vars: Dict) -> Any:
        """解析容器引用"""
        if not isinstance(ref, str):
            return ref

        # @row.X -> 同行列值
        if ref.startswith('@row.'):
            if plugin_context:
                return plugin_context.get_row_value(ref[5:])
            return None

        # @var -> 变量值
        if ref.startswith('@'):
            var_name = ref[1:]
            return pipeline_vars.get(var_name, ref)

        return ref

    def _to_set(self, value: Any) -> set:
        """将值转换为字符串集合"""
        if value is None:
            return set()
        if isinstance(value, list):
            return set(str(v).strip() for v in value if v is not None)
        if isinstance(value, str):
            return set(v.strip() for v in value.split('|') if v.strip())
        return set([str(value)])


class SourceOperator(Operator):
    """数据源操作符 - 指定数据来源

    支持的数据源:
    - @value: 原始单元格值（从上下文中获取）
    - @cell: 同 @value
    - @row.X: 同行X列的值
    - 其他: 直接使用配置值
    """

    name = "source"
    description = "指定数据来源"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        plugin_context = context.get('plugin_context')
        source_ref = config.get('value', '@value')

        if source_ref == '@value' or source_ref == '@cell':
            # 使用原始单元格值（从上下文中获取，而不是input_value）
            original_value = context.get('original_value', input_value)
            return OperatorResult(value=original_value)
        elif isinstance(source_ref, str) and source_ref.startswith('@row.'):
            if plugin_context:
                value = plugin_context.get_row_value(source_ref[5:])
                return OperatorResult(value=value)
            else:
                return OperatorResult(value=None)
        else:
            # 直接使用配置的值
            return OperatorResult(value=source_ref)


class AsOperator(Operator):
    """命名中间结果操作符"""

    name = "as"
    description = "命名中间结果"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        name = config.get('value', '')
        if name and 'pipeline_vars' in context:
            context['pipeline_vars'][name] = input_value
        return OperatorResult(value=input_value)


class UseOperator(Operator):
    """使用变量操作符 - 从pipeline_vars中读取变量值"""

    name = "use"
    description = "使用存储的变量值"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        var_ref = config.get('value', '')
        if isinstance(var_ref, str) and var_ref.startswith('@'):
            var_name = var_ref[1:]
        else:
            var_name = var_ref

        if 'pipeline_vars' in context and var_name in context['pipeline_vars']:
            return OperatorResult(value=context['pipeline_vars'][var_name])
        return OperatorResult(value=var_ref)


class GetOperator(Operator):
    """获取字段操作符"""

    name = "get"
    description = "从记录中获取字段"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        field_name = config.get('value', '')

        if isinstance(input_value, dict):
            return OperatorResult(value=input_value.get(field_name))
        elif isinstance(input_value, list):
            result = []
            for item in input_value:
                if isinstance(item, dict):
                    result.append(item.get(field_name))
            return OperatorResult(value=result)
        else:
            return OperatorResult(value=None)


class SheetExistsOperator(Operator):
    """Sheet存在性检查操作符

    检查指定的Sheet是否存在。支持变量替换 {value}。

    示例:
        - sheet_exists: "PassNewReward({value})"
    """

    name = "sheet_exists"
    description = "检查Sheet是否存在"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        pattern = config.get('value', '')

        # 替换 {value} 为当前单元格值
        if isinstance(input_value, list):
            # 如果是列表，检查每个值
            results = []
            for val in input_value:
                sheet_name = pattern.replace('{value}', str(val))
                excel_provider = context.get('excel_provider')
                if excel_provider:
                    exists = sheet_name in excel_provider.get_sheet_names()
                    results.append(exists)
                else:
                    results.append(False)
            is_valid = all(results)
        else:
            sheet_name = pattern.replace('{value}', str(input_value))
            excel_provider = context.get('excel_provider')
            if excel_provider:
                is_valid = sheet_name in excel_provider.get_sheet_names()
            else:
                is_valid = False

        return OperatorResult(
            value=input_value,
            is_valid=is_valid,
            error_message=None if is_valid else f"Sheet不存在: {sheet_name}"
        )


class CollectOperator(Operator):
    """收集操作符

    跨行收集数据，将所有单元格的值收集到列表中。
    这是一个聚合操作符，需要在规则级别特殊处理。

    示例:
        - collect: "ids"
    """

    name = "collect"
    description = "跨行收集数据"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        """执行收集操作

        实际收集逻辑在引擎中处理，这里只做标记。
        """
        key = config.get('value', 'collected')
        return OperatorResult(
            value=input_value,
            is_valid=True,
            metadata={'collect_key': key, 'collected_value': input_value}
        )


class SequentialOperator(Operator):
    """顺序ID验证操作符

    验证ID是否符合 prefix + number 的格式并按顺序累加。

    示例:
        - sequential:
            prefix: "eventpass"
            start_from: 1
            allow_gap: false
    """

    name = "sequential"
    description = "验证ID按顺序累加"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        """执行顺序验证

        实际验证逻辑在引擎中处理，这里只做标记。
        """
        return OperatorResult(
            value=input_value,
            is_valid=True,
            metadata={'sequential_config': config}
        )


class RowCountOperator(Operator):
    """行数统计操作符

    获取指定Sheet的数据行数，支持跳过指定行数。
    可用于验证某列的值是否等于另一个Sheet的数据行数。

    示例:
        # 获取当前文件指定Sheet的行数（跳过前4行）
        - row_count:
            sheet: "PassNewEFGH"
            skip_rows: 4

        # 通过refs引用获取外部文件行数
        - row_count:
            ref: "external_data"
            skip_rows: 4

        # 直接指定外部文件路径
        - row_count:
            file: "other.xlsx"
            sheet: "Sheet1"
            skip_rows: 0
    """

    name = "row_count"
    description = "获取Sheet数据行数"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        """执行行数统计

        Args:
            input_value: 输入值（忽略）
            config: 配置参数
                - sheet: Sheet名称（同文件时使用）
                - ref: 外部数据源引用名称（通过refs定义）
                - file: 文件路径（直接指定）
                - skip_rows: 跳过行数（可选，默认0）
            context: 执行上下文

        Returns:
            OperatorResult: 包含行数的结果
        """
        # 统一处理配置格式
        if isinstance(config.get('value'), dict):
            cfg = config['value']
        elif isinstance(config, dict) and 'value' not in config:
            cfg = config
        else:
            cfg = {}

        sheet_name = cfg.get('sheet')
        ref_name = cfg.get('ref')
        file_path = cfg.get('file')
        skip_rows = cfg.get('skip_rows', 0)

        # 支持简写格式: row_count: "SheetName"
        if isinstance(config.get('value'), str):
            sheet_name = config['value']
            skip_rows = 0

        # 如果指定了ref，从external_data获取文件和sheet信息
        if ref_name:
            external_data = context.get('external_data')
            if external_data and hasattr(external_data, 'get_source'):
                try:
                    source = external_data.get_source(ref_name)
                    file_path = str(source.file)
                    sheet_name = source.sheet
                except KeyError:
                    return OperatorResult(
                        value=None,
                        is_valid=False,
                        error_message=f"未找到refs定义: {ref_name}"
                    )
            else:
                return OperatorResult(
                    value=None,
                    is_valid=False,
                    error_message="外部数据管理器未配置"
                )

        if not sheet_name:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message="row_count操作符需要指定sheet、ref或value参数"
            )

        try:
            # 如果指定了外部文件，需要创建新的provider
            if file_path:
                from echecker.excel.provider import ExcelProvider
                provider = ExcelProvider(file_path).open()
                try:
                    max_row, _ = provider.get_sheet_dimensions(sheet_name)
                finally:
                    provider.close()
            else:
                # 使用当前文件的provider
                provider = context.get('excel_provider')
                if not provider:
                    return OperatorResult(
                        value=None,
                        is_valid=False,
                        error_message="无法获取Excel provider"
                    )
                max_row, _ = provider.get_sheet_dimensions(sheet_name)

            # 计算有效数据行数（总行数 - 跳过行数）
            data_rows = max(0, max_row - skip_rows)

            return OperatorResult(
                value=data_rows,
                is_valid=True
            )

        except Exception as e:
            return OperatorResult(
                value=None,
                is_valid=False,
                error_message=f"获取Sheet行数失败: {e}"
            )


class FilterOperator(Operator):
    """数组过滤操作符

    根据指定条件过滤数组元素，支持正则、前缀、后缀匹配。
    """

    name = "filter"
    description = "根据条件过滤数组元素"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        import re

        filter_type = config.get("type")

        if input_value is None:
            return OperatorResult(value=[], is_valid=True)

        # 统一转为数组处理
        if not isinstance(input_value, list):
            input_value = [input_value]

        if filter_type == "regex":
            pattern = config.get("pattern", "")
            try:
                regex = re.compile(pattern)
                result = [item for item in input_value
                         if item is not None and regex.search(str(item))]
                return OperatorResult(value=result, is_valid=True)
            except re.error as e:
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=f"无效的正则表达式: {e}"
                )

        elif filter_type == "prefix":
            prefix = config.get("value", "")
            result = [item for item in input_value
                     if item is not None and str(item).startswith(prefix)]
            return OperatorResult(value=result, is_valid=True)

        elif filter_type == "suffix":
            suffix = config.get("value", "")
            result = [item for item in input_value
                     if item is not None and str(item).endswith(suffix)]
            return OperatorResult(value=result, is_valid=True)

        return OperatorResult(
            value=input_value,
            is_valid=False,
            error_message=f"未知的过滤类型: {filter_type}"
        )


class MatchStructureOperator(Operator):
    """结构匹配验证操作符

    验证单个值或数组的每个元素符合指定结构。
    """

    name = "match_structure"
    description = "验证值或数组元素的结构"

    def execute(self, input_value: Any, config: Dict[str, Any], context: Dict[str, Any]) -> OperatorResult:
        import re

        validate_type = config.get("type")
        mode = config.get("mode", "each")
        custom_message = config.get("message", "结构验证失败")

        # 构建验证函数
        def get_validator():
            if validate_type == "regex":
                pattern = config.get("pattern", "")
                try:
                    regex = re.compile(pattern)
                    return lambda x: bool(regex.match(str(x))) if x is not None else False
                except re.error as e:
                    return None, f"无效的正则表达式: {e}"
            elif validate_type == "prefix":
                prefix = config.get("value", "")
                return lambda x: str(x).startswith(prefix) if x is not None else False
            elif validate_type == "suffix":
                suffix = config.get("value", "")
                return lambda x: str(x).endswith(suffix) if x is not None else False
            return None, f"未知的验证类型: {validate_type}"

        validator_result = get_validator()
        if isinstance(validator_result, tuple):
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=validator_result[1]
            )
        validator = validator_result

        # 根据 mode 执行验证
        if mode == "single":
            # 将输入作为整体验证
            if input_value is None:
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=custom_message,
                    expected=f"符合{validate_type}验证",
                    actual=None
                )
            if not validator(input_value):
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=custom_message,
                    expected=f"符合{validate_type}验证",
                    actual=input_value
                )
            return OperatorResult(value=input_value, is_valid=True)
        else:  # mode == "each"
            # 如果是数组，验证每个元素；如果是单值，直接验证
            if input_value is None:
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=custom_message,
                    expected=f"符合{validate_type}验证",
                    actual=None
                )

            items = input_value if isinstance(input_value, list) else [input_value]
            errors = []

            for idx, item in enumerate(items):
                if not validator(item):
                    errors.append(str(item) if item is not None else "None")

            if errors:
                error_msg = f"{custom_message}: 以下元素不符合规范: {', '.join(errors)}"
                return OperatorResult(
                    value=input_value,
                    is_valid=False,
                    error_message=error_msg,
                    expected=f"符合{validate_type}验证",
                    actual=errors
                )

            return OperatorResult(value=input_value, is_valid=True)


class OperatorManager:
    """操作符管理器

    负责管理所有可用的操作符。
    """

    def __init__(self):
        self._operators: Dict[str, Operator] = {}
        self._register_builtin_operators()

    def _register_builtin_operators(self):
        """注册内置操作符"""
        operators = [
            SplitOperator(),
            CountOperator(),
            ExtractOperator(),
            LookupOperator(),
            ExistsOperator(),
            ExistsInOperator(),
            WhereOperator(),
            AllExistInOperator(),
            UnionOperator(),
            UniqueOperator(),
            EqOperator(),
            CountEqOperator(),
            InOperator(),
            SourceOperator(),
            AsOperator(),
            UseOperator(),
            GetOperator(),
            SheetExistsOperator(),
            CollectOperator(),
            SequentialOperator(),
            RowCountOperator(),
            SumOperator(),
            LessThanEqOperator(),
            GreaterThanEqOperator(),
            GreaterThanOperator(),
            LessThanOperator(),
            NotEqOperator(),
            AndOperator(),
            OrOperator(),
            NotOperator(),
            SameOperator(),
            MapOperator(),
            FlattenOperator(),
            SliceOperator(),
            TrimOperator(),
            ToNumberOperator(),
            AllOperator(),
            MathOperator(),
            RoundOperator(),
            FloorOperator(),
            CeilOperator(),
            FilterOperator(),
            MatchStructureOperator(),
        ]

        for op in operators:
            self.register(op)

    def register(self, operator: Operator) -> None:
        """注册操作符"""
        self._operators[operator.name] = operator

    def get(self, name: str) -> Optional[Operator]:
        """获取操作符"""
        return self._operators.get(name)

    def has(self, name: str) -> bool:
        """检查操作符是否存在"""
        return name in self._operators

    def list_operators(self) -> List[str]:
        """列出所有操作符名称"""
        return list(self._operators.keys())

    def execute(
        self,
        operator_name: str,
        input_value: Any,
        config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> OperatorResult:
        """执行操作符"""
        operator = self.get(operator_name)
        if operator is None:
            return OperatorResult(
                value=input_value,
                is_valid=False,
                error_message=f"未知操作符: {operator_name}"
            )

        return operator.execute(input_value, config, context)


class Pipeline:
    """Pipeline执行器

    负责执行一系列操作符步骤。
    """

    def __init__(self, operator_manager: OperatorManager):
        self.operator_manager = operator_manager

    def execute(
        self,
        pipeline: PipelineValidation,
        initial_value: Any,
        context: Dict[str, Any]
    ) -> OperatorResult:
        """执行pipeline

        Args:
            pipeline: Pipeline验证配置
            initial_value: 初始值（当前单元格值）
            context: 执行上下文

        Returns:
            OperatorResult: 最终执行结果
        """
        current_value = initial_value

        # 保存原始单元格值到上下文，供 source @value 使用
        context['original_value'] = initial_value

        for step in pipeline.steps:
            result = self.operator_manager.execute(
                step.operator,
                current_value,
                step.config,
                context
            )

            if not result.is_valid:
                return result

            current_value = result.value

        return OperatorResult(value=current_value, is_valid=True)


class V3ValidationEngine:
    """V3校验引擎

    使用pipeline操作符语法的校验引擎。
    """

    def __init__(
        self,
        operator_manager: Optional[OperatorManager] = None,
        external_data: Optional[ExternalDataManager] = None
    ):
        self.operator_manager = operator_manager or OperatorManager()
        self.external_data = external_data or ExternalDataManager()
        self.excel_provider: Optional[ExcelProvider] = None
        self._report = ValidationReport()
        self._pipeline_executor = Pipeline(self.operator_manager)

    def validate(
        self,
        excel_path: Path,
        ruleset: V3RuleSet
    ) -> ValidationReport:
        """执行校验

        Args:
            excel_path: Excel文件路径
            ruleset: V3规则集

        Returns:
            ValidationReport: 校验报告
        """
        self._report = ValidationReport()
        start_time = time.time()

        # 1. 初始化外部数据源
        self._init_external_data(ruleset)

        # 2. 打开Excel
        self.excel_provider = ExcelProvider(str(excel_path)).open()

        try:
            # 3. 执行每条规则
            for rule in ruleset.rules:
                if not rule.enabled:
                    continue
                self._validate_rule(rule)

        finally:
            # 4. 关闭Excel
            self.excel_provider.close()

        # 5. 生成报告摘要
        self._report.summary.duration_seconds = time.time() - start_time
        self._report.summary.total_rules = len(ruleset.rules)

        return self._report

    def get_results(self) -> ValidationReport:
        """获取验证结果

        Returns:
            ValidationReport: 当前验证报告
        """
        return self._report

    def _init_external_data(self, ruleset: V3RuleSet) -> None:
        """初始化外部数据源"""
        for ref_name, ref_config in ruleset.refs.items():
            source = ExternalDataSource(
                name=ref_name,
                file=ref_config.file,
                sheet=ref_config.sheet,
                columns=ref_config.columns
            )
            self.external_data.register_source(source)

    def _validate_rule(self, rule: V3Rule) -> None:
        """校验单条规则"""
        # 解析目标范围
        cell_range = CellRange.from_string(rule.target)

        # 处理动态末尾标记 (如 A5:*)
        if cell_range._dynamic_end_row:
            actual_end_row = self._get_actual_end_row(cell_range)
            cell_range.end_row = actual_end_row
            cell_range._dynamic_end_row = False

        cell_refs = list(cell_range.to_cell_refs())

        # 用于跨单元格共享的缓存
        shared_cache: Dict[str, Any] = {}

        # 检查是否包含聚合操作符的pipeline
        has_aggregate = self._has_aggregate_operator(rule)

        if has_aggregate:
            # 聚合操作符需要特殊处理：先收集所有数据，再执行验证
            self._validate_rule_with_aggregate(rule, cell_refs, shared_cache)
        else:
            # 普通规则：逐单元格验证
            for idx, cell_ref in enumerate(cell_refs):
                # 获取单元格值
                value = self.excel_provider.get_cell_value(cell_ref)

                # 获取整行数据
                row_data = self._get_row_data(cell_ref.sheet, cell_ref.row)

                # 构建单元格引用字符串
                col_letter = self._column_index_to_letter(cell_ref.col)
                cell_ref_str = f"{col_letter}{cell_ref.row}"

                # 创建行执行上下文
                row_context = RowContext(
                    excel_path=self.excel_provider.path,
                    current_sheet=cell_ref.sheet,
                    current_cell=cell_ref_str,
                    current_row=cell_ref.row,
                    current_col=cell_ref.col,
                    _row_data=row_data,
                    _external_data=self.external_data,
                    _cache=shared_cache
                )

                # 创建pipeline执行上下文
                pipeline_context = {
                    'external_data': self.external_data,
                    'plugin_context': row_context,
                    'row_data': row_data,
                    'cell_ref': cell_ref_str,
                    'sheet': cell_ref.sheet,
                    'pipeline_vars': {},
                    'excel_provider': self.excel_provider
                }

                # 执行每个校验
                for validation in rule.validations:
                    self._validate_with_pipeline(
                        value, pipeline_context, validation, cell_ref_str, rule.id
                    )

    def _has_aggregate_operator(self, rule: V3Rule) -> bool:
        """检查规则是否包含聚合操作符"""
        aggregate_ops = {'collect', 'sequential', 'previous'}
        for validation in rule.validations:
            if validation.validation_type == 'pipeline':
                for step in validation.pipeline.steps:
                    if step.operator in aggregate_ops:
                        return True
        return False

    def _validate_rule_with_aggregate(
        self, rule: V3Rule, cell_refs: list, shared_cache: Dict[str, Any]
    ) -> None:
        """使用聚合操作符验证规则"""
        # 收集所有单元格的数据
        collected_data: List[Dict] = []

        for cell_ref in cell_refs:
            value = self.excel_provider.get_cell_value(cell_ref)
            row_data = self._get_row_data(cell_ref.sheet, cell_ref.row)
            col_letter = self._column_index_to_letter(cell_ref.col)
            cell_ref_str = f"{col_letter}{cell_ref.row}"

            collected_data.append({
                'cell_ref': cell_ref_str,
                'sheet': cell_ref.sheet,
                'row': cell_ref.row,
                'col': cell_ref.col,
                'value': value,
                'row_data': row_data
            })

        # 对每个validation执行收集和验证
        for validation in rule.validations:
            if validation.validation_type != 'pipeline':
                continue

            steps = validation.pipeline.steps

            # 检查是否有collect操作符
            collect_step_idx = None
            collect_key = 'collected'
            sequential_config = None

            for idx, step in enumerate(steps):
                if step.operator == 'collect':
                    collect_step_idx = idx
                    collect_key = step.config.get('value', 'collected')
                elif step.operator == 'sequential':
                    sequential_config = step.config

            if collect_step_idx is not None:
                # 执行collect：收集所有值
                collected_values = []

                for data in collected_data:
                    value = data['value']

                    # 执行collect之前的步骤
                    current_value = value
                    for step in steps[:collect_step_idx]:
                        result = self.operator_manager.execute(
                            step.operator, current_value, step.config,
                            {
                                'external_data': self.external_data,
                                'plugin_context': RowContext(
                                    excel_path=self.excel_provider.path,
                                    current_sheet=data['sheet'],
                                    current_cell=data['cell_ref'],
                                    current_row=data['row'],
                                    current_col=data['col'],
                                    _row_data=data['row_data'],
                                    _external_data=self.external_data,
                                    _cache=shared_cache
                                ),
                                'row_data': data['row_data'],
                                'cell_ref': data['cell_ref'],
                                'sheet': data['sheet'],
                                'pipeline_vars': {},
                                'excel_provider': self.excel_provider
                            }
                        )
                        if result.is_valid:
                            current_value = result.value

                    # 添加到收集列表
                    if isinstance(current_value, list):
                        collected_values.extend(current_value)
                    elif current_value is not None:
                        collected_values.append(current_value)

                # 执行collect之后的验证步骤
                remaining_steps = steps[collect_step_idx + 1:]

                # 如果有sequential操作符，执行顺序验证
                if sequential_config:
                    self._validate_sequential(
                        collected_values, sequential_config, collected_data,
                        rule.id, validation.message
                    )

                # 执行剩余的验证步骤（如果有）
                for step in remaining_steps:
                    if step.operator == 'sequential':
                        continue  # 已经处理过了
                    # 其他验证步骤的处理...

    def _validate_sequential(
        self, values: List[Any], config: Dict, collected_data: List[Dict],
        rule_id: str, message: str
    ) -> None:
        """验证顺序ID"""
        prefix = config.get('prefix', '')
        start_from = config.get('start_from', 1)
        allow_gap = config.get('allow_gap', False)

        errors = []
        valid_entries = []

        # 解析所有值
        for i, value in enumerate(values):
            if value is None or str(value).strip() == '':
                continue

            value_str = str(value).strip()
            pattern = f'^{re.escape(prefix)}(\\d+)$'
            match = re.match(pattern, value_str)

            if match:
                number = int(match.group(1))
                valid_entries.append((i, number, value_str))
            else:
                errors.append({
                    'cell': collected_data[i]['cell_ref'] if i < len(collected_data) else f'idx_{i}',
                    'message': f"ID格式错误: {value_str}",
                    'expected': f'{prefix}N',
                    'actual': value_str
                })

        if not valid_entries:
            return

        # 检查是否从start_from开始
        first_num = valid_entries[0][1]
        if first_num != start_from:
            idx, _, val = valid_entries[0]
            self._report.add_error(ValidationError(
                rule_id=rule_id,
                cell_ref=f"{collected_data[idx]['sheet']}.{collected_data[idx]['cell_ref']}",
                error_type=ErrorType.FORMAT_ERROR,
                message=f"ID应从 {prefix}{start_from} 开始，但第一个是 {val}",
                severity=Severity.ERROR,
                sheet_name=collected_data[idx]['sheet']
            ))

        # 检查是否连续
        if not allow_gap:
            numbers = [num for _, num, _ in valid_entries]
            expected_sequence = list(range(min(numbers), max(numbers) + 1))
            missing = set(expected_sequence) - set(numbers)

            if missing:
                missing_str = ', '.join(f'{prefix}{n}' for n in sorted(missing))
                last_idx, _, _ = valid_entries[-1]
                self._report.add_error(ValidationError(
                    rule_id=rule_id,
                    cell_ref=f"{collected_data[last_idx]['sheet']}.{collected_data[last_idx]['cell_ref']}",
                    error_type=ErrorType.FORMAT_ERROR,
                    message=f"ID序号不连续，缺少: {missing_str}",
                    severity=Severity.ERROR,
                    sheet_name=collected_data[last_idx]['sheet']
                ))

    def _validate_with_pipeline(
        self,
        value: Any,
        context: Dict[str, Any],
        validation: V3ValidationConfig,
        cell_ref_str: str,
        rule_id: str
    ) -> None:
        """使用pipeline执行校验"""
        if not validation.pipeline:
            return

        result = self._pipeline_executor.execute(
            validation.pipeline,
            value,
            context
        )

        if not result.is_valid:
            error = ValidationError(
                rule_id=rule_id,
                cell_ref=f"{context['sheet']}.{cell_ref_str}",
                error_type=ErrorType.FORMAT_ERROR,
                message=result.error_message or validation.message or "Pipeline验证失败",
                severity=Severity.ERROR,
                sheet_name=context['sheet'],
                expected=result.expected,
                actual=result.actual
            )
            self._report.add_error(error)

    def _get_row_data(self, sheet: str, row: int) -> Dict[str, Any]:
        """获取整行数据"""
        row_data = {}
        for col_idx in range(1, 27):
            col_letter = self._column_index_to_letter(col_idx)
            cell_ref = CellRef(sheet=sheet, row=row, col=col_idx)
            value = self.excel_provider.get_cell_value(cell_ref)
            if value is not None:
                row_data[col_letter] = value
        return row_data

    def _get_actual_end_row(self, cell_range: CellRange) -> int:
        """获取动态范围的实际结束行号"""
        sheet = cell_range.sheet
        start_row = cell_range.start_row
        start_col = cell_range.start_col

        max_row = self.excel_provider.get_sheet_dimensions(sheet)[0]

        last_data_row = start_row
        consecutive_empty = 0
        max_consecutive_empty = 3

        for row in range(start_row, max_row + 1):
            cell_ref = CellRef(sheet=sheet, row=row, col=start_col)
            value = self.excel_provider.get_cell_value(cell_ref)

            if value is not None and str(value).strip() != '':
                last_data_row = row
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    break

        return last_data_row

    @staticmethod
    def _column_index_to_letter(index: int) -> str:
        """将1-based索引转换为Excel列字母"""
        result = ""
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            result = chr(ord('A') + remainder) + result
        return result


def validate_excel(
    excel_path: Path,
    rules_path: Path
) -> ValidationReport:
    """校验Excel文件（便捷函数）

    Args:
        excel_path: Excel文件路径
        rules_path: 规则文件路径

    Returns:
        ValidationReport: 校验报告
    """
    from echecker.rules.v3_parser import V3RuleParser, is_v3_rules

    # 自动检测规则版本
    with open(rules_path, 'r', encoding='utf-8') as f:
        import yaml
        data = yaml.safe_load(f)

    if is_v3_rules(data):
        parser = V3RuleParser()
        ruleset = parser.parse_file(rules_path)
        engine = V3ValidationEngine()
    else:
        raise ValueError("无法识别的规则文件格式，请使用V3格式规则文件（version: '3.0'）")

    return engine.validate(excel_path, ruleset)
