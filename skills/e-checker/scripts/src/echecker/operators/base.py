"""操作符基类定义

V3管道架构的核心组件，定义操作符接口和类型。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union


class OperatorType(Enum):
    """操作符类型"""
    SOURCE = auto()      # 数据源操作符（产生数据）
    TRANSFORM = auto()   # 转换操作符（变换数据）
    LOOKUP = auto()      # 查找操作符（查询外部数据）
    AGGREGATE = auto()   # 聚合操作符（跨行收集）
    VALIDATE = auto()    # 验证操作符（最终验证）


@dataclass
class OperatorResult:
    """操作符执行结果

    Attributes:
        success: 操作是否成功
        value: 输出数据（用于TRANSFORM/LOOKUP类型）
        errors: 错误列表（用于VALIDATE类型）
        message: 错误消息
        state_updates: 状态更新（用于跨操作符共享数据）
    """
    success: bool
    value: Any = None
    errors: List[Dict] = field(default_factory=list)
    message: Optional[str] = None
    state_updates: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.state_updates is None:
            self.state_updates = {}

    @classmethod
    def ok(cls, value: Any = None, state_updates: Dict[str, Any] = None) -> "OperatorResult":
        """创建成功的结果"""
        return cls(success=True, value=value, state_updates=state_updates or {})

    @classmethod
    def error(cls, message: str, errors: List[Dict] = None) -> "OperatorResult":
        """创建失败的结果"""
        return cls(success=False, message=message, errors=errors or [])


@dataclass
class OperatorContext:
    """操作符执行上下文

    提供操作符执行时所需的所有上下文信息，包括：
    - 基础位置信息（文件、工作表、单元格）
    - 行数据访问（支持@row.X语法）
    - 外部数据访问（跨文件引用）
    - Pipeline状态共享
    - 模板表达式求值支持
    """
    excel_path: Optional[Path] = None
    current_sheet: str = ""
    current_cell: str = ""
    current_row: int = 0
    current_col: int = 0
    cell_value: Any = None
    row_data: Dict[str, Any] = field(default_factory=dict)
    pipeline_state: Dict[str, Any] = field(default_factory=dict)
    external_data: Any = None
    excel_provider: Any = None  # Excel数据提供者

    def __post_init__(self):
        if self.row_data is None:
            self.row_data = {}
        if self.pipeline_state is None:
            self.pipeline_state = {}

    def get_row_value(self, col_ref: str) -> Any:
        """获取同行其他列的值

        Args:
            col_ref: 列引用，如"H"或"@row.H"

        Returns:
            列值
        """
        # 处理 @row.H 格式
        if col_ref.startswith("@row."):
            col_ref = col_ref[5:]

        col_ref = col_ref.upper()
        return self.row_data.get(col_ref)

    def get_state(self, key: str, default=None) -> Any:
        """获取管道状态值"""
        return self.pipeline_state.get(key, default)

    def set_state(self, key: str, value: Any):
        """设置管道状态值"""
        self.pipeline_state[key] = value

    def update_state(self, updates: Dict[str, Any]):
        """批量更新管道状态"""
        self.pipeline_state.update(updates)

    def resolve_variable(self, var_ref: str) -> Any:
        """解析变量引用

        支持以下语法：
        - @value: 当前单元格值
        - @row.X: 同行X列的值
        - @var_name: Pipeline状态中的变量

        Args:
            var_ref: 变量引用字符串

        Returns:
            Any: 解析后的值
        """
        if not var_ref.startswith("@"):
            return var_ref

        # @value -> 当前值
        if var_ref == "@value":
            return self.cell_value

        # @row.X -> 行数据
        if var_ref.startswith("@row."):
            return self.get_row_value(var_ref[5:])

        # @var_name -> Pipeline状态
        return self.get_state(var_ref[1:])

    @property
    def cell_ref(self) -> str:
        """获取完整单元格引用（如"Sheet1.A1"）"""
        return f"{self.current_sheet}.{self.current_cell}"

    def evaluate_template(self, value: Any) -> Any:
        """求值模板表达式

        如果值是 TemplateExpr，则在当前上下文中求值；
        如果是普通值，则直接返回。

        Args:
            value: 配置值（可能是 TemplateExpr 或其他类型）

        Returns:
            Any: 求值结果
        """
        from echecker.expression.template import TemplateExpr
        from echecker.expression.context import EvalContext

        if isinstance(value, TemplateExpr):
            eval_context = EvalContext.from_operator_context(self)
            return value.evaluate(eval_context)

        return value

    def resolve_config_value(self, config: Dict[str, Any], key: str, default: Any = None) -> Any:
        """解析配置值（支持模板表达式）

        从配置字典中获取指定键的值，如果是 TemplateExpr 则自动求值。

        Args:
            config: 配置字典
            key: 键名
            default: 默认值

        Returns:
            Any: 解析后的值
        """
        from echecker.expression.template import TemplateExpr
        from echecker.expression.context import EvalContext

        value = config.get(key, default)

        if isinstance(value, TemplateExpr):
            eval_context = EvalContext.from_operator_context(self)
            return value.evaluate(eval_context)

        return value


# 别名，保持兼容性
PipelineContext = OperatorContext


class Operator(ABC):
    """操作符基类

    所有操作符必须继承此类，并提供以下类属性：
    - name: 操作符标识名（唯一）
    - operator_type: OperatorType枚举值
    - description: 描述
    - config_spec: JSON Schema格式的配置规格

    示例:
        class MyOperator(Operator):
            name = "my_operator"
            operator_type = OperatorType.TRANSFORM
            description = "我的操作符"
            config_spec = {
                "type": "object",
                "properties": {
                    "param": {"type": "string"}
                }
            }

            def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
                # 实现操作逻辑
                return OperatorResult.ok(result)
    """

    # 类属性：元数据
    name: str = ""  # 操作符标识名（必须唯一）
    operator_type: OperatorType = OperatorType.TRANSFORM  # 操作符类型
    version: str = "1.0.0"  # 版本
    description: str = ""  # 描述
    category: str = "general"  # 分类

    # 类属性：配置规格（用于YAML校验和IDE提示）
    config_spec: Dict[str, Any] = {}  # JSON Schema格式

    def __init__(self):
        """初始化操作符实例"""
        pass

    @abstractmethod
    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        """执行操作符

        Args:
            input_data: 输入值（来自上一步的结果）
            context: 管道执行上下文
            config: 该操作符的配置（来自YAML规则文件）

        Returns:
            OperatorResult: 执行结果
        """
        pass

    @classmethod
    def get_config_spec(cls) -> Dict[str, Any]:
        """获取配置规格，用于YAML校验和IDE自动完成

        Returns:
            Dict: JSON Schema格式的配置规格
        """
        return cls.config_spec


# 别名，保持兼容性
PipelineOperator = Operator


class AggregateOperator(Operator):
    """聚合操作符基类

    聚合操作符在单cell验证阶段收集数据，在finalize阶段执行验证。
    子类需要实现:
    - collect(): 收集阶段逻辑
    - finalize(): 最终验证逻辑
    """

    operator_type = OperatorType.AGGREGATE

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        """默认执行方法 - 调用collect进行数据收集"""
        return self.collect(input_data, context, config)

    @abstractmethod
    def collect(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        """收集阶段 - 收集数据到pipeline_state

        Args:
            input_data: 当前单元格值
            context: 管道上下文
            config: 配置

        Returns:
            OperatorResult: 收集结果（通常success=True，仅收集数据）
        """
        pass

    @abstractmethod
    def finalize(self, context: OperatorContext, config: Dict) -> OperatorResult:
        """最终验证阶段 - 在所有单元格处理完毕后调用

        Args:
            context: 管道上下文（包含完整的pipeline_state）
            config: 配置

        Returns:
            OperatorResult: 验证结果
        """
        pass


class Pipeline:
    """Pipeline执行引擎

    一组有序的操作符，按顺序执行数据转换和验证。

    示例:
        pipeline = Pipeline([
            {"operator": "split", "config": {"delimiter": "|"}},
            {"operator": "lookup", "config": {"ref_source": "elements", "column": "id"}},
            {"operator": "exists", "config": {}}
        ], operator_manager)

        result = pipeline.execute("a|b|c", context)
    """

    def __init__(self, steps: List[Dict[str, Any]], operator_manager: Any):
        """初始化Pipeline

        Args:
            steps: 操作符步骤列表，每个步骤包含operator名称和config
            operator_manager: 操作符管理器，用于获取操作符实例
        """
        self.steps = steps
        self.operator_manager = operator_manager

    def execute(self, initial_value: Any, context: OperatorContext) -> OperatorResult:
        """按顺序执行所有操作符

        Args:
            initial_value: 初始输入值
            context: 操作符执行上下文

        Returns:
            OperatorResult: 执行结果
        """
        current_value = initial_value
        all_errors = []

        for step in self.steps:
            op_name = step.get("operator")
            config = step.get("config", {})
            on_error = step.get("on_error", "fail")  # fail, continue, skip

            # 求值配置中的模板表达式
            config = self._evaluate_config_templates(config, context)

            operator_class = self.operator_manager.get_operator(op_name)
            if operator_class is None:
                error_msg = f"操作符 '{op_name}' 不存在"
                if on_error == "fail":
                    return OperatorResult.error(error_msg)
                continue

            # 创建操作符实例并执行
            operator = operator_class()
            result = operator.execute(current_value, context, config)

            # 应用状态更新
            if result.state_updates:
                context.update_state(result.state_updates)

            if not result.success:
                if result.errors:
                    all_errors.extend(result.errors)
                if result.message:
                    all_errors.append({"message": result.message})

                # 遇到验证失败的操作符，根据on_error策略处理
                if operator_class.operator_type == OperatorType.VALIDATE:
                    if on_error == "fail":
                        break
                elif on_error == "fail":
                    break

            # 更新当前值（用于下一步的输入）
            current_value = result.value if result.value is not None else current_value

        return OperatorResult(
            success=len(all_errors) == 0,
            value=current_value,
            errors=all_errors
        )

    def _evaluate_config_templates(self, config: Any, context: OperatorContext) -> Any:
        """求值配置中的模板表达式

        递归处理配置数据，将所有 TemplateExpr 求值为实际值。

        Args:
            config: 配置数据（可能是 dict, list 或标量值）
            context: 操作符执行上下文

        Returns:
            Any: 求值后的配置数据
        """
        from echecker.expression.template import TemplateExpr
        from echecker.expression.context import EvalContext

        if isinstance(config, dict):
            return {
                key: self._evaluate_config_templates(value, context)
                for key, value in config.items()
            }

        elif isinstance(config, list):
            return [self._evaluate_config_templates(item, context) for item in config]

        elif isinstance(config, TemplateExpr):
            eval_context = EvalContext.from_operator_context(context)
            return config.evaluate(eval_context)

        else:
            return config


# 操作符注册表（向后兼容）
_operator_registry: Dict[str, Type[Operator]] = {}


def register_operator(operator_class: Type[Operator]) -> Type[Operator]:
    """注册操作符（类装饰器）

    用法:
        @register_operator
        class MyOperator(Operator):
            name = "my_operator"
            ...

    Args:
        operator_class: 操作符类

    Returns:
        Type[Operator]: 传入的操作符类（装饰器语法需要）
    """
    if not operator_class.name:
        raise ValueError(f"操作符 {operator_class.__name__} 必须定义name属性")

    _operator_registry[operator_class.name] = operator_class
    return operator_class


def get_operator_class(name: str) -> Optional[Type[Operator]]:
    """获取操作符类

    Args:
        name: 操作符名称

    Returns:
        Optional[Type[Operator]]: 操作符类，不存在则返回None
    """
    return _operator_registry.get(name)


def list_registered_operators() -> List[str]:
    """列出所有已注册的操作符名称

    Returns:
        List[str]: 操作符名称列表
    """
    return list(_operator_registry.keys())


def get_operators_by_type(op_type: OperatorType) -> List[Type[Operator]]:
    """获取指定类型的所有操作符

    Args:
        op_type: 操作符类型

    Returns:
        List[Type[Operator]]: 操作符类列表
    """
    return [op for op in _operator_registry.values() if op.operator_type == op_type]
