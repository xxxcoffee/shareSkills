"""Pipeline执行引擎

负责操作符的编排和顺序执行，管理状态更新和错误处理。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from echecker.operators.base import (
    Operator,
    OperatorContext,
    OperatorResult,
    OperatorType,
)
from echecker.operators.registry import OperatorRegistry, get_registry


@dataclass
class PipelineStep:
    """Pipeline步骤

    定义Pipeline中的一个执行步骤。

    Attributes:
        operator_name: 操作符名称
        config: 操作符配置
        condition: 执行条件（可选），返回True时执行
        skip_on_error: 出错时是否跳过继续执行后续步骤
    """
    operator_name: str
    config: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Callable[[OperatorContext], bool]] = None
    skip_on_error: bool = False

    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class PipelineResult:
    """Pipeline执行结果

    Attributes:
        success: 是否成功执行
        final_output: 最终输出数据
        step_results: 每个步骤的执行结果
        errors: 所有错误消息
        state: 最终Pipeline状态
    """
    success: bool
    final_output: Any = None
    step_results: List[OperatorResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.step_results is None:
            self.step_results = []
        if self.errors is None:
            self.errors = []
        if self.state is None:
            self.state = {}

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0 or not self.success

    @property
    def step_count(self) -> int:
        """执行的步骤数"""
        return len(self.step_results)


class Pipeline:
    """Pipeline执行引擎

    负责按顺序执行操作符，管理状态传递和错误处理。

    示例:
        # 创建Pipeline
        pipeline = Pipeline()

        # 添加步骤
        pipeline.add_step("filter_empty")
        pipeline.add_step("transform_upper", config={"field": "name"})
        pipeline.add_step("validate_format", config={"pattern": r"^\\d+$"})

        # 执行Pipeline
        context = OperatorContext(
            excel_path=Path("data.xlsx"),
            current_sheet="Sheet1",
            current_cell="A1",
            current_row=1,
            current_col=1
        )
        result = pipeline.execute("initial_data", context)

        if result.success:
            print(f"最终结果: {result.final_output}")
        else:
            print(f"错误: {result.errors}")
    """

    def __init__(self, registry: Optional[OperatorRegistry] = None):
        """初始化Pipeline

        Args:
            registry: 操作符注册中心，默认使用全局注册中心
        """
        self._steps: List[PipelineStep] = []
        self._registry = registry or get_registry()

    def add_step(
        self,
        operator_name: str,
        config: Optional[Dict[str, Any]] = None,
        condition: Optional[Callable[[OperatorContext], bool]] = None,
        skip_on_error: bool = False
    ) -> "Pipeline":
        """添加执行步骤（链式调用）

        Args:
            operator_name: 操作符名称
            config: 操作符配置
            condition: 执行条件，返回True时执行此步骤
            skip_on_error: 出错时是否跳过继续执行

        Returns:
            Pipeline: self（支持链式调用）

        Raises:
            ValueError: 操作符不存在
        """
        if not self._registry.has(operator_name):
            raise ValueError(f"操作符 '{operator_name}' 未注册")

        step = PipelineStep(
            operator_name=operator_name,
            config=config or {},
            condition=condition,
            skip_on_error=skip_on_error
        )
        self._steps.append(step)
        return self

    def add_steps(self, *steps: PipelineStep) -> "Pipeline":
        """批量添加步骤

        Args:
            *steps: 步骤列表

        Returns:
            Pipeline: self
        """
        for step in steps:
            if not self._registry.has(step.operator_name):
                raise ValueError(f"操作符 '{step.operator_name}' 未注册")
        self._steps.extend(steps)
        return self

    def insert_step(
        self,
        index: int,
        operator_name: str,
        config: Optional[Dict[str, Any]] = None,
        condition: Optional[Callable[[OperatorContext], bool]] = None,
        skip_on_error: bool = False
    ) -> "Pipeline":
        """在指定位置插入步骤

        Args:
            index: 插入位置
            operator_name: 操作符名称
            config: 操作符配置
            condition: 执行条件
            skip_on_error: 出错时是否跳过

        Returns:
            Pipeline: self
        """
        if not self._registry.has(operator_name):
            raise ValueError(f"操作符 '{operator_name}' 未注册")

        step = PipelineStep(
            operator_name=operator_name,
            config=config or {},
            condition=condition,
            skip_on_error=skip_on_error
        )
        self._steps.insert(index, step)
        return self

    def remove_step(self, index: int) -> "Pipeline":
        """移除指定位置的步骤

        Args:
            index: 步骤索引

        Returns:
            Pipeline: self
        """
        if 0 <= index < len(self._steps):
            del self._steps[index]
        return self

    def clear_steps(self) -> "Pipeline":
        """清除所有步骤

        Returns:
            Pipeline: self
        """
        self._steps.clear()
        return self

    def get_steps(self) -> List[PipelineStep]:
        """获取所有步骤

        Returns:
            List[PipelineStep]: 步骤列表
        """
        return self._steps.copy()

    def step_count(self) -> int:
        """获取步骤数量"""
        return len(self._steps)

    def execute(
        self,
        initial_data: Any,
        context: OperatorContext,
        stop_on_error: bool = True
    ) -> PipelineResult:
        """执行Pipeline

        按顺序执行所有步骤，将每个步骤的输出作为下一个步骤的输入。

        Args:
            initial_data: 初始输入数据
            context: 操作符执行上下文
            stop_on_error: 遇到错误时是否停止执行

        Returns:
            PipelineResult: 执行结果
        """
        if not self._steps:
            return PipelineResult(
                success=True,
                final_output=initial_data,
                state=context._pipeline_state.copy()
            )

        current_data = initial_data
        step_results: List[OperatorResult] = []
        all_errors: List[str] = []
        success = True

        for i, step in enumerate(self._steps):
            # 检查执行条件
            if step.condition is not None:
                try:
                    should_execute = step.condition(context)
                except Exception as e:
                    error_msg = f"步骤 {i+1} ({step.operator_name}) 条件判断失败: {e}"
                    all_errors.append(error_msg)
                    if stop_on_error and not step.skip_on_error:
                        success = False
                        break
                    continue

                if not should_execute:
                    # 跳过此步骤
                    continue

            # 获取操作符实例
            operator = self._registry.get_instance(step.operator_name)
            if operator is None:
                error_msg = f"步骤 {i+1}: 操作符 '{step.operator_name}' 未找到"
                all_errors.append(error_msg)
                if stop_on_error and not step.skip_on_error:
                    success = False
                    break
                continue

            # 执行操作符
            try:
                result = operator.execute(current_data, context, step.config)
                step_results.append(result)

                # 更新状态
                if result.state_updates:
                    context.update_state(result.state_updates)

                # 处理结果
                if not result.success:
                    all_errors.extend(result.errors)
                    if stop_on_error and not step.skip_on_error:
                        success = False
                        break

                # 检查是否跳过后续步骤
                if result.skip_following:
                    break

                # 传递数据给下一步
                current_data = result.output

            except Exception as e:
                error_msg = f"步骤 {i+1} ({step.operator_name}) 执行异常: {e}"
                all_errors.append(error_msg)
                if stop_on_error and not step.skip_on_error:
                    success = False
                    break

        return PipelineResult(
            success=success and len(all_errors) == 0,
            final_output=current_data,
            step_results=step_results,
            errors=all_errors,
            state=context._pipeline_state.copy()
        )

    def execute_batch(
        self,
        data_list: List[Any],
        context_factory: Callable[[int, Any], OperatorContext],
        stop_on_error: bool = True
    ) -> List[PipelineResult]:
        """批量执行Pipeline

        对多个数据项执行相同的Pipeline。

        Args:
            data_list: 数据列表
            context_factory: 上下文工厂函数，接收索引和数据，返回上下文
            stop_on_error: 遇到错误时是否停止

        Returns:
            List[PipelineResult]: 每个数据项的执行结果
        """
        results = []
        for i, data in enumerate(data_list):
            context = context_factory(i, data)
            result = self.execute(data, context, stop_on_error)
            results.append(result)
        return results

    def __len__(self) -> int:
        """返回步骤数量"""
        return len(self._steps)

    def __repr__(self) -> str:
        step_names = [s.operator_name for s in self._steps]
        return f"Pipeline({', '.join(step_names)})"


class PipelineBuilder:
    """Pipeline构建器

    提供流畅的API构建Pipeline。

    示例:
        pipeline = (
            PipelineBuilder()
            .add("filter_empty")
            .add("transform_upper", config={"field": "name"})
            .add("validate_format", config={"pattern": r"^\\d+$"})
            .build()
        )
    """

    def __init__(self, registry: Optional[OperatorRegistry] = None):
        self._registry = registry or get_registry()
        self._pipeline = Pipeline(registry)

    def add(
        self,
        operator_name: str,
        config: Optional[Dict[str, Any]] = None,
        condition: Optional[Callable[[OperatorContext], bool]] = None,
        skip_on_error: bool = False
    ) -> "PipelineBuilder":
        """添加步骤

        Args:
            operator_name: 操作符名称
            config: 操作符配置
            condition: 执行条件
            skip_on_error: 出错时是否跳过

        Returns:
            PipelineBuilder: self
        """
        self._pipeline.add_step(operator_name, config, condition, skip_on_error)
        return self

    def add_if(
        self,
        condition: Callable[[OperatorContext], bool],
        operator_name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> "PipelineBuilder":
        """条件添加步骤

        Args:
            condition: 执行条件
            operator_name: 操作符名称
            config: 操作符配置

        Returns:
            PipelineBuilder: self
        """
        self._pipeline.add_step(operator_name, config, condition)
        return self

    def build(self) -> Pipeline:
        """构建Pipeline

        Returns:
            Pipeline: 构建好的Pipeline
        """
        return self._pipeline
