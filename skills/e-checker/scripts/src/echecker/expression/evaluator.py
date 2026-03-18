"""表达式求值器"""

import re
from typing import Any, Dict, List, Optional, Set, Callable

from echecker.expression.ast_nodes import (
    ASTNode, CellRefNode, CellRangeNode, LiteralNode,
    BinaryOpNode, UnaryOpNode, PipeNode, LookupNode,
    InConditionNode, ArrayNode, FunctionCallNode, TemplateStringNode
)
from echecker.expression.exceptions import (
    ExpressionTypeError,
    ExpressionZeroDivisionError,
    ExpressionNameError,
    ExpressionValueError,
)
from echecker.excel.provider import ExcelProvider
from echecker.types import ValidationContext


class ExpressionEvaluator:
    """表达式求值器

    支持数学运算、变量解析、内置函数调用。

    变量引用:
        - @value: 当前单元格值
        - @row.X: 同行X列的值
        - @var_name: Pipeline状态中的变量

    内置函数:
        - len(x): 返回列表/字符串长度
        - abs(x): 绝对值
        - max(a, b, ...): 最大值
        - min(a, b, ...): 最小值
        - sum(x): 求和
    """

    def __init__(self, provider: ExcelProvider, context: ValidationContext):
        self.provider = provider
        self.context = context
        self.variables: Dict[str, Any] = getattr(context, 'pipeline_state', {}) or {}
        self.row_data: Dict[str, Any] = getattr(context, 'row_data', {}) or {}
        self.cell_value: Any = getattr(context, 'cell_value', None)

        # 注册内置函数
        self._builtins: Dict[str, Callable] = {
            'len': self._builtin_len,
            'abs': self._builtin_abs,
            'max': self._builtin_max,
            'min': self._builtin_min,
            'sum': self._builtin_sum,
        }

    def evaluate(self, node: ASTNode) -> Any:
        """求值AST节点"""
        return node.accept(self)

    def visit_cell_ref(self, node: CellRefNode) -> Any:
        """访问单元格引用"""
        ref = f"{node.sheet}.{node.cell}"
        return self.provider.get_cell_value(ref)

    def visit_cell_range(self, node: CellRangeNode) -> List[Any]:
        """访问单元格范围"""
        ref = f"{node.sheet}.{node.start}:{node.end}"
        values = self.provider.get_range_values(ref)
        return list(values.values())

    def visit_literal(self, node: LiteralNode) -> Any:
        """访问字面量

        如果值是字符串且以 @ 开头，则作为变量引用解析。
        """
        value = node.value
        if isinstance(value, str) and value.startswith("@"):
            return self._resolve_variable(value)
        return value

    def _builtin_len(self, x: Any) -> int:
        """内置函数: len(x)"""
        if x is None:
            return 0
        if isinstance(x, (str, list, tuple, dict, set)):
            return len(x)
        raise ExpressionTypeError(f"len() 不支持类型: {type(x).__name__}")

    def _builtin_abs(self, x: Any) -> Any:
        """内置函数: abs(x)"""
        if x is None:
            raise ExpressionTypeError("abs() 参数不能为 None")
        if isinstance(x, (int, float)):
            return abs(x)
        raise ExpressionTypeError(f"abs() 要求数字类型，实际为: {type(x).__name__}")

    def _builtin_max(self, *args: Any) -> Any:
        """内置函数: max(a, b, ...)"""
        if not args:
            raise ExpressionValueError("max() 至少需要1个参数")
        # 如果传入单个可迭代对象
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            if not args[0]:
                raise ExpressionValueError("max() 参数不能为空序列")
            return max(args[0])
        return max(args)

    def _builtin_min(self, *args: Any) -> Any:
        """内置函数: min(a, b, ...)"""
        if not args:
            raise ExpressionValueError("min() 至少需要1个参数")
        # 如果传入单个可迭代对象
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            if not args[0]:
                raise ExpressionValueError("min() 参数不能为空序列")
            return min(args[0])
        return min(args)

    def _builtin_sum(self, x: Any) -> Any:
        """内置函数: sum(x)"""
        if x is None:
            raise ExpressionTypeError("sum() 参数不能为 None")
        if isinstance(x, (list, tuple)):
            if not x:
                return 0
            return sum(x)
        raise ExpressionTypeError(f"sum() 要求可迭代对象，实际为: {type(x).__name__}")

    def _is_number(self, value: Any) -> bool:
        """检查值是否为数字类型"""
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _ensure_number(self, value: Any, context: str) -> None:
        """确保值为数字类型，否则抛出类型错误"""
        if not self._is_number(value):
            raise ExpressionTypeError(f"{context} 要求数字类型，实际为: {type(value).__name__}")

    def _resolve_variable(self, var_ref: str) -> Any:
        """解析变量引用

        支持:
            - @value: 当前单元格值
            - @row.X: 同行X列的值
            - @var_name: Pipeline状态中的变量

        Args:
            var_ref: 变量引用字符串 (如 "@value", "@row.H")

        Returns:
            Any: 解析后的值

        Raises:
            ExpressionNameError: 变量未定义
        """
        if not var_ref.startswith("@"):
            return var_ref

        # @value -> 当前值
        if var_ref == "@value":
            return self.cell_value

        # @row.X -> 行数据
        if var_ref.startswith("@row."):
            col_ref = var_ref[5:].upper()
            if col_ref in self.row_data:
                return self.row_data[col_ref]
            raise ExpressionNameError(f"未定义的列引用: {var_ref}")

        # @var_name -> Pipeline状态变量
        var_name = var_ref[1:]
        if var_name in self.variables:
            return self.variables[var_name]
        raise ExpressionNameError(f"未定义的变量: {var_ref}")

    def visit_binary_op(self, node: BinaryOpNode) -> Any:
        """访问二元操作

        支持的运算符:
            - 算术: +, -, *, /, %, **
            - 比较: ==, !=, <, >, <=, >=

        严格类型检查:
            - 算术运算要求操作数为数字类型
            - 比较运算要求类型兼容
        """
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)

        # 算术运算符
        if node.op == '+':
            # 字符串拼接或列表拼接
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            # 数字相加
            self._ensure_number(left, "加法左操作数")
            self._ensure_number(right, "加法右操作数")
            return left + right

        if node.op == '-':
            self._ensure_number(left, "减法左操作数")
            self._ensure_number(right, "减法右操作数")
            return left - right

        if node.op == '*':
            self._ensure_number(left, "乘法左操作数")
            self._ensure_number(right, "乘法右操作数")
            return left * right

        if node.op == '/':
            self._ensure_number(left, "除法左操作数")
            self._ensure_number(right, "除法右操作数")
            if right == 0:
                raise ExpressionZeroDivisionError("除零错误")
            return left / right

        if node.op == '%':
            self._ensure_number(left, "取模左操作数")
            self._ensure_number(right, "取模右操作数")
            if right == 0:
                raise ExpressionZeroDivisionError("取模除零错误")
            return left % right

        if node.op == '**':
            self._ensure_number(left, "幂运算左操作数")
            self._ensure_number(right, "幂运算右操作数")
            return left ** right

        # 比较运算符
        if node.op == '==':
            return left == right

        if node.op == '!=':
            return left != right

        if node.op == '<':
            self._ensure_number(left, "小于比较左操作数")
            self._ensure_number(right, "小于比较右操作数")
            return left < right

        if node.op == '>':
            self._ensure_number(left, "大于比较左操作数")
            self._ensure_number(right, "大于比较右操作数")
            return left > right

        if node.op == '<=':
            self._ensure_number(left, "小于等于比较左操作数")
            self._ensure_number(right, "小于等于比较右操作数")
            return left <= right

        if node.op == '>=':
            self._ensure_number(left, "大于等于比较左操作数")
            self._ensure_number(right, "大于等于比较右操作数")
            return left >= right

        raise ExpressionValueError(f"未知运算符: {node.op}")

    def visit_unary_op(self, node: UnaryOpNode) -> Any:
        """访问一元操作

        支持的运算符:
            - -: 取负（要求数字类型）
            - +: 取正（要求数字类型）
            - not: 逻辑非
        """
        operand = self.evaluate(node.operand)

        if node.op == '-':
            self._ensure_number(operand, "取负操作数")
            return -operand

        if node.op == '+':
            self._ensure_number(operand, "取正操作数")
            return +operand

        if node.op == 'not':
            return not operand

        raise ExpressionValueError(f"未知一元运算符: {node.op}")

    def visit_pipe(self, node: PipeNode) -> Any:
        """访问管道操作

        支持内置函数:
            - split(delimiter): 按分隔符分割字符串
            - strip: 去除首尾空白
            - lower: 转换为小写
            - upper: 转换为大写
            - len: 返回列表/字符串长度
            - abs: 绝对值
            - max: 最大值
            - min: 最小值
            - sum: 求和
        """
        source_value = self.evaluate(node.source)

        # 字符串处理函数
        if node.func_name == 'split':
            delimiter = node.args[0] if node.args else '|'
            if source_value is None:
                return []
            return str(source_value).split(delimiter)

        if node.func_name == 'strip':
            if source_value is None:
                return ''
            return str(source_value).strip()

        if node.func_name == 'lower':
            if source_value is None:
                return ''
            return str(source_value).lower()

        if node.func_name == 'upper':
            if source_value is None:
                return ''
            return str(source_value).upper()

        # 内置数学函数
        if node.func_name == 'len':
            return self._builtin_len(source_value)

        if node.func_name == 'abs':
            return self._builtin_abs(source_value)

        if node.func_name == 'sum':
            return self._builtin_sum(source_value)

        if node.func_name == 'max':
            # max可以接受额外参数
            args = [source_value]
            if node.args:
                args.extend(node.args)
            return self._builtin_max(*args)

        if node.func_name == 'min':
            # min可以接受额外参数
            args = [source_value]
            if node.args:
                args.extend(node.args)
            return self._builtin_min(*args)

        raise ExpressionValueError(f"未知管道函数: {node.func_name}")

    def visit_lookup(self, node: LookupNode) -> Any:
        """访问lookup操作"""
        # 获取目标sheet的所有行
        max_row, max_col = self.provider.get_sheet_dimensions(node.sheet)

        for row in range(1, max_row + 1):
            match = True

            for col, condition_node in node.conditions.items():
                col_idx = int(col) if isinstance(col, (int, str)) and str(col).isdigit() else col
                if isinstance(col_idx, int):
                    cell_value = self.provider.get_cell_value(f"{node.sheet}.{self._col_letter(col_idx)}{row}")
                else:
                    continue

                condition_value = self.evaluate(condition_node)

                # 检查条件是否满足
                if isinstance(condition_value, list):
                    if cell_value not in condition_value:
                        match = False
                        break
                else:
                    if cell_value != condition_value:
                        match = False
                        break

            if match:
                result_col = self._col_letter(node.column)
                return self.provider.get_cell_value(f"{node.sheet}.{result_col}{row}")

        return None

    def visit_in_condition(self, node: InConditionNode) -> bool:
        """访问IN条件"""
        values = self.evaluate(node.values)

        if isinstance(node.column, int):
            col_letter = self._col_letter(node.column)
            cell_value = self.provider.get_cell_value(f"{self.context.current_sheet}.{col_letter}{self.context.current_row}")
        else:
            cell_value = None

        if isinstance(values, list):
            return cell_value in values
        return cell_value == values

    def visit_array(self, node: ArrayNode) -> List[Any]:
        """访问数组"""
        return [self.evaluate(elem) for elem in node.elements]

    def visit_function_call(self, node: FunctionCallNode) -> Any:
        """访问函数调用

        支持内置函数:
            - len(x): 返回列表/字符串长度
            - abs(x): 绝对值
            - max(a, b, ...): 最大值
            - min(a, b, ...): 最小值
            - sum(x): 求和
        """
        # 求值所有参数
        args = [self.evaluate(arg) for arg in node.args]

        func_name = node.func_name.lower()

        if func_name not in self._builtins:
            raise ExpressionNameError(f"未知函数: {node.func_name}")

        func = self._builtins[func_name]
        return func(*args)

    def visit_template_string(self, node: TemplateStringNode) -> str:
        """访问模板字符串

        将模板字符串的各个部分求值并拼接。
        文本部分保持不变，表达式部分求值后转为字符串。
        """
        result_parts = []

        for part in node.parts:
            if isinstance(part, str):
                # 文本部分直接添加
                result_parts.append(part)
            else:
                # 表达式部分求值并转为字符串
                value = self.evaluate(part)
                if value is not None:
                    result_parts.append(str(value))
                else:
                    result_parts.append('')

        return ''.join(result_parts)

    @staticmethod
    def _col_letter(col: int) -> str:
        """将列号转换为字母"""
        result = ""
        c = col
        while c > 0:
            c, rem = divmod(c - 1, 26)
            result = chr(65 + rem) + result
        return result
