"""
内置转换操作符

提供数据转换相关的操作符：
- split: 字符串分割
- extract: 复合值提取
- map: 映射操作
- unique: 去重
- flatten: 扁平化
"""

from typing import Any, Dict, List

from ..base import (
    OperatorResult,
    OperatorType,
    PipelineContext,
    PipelineOperator,
    register_operator,
)


@register_operator
class SplitOperator(PipelineOperator):
    """
    字符串分割操作符

    将字符串按分隔符分割成列表。如果输入是列表，对每个元素分割后扁平化。

    配置：
        delimiter (str): 分隔符，默认为 ","

    示例：
        >>> op = SplitOperator()
        >>> op.execute("a,b,c", context, {"delimiter": ","})
        OperatorResult(success=True, value=["a", "b", "c"])

        >>> op.execute(["a,b", "c,d"], context, {"delimiter": ","})
        OperatorResult(success=True, value=["a", "b", "c", "d"])
    """

    name = "split"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "字符串分割，支持批量处理"
    config_spec = {
        "type": "object",
        "properties": {
            "delimiter": {
                "type": "string",
                "default": ",",
                "description": "分隔符",
            }
        },
    }

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        delimiter = config.get("delimiter", ",")

        if value is None:
            return OperatorResult(success=True, value=[])

        # 如果是字符串，直接分割
        if isinstance(value, str):
            if not value:
                return OperatorResult(success=True, value=[])
            return OperatorResult(success=True, value=value.split(delimiter))

        # 如果是列表，对每个元素分割后扁平化
        if isinstance(value, list):
            result = []
            for item in value:
                if isinstance(item, str):
                    if item:  # 跳过空字符串
                        result.extend(item.split(delimiter))
                elif item is not None:
                    # 非字符串元素转为字符串处理
                    result.append(str(item))
            return OperatorResult(success=True, value=result)

        # 其他类型转为字符串处理
        return OperatorResult(success=True, value=[str(value)])


@register_operator
class ExtractOperator(PipelineOperator):
    """
    复合值提取操作符

    按分隔符分割字符串，取第index部分。如果输入是列表，对每个元素提取。

    配置：
        delimiter (str): 分隔符，默认为 ":"
        index (int): 取第几部分，默认为0

    示例：
        >>> op = ExtractOperator()
        >>> op.execute("93106:1", context, {"delimiter": ":", "index": 0})
        OperatorResult(success=True, value="93106")

        >>> op.execute(["a:1", "b:2", "c:3"], context, {"delimiter": ":", "index": 0})
        OperatorResult(success=True, value=["a", "b", "c"])
    """

    name = "extract"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "复合值提取，如从'id:count'中提取id"
    config_spec = {
        "type": "object",
        "properties": {
            "delimiter": {
                "type": "string",
                "default": ":",
                "description": "分隔符",
            },
            "index": {
                "type": "integer",
                "default": 0,
                "description": "取第几部分（从0开始）",
            },
        },
    }

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        delimiter = config.get("delimiter", ":")
        index = config.get("index", 0)

        if value is None:
            return OperatorResult(success=True, value=None)

        def _extract(val: Any) -> Any:
            if val is None:
                return None
            if not isinstance(val, str):
                val = str(val)
            parts = val.split(delimiter)
            if 0 <= index < len(parts):
                return parts[index]
            return None

        # 如果是列表，对每个元素提取
        if isinstance(value, list):
            result = [_extract(item) for item in value]
            # 过滤None值
            result = [r for r in result if r is not None]
            return OperatorResult(success=True, value=result)

        # 单值处理
        return OperatorResult(success=True, value=_extract(value))


@register_operator
class MapOperator(PipelineOperator):
    """
    映射操作符

    对列表中的每个元素执行指定操作。

    配置：
        operation (str): 操作类型，支持 "strip", "lower", "upper", "int", "float", "str"

    示例：
        >>> op = MapOperator()
        >>> op.execute(["  A  ", "  B  "], context, {"operation": "strip"})
        OperatorResult(success=True, value=["A", "B"])

        >>> op.execute(["a", "b", "c"], context, {"operation": "upper"})
        OperatorResult(success=True, value=["A", "B", "C"])
    """

    name = "map"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "对列表元素执行映射操作"
    config_spec = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["strip", "lower", "upper", "int", "float", "str"],
                "default": "str",
                "description": "映射操作类型",
            }
        },
        "required": ["operation"],
    }

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        operation = config.get("operation", "str")

        # 如果输入不是列表，转为单元素列表
        if not isinstance(value, list):
            value = [value] if value is not None else []

        def _apply(val: Any) -> Any:
            if val is None:
                return None

            if operation == "strip":
                return str(val).strip()
            elif operation == "lower":
                return str(val).lower()
            elif operation == "upper":
                return str(val).upper()
            elif operation == "int":
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return None
            elif operation == "float":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None
            elif operation == "str":
                return str(val)
            else:
                # 未知操作，返回原值
                return val

        result = [_apply(item) for item in value]
        # 过滤None值
        result = [r for r in result if r is not None]

        return OperatorResult(success=True, value=result)


@register_operator
class UniqueOperator(PipelineOperator):
    """
    去重操作符

    移除列表中的重复项，保持顺序。

    配置：
        无特殊配置

    示例：
        >>> op = UniqueOperator()
        >>> op.execute(["a", "b", "a", "c", "b"], context, {})
        OperatorResult(success=True, value=["a", "b", "c"])
    """

    name = "unique"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "列表去重，保持顺序"
    config_spec = {"type": "object", "properties": {}}

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        if value is None:
            return OperatorResult(success=True, value=[])

        if not isinstance(value, list):
            # 非列表转为单元素列表
            return OperatorResult(success=True, value=[value])

        seen = set()
        result = []

        for item in value:
            # 使用元组处理不可哈希类型（如列表）
            try:
                key = item
                hash(key)
            except TypeError:
                key = str(item)

            if key not in seen:
                seen.add(key)
                result.append(item)

        return OperatorResult(success=True, value=result)


@register_operator
class FlattenOperator(PipelineOperator):
    """
    扁平化操作符

    将嵌套列表扁平化为单层列表。

    配置：
        无特殊配置

    示例：
        >>> op = FlattenOperator()
        >>> op.execute([["a", "b"], ["c", "d"]], context, {})
        OperatorResult(success=True, value=["a", "b", "c", "d"])

        >>> op.execute(["a", ["b", "c"], "d"], context, {})
        OperatorResult(success=True, value=["a", "b", "c", "d"])
    """

    name = "flatten"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "嵌套列表扁平化"
    config_spec = {"type": "object", "properties": {}}

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        if value is None:
            return OperatorResult(success=True, value=[])

        if not isinstance(value, list):
            return OperatorResult(success=True, value=[value])

        def _flatten(items: List[Any]) -> List[Any]:
            result = []
            for item in items:
                if isinstance(item, list):
                    result.extend(_flatten(item))
                elif item is not None:
                    result.append(item)
            return result

        return OperatorResult(success=True, value=_flatten(value))


@register_operator
class CountOperator(PipelineOperator):
    """计数操作符

    计算列表元素个数。如果输入是字符串，按分隔符分割后计数；
    如果输入是列表，直接返回列表长度；如果输入是None或空，返回0。

    配置：
        delimiter (str): 当输入为字符串时的分隔符，默认"|"

    示例：
        >>> op = CountOperator()
        >>> op.execute(["a", "b", "c"], context, {})
        OperatorResult(success=True, value=3)

        >>> op.execute("a|b|c", context, {"delimiter": "|"})
        OperatorResult(success=True, value=3)

        >>> op.execute("", context, {})
        OperatorResult(success=True, value=0)
    """

    name = "count"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "计算列表元素个数"
    config_spec = {
        "type": "object",
        "properties": {
            "delimiter": {
                "type": "string",
                "default": "|",
                "description": "字符串分隔符",
            }
        },
    }

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        delimiter = config.get("delimiter", "|")

        if value is None:
            return OperatorResult(success=True, value=0)

        # 如果是字符串，按分隔符分割后计数
        if isinstance(value, str):
            if not value.strip():
                return OperatorResult(success=True, value=0)
            parts = value.split(delimiter)
            # 过滤空字符串
            parts = [p for p in parts if p.strip()]
            return OperatorResult(success=True, value=len(parts))

        # 如果是列表，返回长度
        if isinstance(value, list):
            return OperatorResult(success=True, value=len(value))

        # 其他类型视为单元素
        return OperatorResult(success=True, value=1)


import re


@register_operator
class FilterOperator(PipelineOperator):
    """
    数组过滤操作符

    根据指定条件过滤数组元素，支持正则、前缀、后缀匹配。

    配置：
        type (str): 过滤类型，支持 "regex", "prefix", "suffix"
        pattern (str): 正则表达式（当 type="regex" 时使用）
        value (str): 前缀/后缀字符串（当 type="prefix"/"suffix" 时使用）

    示例：
        >>> op = FilterOperator()
        >>> op.execute(["a", "b", "c"], context, {"type": "regex", "pattern": "^a"})
        OperatorResult(success=True, value=["a"])
    """

    name = "filter"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "根据条件过滤数组元素"
    config_spec = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["regex", "prefix", "suffix"],
                "description": "过滤方式"
            },
            "pattern": {
                "type": "string",
                "description": "正则表达式（当 type=regex 时使用）"
            },
            "value": {
                "type": "string",
                "description": "前缀/后缀字符串（当 type=prefix/suffix 时使用）"
            }
        },
        "required": ["type"]
    }

    def execute(
        self, value: Any, context: PipelineContext, config: Dict
    ) -> OperatorResult:
        filter_type = config.get("type")

        if value is None:
            return OperatorResult(success=True, value=[])

        # 统一转为数组处理
        if not isinstance(value, list):
            value = [value]

        if filter_type == "regex":
            pattern = config.get("pattern", "")
            try:
                regex = re.compile(pattern)
                result = [item for item in value
                         if item is not None and regex.search(str(item))]
                return OperatorResult(success=True, value=result)
            except re.error as e:
                return OperatorResult.error(f"无效的正则表达式: {e}")

        elif filter_type == "prefix":
            prefix = config.get("value", "")
            result = [item for item in value
                     if item is not None and str(item).startswith(prefix)]
            return OperatorResult(success=True, value=result)

        elif filter_type == "suffix":
            suffix = config.get("value", "")
            result = [item for item in value
                     if item is not None and str(item).endswith(suffix)]
            return OperatorResult(success=True, value=result)

        return OperatorResult.error(f"未知的过滤类型: {filter_type}")
