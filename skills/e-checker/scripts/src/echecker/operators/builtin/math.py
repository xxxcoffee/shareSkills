"""数学运算操作符

提供数值计算相关的操作符：
- math: 基本四则运算
- round: 四舍五入
- floor: 向下取整
- ceil: 向上取整
"""

import math
from typing import Any, Dict, Union

from ..base import Operator, OperatorContext, OperatorResult, OperatorType, register_operator


def _resolve_value(value: Any, context: OperatorContext) -> Any:
    """解析值，如果是变量引用则解析变量

    Args:
        value: 值或变量引用
        context: 操作符上下文

    Returns:
        解析后的值
    """
    if isinstance(value, str) and value.startswith("@"):
        return context.resolve_variable(value)
    return value


def _to_number(value: Any) -> Union[int, float]:
    """将值转换为数字

    Args:
        value: 输入值

    Returns:
        int 或 float

    Raises:
        TypeError: 无法转换为数字
    """
    if value is None:
        raise TypeError("math操作符不支持空值输入")

    if isinstance(value, bool):
        # bool 是 int 的子类，需要单独处理
        raise TypeError(f"math操作符不支持布尔值")

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise TypeError("math操作符不支持空字符串")
        try:
            if '.' in value or 'e' in value.lower():
                return float(value)
            return int(value)
        except ValueError:
            raise TypeError(f"无法将字符串转换为数字: '{value}'")

    raise TypeError(f"无法转换为数字: {type(value).__name__}")


@register_operator
class MathOperator(Operator):
    """数学运算操作符

    对当前值执行基本四则运算。

    配置：
        op (str): 运算类型，支持 "add", "sub", "mul", "div"
        value (number|str): 运算数，可以是数字或变量引用

    示例：
        >>> op = MathOperator()
        >>> op.execute(5, context, {"op": "add", "value": 1})
        OperatorResult(success=True, value=6)

        >>> op.execute(10, context, {"op": "mul", "value": 2})
        OperatorResult(success=True, value=20)

        # 使用变量
        >>> op.execute(5, context, {"op": "sub", "value": "@offset"})
        # 如果 @offset = 2，结果为 3
    """

    name = "math"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "基本数学运算（加、减、乘、除）"
    config_spec = {
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["add", "sub", "mul", "div"],
                "description": "运算类型",
            },
            "value": {
                "oneOf": [
                    {"type": "number"},
                    {"type": "string", "description": "变量引用，如 @offset 或 @row.B"},
                ],
                "description": "运算数",
            },
        },
        "required": ["op", "value"],
    }

    def execute(
        self, input_data: Any, context: OperatorContext, config: Dict
    ) -> OperatorResult:
        op = config.get("op")
        operand = config.get("value")

        # 解析变量引用
        try:
            operand = _resolve_value(operand, context)
        except Exception as e:
            return OperatorResult.error(f"变量解析失败: {e}")

        # 转换为数字
        try:
            left = _to_number(input_data)
            right = _to_number(operand)
        except TypeError as e:
            return OperatorResult.error(str(e))

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
                    return OperatorResult.error("除零错误")
                result = left / right
            else:
                return OperatorResult.error(f"不支持的运算类型: {op}")
        except Exception as e:
            return OperatorResult.error(f"运算错误: {e}")

        return OperatorResult.ok(result)


@register_operator
class RoundOperator(Operator):
    """四舍五入操作符

    对当前值进行四舍五入到指定小数位。

    配置：
        decimals (int): 保留小数位数，默认为 0

    示例：
        >>> op = RoundOperator()
        >>> op.execute(3.14159, context, {"decimals": 2})
        OperatorResult(success=True, value=3.14)

        >>> op.execute(2.71828, context, {})
        OperatorResult(success=True, value=3)  # 默认整数
    """

    name = "round"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "四舍五入到指定小数位"
    config_spec = {
        "type": "object",
        "properties": {
            "decimals": {
                "type": "integer",
                "default": 0,
                "description": "保留小数位数",
            },
        },
    }

    def execute(
        self, input_data: Any, context: OperatorContext, config: Dict
    ) -> OperatorResult:
        decimals = config.get("decimals", 0)

        # 转换为数字
        try:
            value = _to_number(input_data)
        except TypeError as e:
            return OperatorResult.error(str(e))

        try:
            result = round(value, decimals)
            return OperatorResult.ok(result)
        except Exception as e:
            return OperatorResult.error(f"取整错误: {e}")


@register_operator
class FloorOperator(Operator):
    """向下取整操作符

    返回不大于当前值的最大整数。

    示例：
        >>> op = FloorOperator()
        >>> op.execute(4.7, context, {})
        OperatorResult(success=True, value=4)

        >>> op.execute(-1.2, context, {})
        OperatorResult(success=True, value=-2)
    """

    name = "floor"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "向下取整"
    config_spec = {"type": "object", "properties": {}}

    def execute(
        self, input_data: Any, context: OperatorContext, config: Dict
    ) -> OperatorResult:
        # 转换为数字
        try:
            value = _to_number(input_data)
        except TypeError as e:
            return OperatorResult.error(str(e))

        try:
            result = math.floor(value)
            return OperatorResult.ok(result)
        except Exception as e:
            return OperatorResult.error(f"取整错误: {e}")


@register_operator
class CeilOperator(Operator):
    """向上取整操作符

    返回不小于当前值的最小整数。

    示例：
        >>> op = CeilOperator()
        >>> op.execute(4.2, context, {})
        OperatorResult(success=True, value=5)

        >>> op.execute(-1.7, context, {})
        OperatorResult(success=True, value=-1)
    """

    name = "ceil"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "向上取整"
    config_spec = {"type": "object", "properties": {}}

    def execute(
        self, input_data: Any, context: OperatorContext, config: Dict
    ) -> OperatorResult:
        # 转换为数字
        try:
            value = _to_number(input_data)
        except TypeError as e:
            return OperatorResult.error(str(e))

        try:
            result = math.ceil(value)
            return OperatorResult.ok(result)
        except Exception as e:
            return OperatorResult.error(f"取整错误: {e}")
