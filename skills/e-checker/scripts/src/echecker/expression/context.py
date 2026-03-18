"""表达式求值上下文

提供模板表达式求值所需的变量解析功能。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EvalContext:
    """表达式求值上下文

    提供模板表达式求值时所需的变量解析功能，支持：
    - @value: 当前单元格值
    - @row.X: 同行其他列的值
    - @var_name: 自定义变量

    Attributes:
        cell_value: 当前单元格值，对应 @value
        row_data: 行数据字典，对应 @row.X
        variables: 变量字典，对应 @var_name
    """

    cell_value: Any = None
    row_data: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.row_data is None:
            self.row_data = {}
        if self.variables is None:
            self.variables = {}

    def resolve(self, name: str) -> Any:
        """解析变量引用

        支持以下语法：
        - @value: 返回当前单元格值
        - @row.X: 返回同行X列的值
        - @var_name: 返回变量字典中的值

        Args:
            name: 变量引用字符串，必须以 @ 开头

        Returns:
            Any: 解析后的值，如果变量不存在则返回 None

        Examples:
            >>> ctx = EvalContext(cell_value="hello", row_data={"A": 1, "B": 2})
            >>> ctx.resolve("@value")
            'hello'
            >>> ctx.resolve("@row.A")
            1
            >>> ctx.resolve("@foo", {"foo": "bar"})
            'bar'
        """
        if not name.startswith("@"):
            return name

        var_path = name[1:]  # 去掉 @ 前缀

        # @value -> 当前单元格值
        if var_path == "value":
            return self.cell_value

        # @row.X -> 行数据
        if var_path.startswith("row."):
            col_ref = var_path[4:]  # 去掉 "row." 前缀
            return self._get_row_value(col_ref)

        # @var_name -> 变量
        return self.variables.get(var_path)

    def _get_row_value(self, col_ref: str) -> Any:
        """获取同行指定列的值

        Args:
            col_ref: 列引用，如 "A", "B", "AA"

        Returns:
            Any: 列值，如果不存在则返回 None
        """
        # 标准化列引用（转为大写）
        col_ref = col_ref.upper()
        return self.row_data.get(col_ref)

    def get_row_value(self, col_ref: str) -> Any:
        """获取同行其他列的值（公共方法）

        Args:
            col_ref: 列引用，如 "A" 或 "@row.A"

        Returns:
            Any: 列值
        """
        if col_ref.startswith("@row."):
            col_ref = col_ref[5:]
        return self._get_row_value(col_ref)

    def get_variable(self, name: str) -> Any:
        """获取变量值

        Args:
            name: 变量名（不含 @ 前缀）

        Returns:
            Any: 变量值，不存在则返回 None
        """
        return self.variables.get(name)

    def set_variable(self, name: str, value: Any) -> None:
        """设置变量值

        Args:
            name: 变量名（不含 @ 前缀）
            value: 变量值
        """
        self.variables[name] = value

    @classmethod
    def from_operator_context(cls, op_context: Any) -> "EvalContext":
        """从 OperatorContext 创建 EvalContext

        用于与现有的 Pipeline/Operator 系统集成。

        Args:
            op_context: OperatorContext 实例

        Returns:
            EvalContext: 新的求值上下文
        """
        return cls(
            cell_value=getattr(op_context, "cell_value", None),
            row_data=getattr(op_context, "row_data", {}),
            variables=getattr(op_context, "pipeline_state", {}),
        )
