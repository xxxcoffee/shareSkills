"""eChecker V3 操作符系统

Pipeline架构的核心包，提供可组合的验证操作符。
"""

from echecker.operators.base import (
    Operator,
    PipelineOperator,  # 别名，向后兼容
    AggregateOperator,
    OperatorContext,
    PipelineContext,  # 别名，向后兼容
    OperatorResult,
    OperatorType,
    Pipeline,
    register_operator,
    get_operator_class,
    list_registered_operators,
    get_operators_by_type,
)
from echecker.operators.manager import OperatorManager, OperatorInfo
from echecker.operators.pipeline import (
    PipelineStep,
    PipelineResult,
    PipelineBuilder,
)
from echecker.operators.registry import (
    OperatorRegistry,
    register as registry_register,
    get_registry,
    get_operator,
    get_operator_instance,
    list_operators as registry_list_operators,
)

# 导入builtin包以自动注册内置操作符
try:
    from echecker.operators import builtin
    # 触发操作符注册
    _ = builtin.REGISTERED_OPERATORS
except ImportError:
    pass  # builtin包可能不存在

__all__ = [
    # 基类
    "Operator",
    "PipelineOperator",  # 别名
    "AggregateOperator",
    "OperatorContext",
    "PipelineContext",  # 别名
    "OperatorResult",
    "OperatorType",
    "Pipeline",
    # 管理器
    "OperatorManager",
    "OperatorInfo",
    # Pipeline构建
    "PipelineStep",
    "PipelineResult",
    "PipelineBuilder",
    # 注册中心
    "OperatorRegistry",
    # 注册函数
    "register_operator",
    "get_operator_class",
    "list_registered_operators",
    "get_operators_by_type",
    "get_operator",
    "get_operator_instance",
]

__version__ = "3.0.0"
