"""验证操作符

提供最终验证相关的操作符。
"""

from typing import Any, Dict, List

from echecker.operators.base import (
    Operator,
    OperatorContext,
    OperatorResult,
    OperatorType,
    register_operator,
)


@register_operator
class ExistsOperator(Operator):
    """存在性验证操作符

    验证值是否存在于查找结果中。
    """

    name = "exists"
    operator_type = OperatorType.VALIDATE
    description = "验证值是否存在"
    config_spec = {
        "type": "object",
        "properties": {}
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class ExistsInOperator(Operator):
    """存在性验证操作符（集合版本）

    验证所有值是否都存在于查找结果中。
    """

    name = "exists_in"
    operator_type = OperatorType.VALIDATE
    description = "验证所有值是否存在于集合中"
    config_spec = {
        "type": "object",
        "properties": {}
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class AllExistInOperator(Operator):
    """全部存在性验证操作符

    验证当前值列表是否全部存在于目标列的列表中。

    配置:
        target_column: 目标列字母
        split_by: 列表分隔符
    """

    name = "all_exist_in"
    operator_type = OperatorType.VALIDATE
    description = "验证所有值都存在于目标列列表中"
    config_spec = {
        "type": "object",
        "properties": {
            "target_column": {"type": "string", "description": "目标列字母"},
            "split_by": {"type": "string", "description": "列表分隔符", "default": "|"}
        },
        "required": ["target_column"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class RangeCheckOperator(Operator):
    """范围校验操作符

    验证数值是否在指定范围内。

    配置:
        min: 最小值
        max: 最大值
        exclusive_min: 是否排除最小值
        exclusive_max: 是否排除最大值
        target_column: 可选，比较目标列
    """

    name = "range_check"
    operator_type = OperatorType.VALIDATE
    description = "验证数值范围"
    config_spec = {
        "type": "object",
        "properties": {
            "min": {"type": ["number", "null"]},
            "max": {"type": ["number", "null"]},
            "exclusive_min": {"type": "boolean"},
            "exclusive_max": {"type": "boolean"},
            "target_column": {"type": "string", "description": "比较目标列（可选）"}
        }
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class ValidateOperator(Operator):
    """通用验证操作符

    使用正则表达式或其他方式验证值。

    配置:
        pattern: 验证模式（正则表达式）
        type: 验证类型（regex等）
    """

    name = "validate"
    operator_type = OperatorType.VALIDATE
    description = "通用值验证"
    config_spec = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "验证模式"},
            "type": {"type": "string", "enum": ["regex", "email", "url", "int", "float"], "default": "regex"}
        },
        "required": ["pattern"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


# 为兼容性提供的别名类
@register_operator
class EqOperator(Operator):
    """等于验证操作符"""
    name = "eq"
    operator_type = OperatorType.VALIDATE
    description = "验证值是否等于预期值"
    config_spec = {
        "type": "object",
        "properties": {
            "value": {"description": "预期值"}
        },
        "required": ["value"]
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        expected = config.get("value")
        return OperatorResult.ok(input_data)  # 待实现


@register_operator
class InOperator(Operator):
    """包含验证操作符"""
    name = "in"
    operator_type = OperatorType.VALIDATE
    description = "验证值是否在指定集合中"
    config_spec = {
        "type": "object",
        "properties": {
            "values": {"type": "array", "description": "允许的值的集合"}
        },
        "required": ["values"]
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        return OperatorResult.ok(input_data)  # 待实现


@register_operator
class RegexMatchOperator(Operator):
    """正则匹配操作符"""
    name = "regex_match"
    operator_type = OperatorType.VALIDATE
    description = "使用正则表达式验证值"
    config_spec = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "正则表达式模式"}
        },
        "required": ["pattern"]
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        return OperatorResult.ok(input_data)  # 待实现


import re


@register_operator
class MatchStructureOperator(Operator):
    """
    结构匹配验证操作符

    验证单个值或数组的每个元素符合指定结构。

    配置：
        type (str): 验证类型，支持 "regex", "prefix", "suffix"
        pattern (str): 正则表达式（当 type="regex" 时使用）
        value (str): 前缀/后缀字符串（当 type="prefix"/"suffix" 时使用）
        mode (str): 验证模式，"each"（默认）或 "single"
        message (str): 自定义错误信息

    示例：
        >>> op = MatchStructureOperator()
        >>> op.execute(["a", "b"], context, {"type": "regex", "pattern": "^[a-z]$"})
        OperatorResult(success=True)
    """

    name = "match_structure"
    operator_type = OperatorType.VALIDATE
    version = "1.0.0"
    description = "验证值或数组元素的结构"
    config_spec = {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["regex", "prefix", "suffix"],
                "description": "验证方式"
            },
            "pattern": {
                "type": "string",
                "description": "正则表达式"
            },
            "value": {
                "type": "string",
                "description": "前缀/后缀值"
            },
            "mode": {
                "type": "string",
                "enum": ["each", "single"],
                "default": "each",
                "description": "验证模式"
            },
            "message": {
                "type": "string",
                "description": "自定义错误信息"
            }
        },
        "required": ["type"]
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
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
            return OperatorResult.error(validator_result[1])
        validator = validator_result

        # 根据 mode 执行验证
        if mode == "single":
            # 将输入作为整体验证
            if input_data is None:
                return OperatorResult.error(
                    custom_message,
                    [{"value": None, "reason": "值为空"}]
                )
            if not validator(input_data):
                return OperatorResult.error(
                    custom_message,
                    [{"value": str(input_data), "reason": f"不符合{validate_type}验证"}]
                )
            return OperatorResult.ok(input_data)
        else:  # mode == "each"
            # 如果是数组，验证每个元素；如果是单值，直接验证
            if input_data is None:
                return OperatorResult.error(
                    custom_message,
                    [{"value": None, "reason": "值为空"}]
                )

            items = input_data if isinstance(input_data, list) else [input_data]
            errors = []

            for idx, item in enumerate(items):
                if not validator(item):
                    errors.append({
                        "value": str(item) if item is not None else None,
                        "index": idx if isinstance(input_data, list) else None,
                        "reason": f"不符合{validate_type}验证规则"
                    })

            if errors:
                error_msg = f"{custom_message}: {len(errors)}个元素不符合规范"
                return OperatorResult.error(error_msg, errors)

            return OperatorResult.ok(input_data)
