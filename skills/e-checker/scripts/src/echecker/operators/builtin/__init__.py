"""内置操作符包

V3管道架构的内置操作符集合。
"""

from echecker.operators.base import (
    PipelineOperator,
    AggregateOperator,
    PipelineContext,
    OperatorResult,
    OperatorType,
    register_operator,
    get_operator_class,
    list_registered_operators,
    get_operators_by_type,
)

from echecker.operators.builtin.transform import (
    SplitOperator,
    ExtractOperator,
    MapOperator,
    UniqueOperator,
    FlattenOperator,
    CountOperator,
    FilterOperator,
)

from echecker.operators.builtin.math import (
    MathOperator,
    RoundOperator,
    FloorOperator,
    CeilOperator,
)

from echecker.operators.builtin.collection import (
    UnionOperator,
    IntersectOperator,
    CollectOperator,
    SequentialOperator,
    PreviousOperator,
)

from echecker.operators.builtin.source import (
    SourceOperator,
)

from echecker.operators.builtin.lookup import (
    LookupOperator,
    WhereOperator,
    GetOperator,
    AttributeMatchOperator,
    SheetExistsOperator,
)

from echecker.operators.builtin.validate import (
    ExistsOperator,
    ExistsInOperator,
    EqOperator,
    InOperator,
    AllExistInOperator,
    RangeCheckOperator,
    RegexMatchOperator,
    MatchStructureOperator,
)

# 自动注册所有内置操作符
def _register_all():
    """确保所有操作符类被加载并注册"""
    # 这些导入确保操作符类被加载并执行register_operator装饰器
    operators = [
        # 数据源操作符
        SourceOperator,
        # 转换操作符
        SplitOperator,
        ExtractOperator,
        MapOperator,
        UniqueOperator,
        FlattenOperator,
        CountOperator,
        FilterOperator,
        # 数学运算操作符
        MathOperator,
        RoundOperator,
        FloorOperator,
        CeilOperator,
        # 查找操作符
        LookupOperator,
        WhereOperator,
        GetOperator,
        AttributeMatchOperator,
        SheetExistsOperator,
        # 集合操作符
        UnionOperator,
        IntersectOperator,
        CollectOperator,
        SequentialOperator,
        PreviousOperator,
        # 验证操作符
        ExistsOperator,
        ExistsInOperator,
        EqOperator,
        InOperator,
        AllExistInOperator,
        RangeCheckOperator,
        RegexMatchOperator,
        MatchStructureOperator,
    ]
    return operators


# 执行注册
REGISTERED_OPERATORS = _register_all()

__all__ = [
    # 基类
    "PipelineOperator",
    "AggregateOperator",
    "PipelineContext",
    "OperatorResult",
    "OperatorType",
    # 注册函数
    "register_operator",
    "get_operator_class",
    "list_registered_operators",
    "get_operators_by_type",
    # 数据源操作符
    "SourceOperator",
    # 转换操作符
    "SplitOperator",
    "ExtractOperator",
    "MapOperator",
    "UniqueOperator",
    "FlattenOperator",
    "CountOperator",
    "FilterOperator",
    # 数学运算操作符
    "MathOperator",
    "RoundOperator",
    "FloorOperator",
    "CeilOperator",
    # 查找操作符
    "LookupOperator",
    "WhereOperator",
    "GetOperator",
    "AttributeMatchOperator",
    "SheetExistsOperator",
    # 集合操作符
    "UnionOperator",
    "IntersectOperator",
    "CollectOperator",
    "SequentialOperator",
    "PreviousOperator",
    # 验证操作符
    "ExistsOperator",
    "ExistsInOperator",
    "EqOperator",
    "InOperator",
    "AllExistInOperator",
    "RangeCheckOperator",
    "RegexMatchOperator",
    "MatchStructureOperator",
    # 常量
    "REGISTERED_OPERATORS",
]
