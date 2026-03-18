"""源操作符

提供数据源获取相关的操作符。
"""

from typing import Any, Dict

from echecker.operators.base import (
    Operator,
    OperatorContext,
    OperatorResult,
    OperatorType,
    register_operator,
)


@register_operator
class SourceOperator(Operator):
    """数据源操作符

    从指定列获取源值。

    配置:
        column: 源列字母
    """

    name = "source"
    operator_type = OperatorType.SOURCE
    description = "从指定列获取源值"
    config_spec = {
        "type": "object",
        "properties": {
            "column": {"type": "string", "description": "源列字母"}
        },
        "required": ["column"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        """执行源操作

        从行数据中获取指定列的值。
        """
        column = config.get("column")
        if not column:
            return OperatorResult.error("缺少column配置")

        value = context.get_row_value(column)
        return OperatorResult.ok(value)


@register_operator
class AsOperator(Operator):
    """别名操作符

    将当前值命名为指定变量，便于后续引用。

    配置:
        name: 变量名
    """

    name = "as"
    operator_type = OperatorType.SOURCE
    description = "为值设置别名"
    config_spec = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "变量名"}
        },
        "required": ["name"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        """执行别名操作"""
        name = config.get("name")
        if not name:
            return OperatorResult.error("缺少name配置")

        # 设置状态变量
        return OperatorResult.ok(
            value=input_data,
            state_updates={name: input_data}
        )
