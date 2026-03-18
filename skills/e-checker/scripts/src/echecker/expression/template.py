"""表达式模板系统

提供模板字符串解析和预编译功能，支持在配置中使用 ${...} 表达式。
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Match, Pattern, Tuple, Union

from echecker.expression.ast_nodes import ASTNode
from echecker.expression.parser import ExpressionParser
from echecker.expression.context import EvalContext


# 模板中的表达式模式: ${...}
TEMPLATE_PATTERN: Pattern = re.compile(r"\$\{([^}]+)\}")


@dataclass
class TemplateExpr:
    """表达式模板

    封装预编译的 AST，支持纯表达式和模板字符串。

    纯表达式: "@row.A + @row.B"
    模板字符串: "prefix_${@row.A}_suffix"

    Attributes:
        source: 原始模板字符串
        is_pure: 是否为纯表达式（不含模板前缀/后缀）
        ast: 纯表达式时的 AST 节点
        segments: 模板字符串时的分段列表
    """

    source: str
    is_pure: bool
    ast: Union[ASTNode, None] = None
    segments: Union[List[Tuple[str, Union[ASTNode, None]]], None] = None

    @classmethod
    def compile(cls, template: str) -> "TemplateExpr":
        """编译模板字符串为 TemplateExpr

        支持两种形式：
        1. 纯表达式: "@row.A + @row.B" -> is_pure=True, ast=ASTNode
        2. 模板字符串: "prefix_${@row.A}_suffix" -> is_pure=False, segments=[...]

        Args:
            template: 模板字符串

        Returns:
            TemplateExpr: 编译后的模板表达式对象

        Examples:
            >>> # 纯表达式
            >>> expr = TemplateExpr.compile("@row.A + 1")
            >>> expr.is_pure
            True

            >>> # 模板字符串
            >>> expr = TemplateExpr.compile("ID_${@row.A}")
            >>> expr.is_pure
            False
        """
        # 检查是否包含 ${...} 模式
        matches = list(TEMPLATE_PATTERN.finditer(template))

        if not matches:
            # 纯表达式，没有 ${...} 包装
            ast = ExpressionParser.parse(template)
            return cls(source=template, is_pure=True, ast=ast, segments=None)

        # 检查是否是纯 ${...} 包裹的表达式（即整个字符串就是一个 ${...}）
        if len(matches) == 1:
            match = matches[0]
            if match.start() == 0 and match.end() == len(template):
                # 整个字符串就是 ${...}，提取内部作为纯表达式
                inner_expr = match.group(1)
                ast = ExpressionParser.parse(inner_expr)
                return cls(source=template, is_pure=True, ast=ast, segments=None)

        # 模板字符串：包含多个 ${...} 或有前缀/后缀
        segments: List[Tuple[str, Union[ASTNode, None]]] = []
        last_end = 0

        for match in matches:
            # 添加前缀文本（如果有）
            if match.start() > last_end:
                prefix = template[last_end:match.start()]
                segments.append((prefix, None))

            # 编译表达式部分
            expr_text = match.group(1)
            ast = ExpressionParser.parse(expr_text)
            segments.append(("", ast))

            last_end = match.end()

        # 添加后缀文本（如果有）
        if last_end < len(template):
            suffix = template[last_end:]
            segments.append((suffix, None))

        return cls(source=template, is_pure=False, ast=None, segments=segments)

    def evaluate(self, context: EvalContext) -> Any:
        """求值模板表达式

        Args:
            context: 求值上下文，提供变量解析

        Returns:
            Any: 求值结果
            - 纯表达式：返回表达式求值结果
            - 模板字符串：返回拼接后的字符串

        Examples:
            >>> ctx = EvalContext(row_data={"A": "123", "B": "456"})
            >>> expr = TemplateExpr.compile("@row.A")
            >>> expr.evaluate(ctx)
            '123'

            >>> expr = TemplateExpr.compile("ID_${@row.A}")
            >>> expr.evaluate(ctx)
            'ID_123'
        """
        if self.is_pure:
            # 纯表达式求值
            if self.ast is None:
                raise ValueError("Pure expression has no AST")
            return self._evaluate_ast(self.ast, context)

        # 模板字符串求值
        if self.segments is None:
            raise ValueError("Template string has no segments")

        result_parts: List[str] = []
        for text, ast in self.segments:
            if text:
                result_parts.append(text)
            if ast:
                value = self._evaluate_ast(ast, context)
                result_parts.append(str(value) if value is not None else "")

        return "".join(result_parts)

    def _evaluate_ast(self, ast: ASTNode, context: EvalContext) -> Any:
        """求值 AST 节点

        使用 EvalContext 进行变量解析。

        Args:
            ast: AST 节点
            context: 求值上下文

        Returns:
            Any: 求值结果
        """
        from echecker.expression.ast_nodes import (
            LiteralNode, BinaryOpNode, UnaryOpNode,
            CellRefNode, CellRangeNode, PipeNode
        )

        # LiteralNode: 直接返回值
        if isinstance(ast, LiteralNode):
            # 检查是否是变量引用（以 @ 开头的字符串）
            if isinstance(ast.value, str) and ast.value.startswith("@"):
                return context.resolve(ast.value)
            return ast.value

        # BinaryOpNode: 二元操作
        if isinstance(ast, BinaryOpNode):
            left = self._evaluate_ast(ast.left, context)
            right = self._evaluate_ast(ast.right, context)

            if ast.op == "+":
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    return left + right
                return str(left) + str(right)
            elif ast.op == "-":
                return left - right
            elif ast.op == "*":
                return left * right
            elif ast.op == "/":
                return left / right if right != 0 else None

            raise ValueError(f"Unknown operator: {ast.op}")

        # UnaryOpNode: 一元操作
        if isinstance(ast, UnaryOpNode):
            operand = self._evaluate_ast(ast.operand, context)
            if ast.op == "-":
                return -operand
            raise ValueError(f"Unknown unary operator: {ast.op}")

        # CellRefNode: 单元格引用（暂不支持，返回 None）
        if isinstance(ast, CellRefNode):
            # TODO: 通过 context 获取外部数据
            return None

        # CellRangeNode: 单元格范围（暂不支持，返回 None）
        if isinstance(ast, CellRangeNode):
            # TODO: 通过 context 获取外部数据
            return None

        # PipeNode: 管道操作
        if isinstance(ast, PipeNode):
            source_value = self._evaluate_ast(ast.source, context)

            # 内置管道函数
            if ast.func_name == "split":
                delimiter = ast.args[0] if ast.args else "|"
                if source_value is None:
                    return []
                return str(source_value).split(delimiter)

            if ast.func_name == "strip":
                if source_value is None:
                    return ""
                return str(source_value).strip()

            if ast.func_name == "lower":
                if source_value is None:
                    return ""
                return str(source_value).lower()

            if ast.func_name == "upper":
                if source_value is None:
                    return ""
                return str(source_value).upper()

            raise ValueError(f"Unknown pipe function: {ast.func_name}")

        # 未知节点类型
        raise ValueError(f"Unknown AST node type: {type(ast)}")


class ConfigPreprocessor:
    """配置预处理器

    遍历配置字典，找到所有 ${...} 模板，预编译为 TemplateExpr 对象。

    设计说明：
    - 在配置加载阶段执行，将字符串模板替换为 TemplateExpr 对象
    - 支持嵌套字典和列表
    - 保持原始配置结构不变，只是替换值类型

    使用示例:
        >>> config = {
        ...     "target": "${@row.A}_${@row.B}",
        ...     "value": "${@value}",
        ...     "nested": {
        ...         "expr": "${@row.C + 1}"
        ...     },
        ...     "items": ["${@row.D}", "static"]
        ... }
        >>> preprocessor = ConfigPreprocessor()
        >>> processed = preprocessor.process(config)
        >>> # processed["target"] 现在是 TemplateExpr 对象
    """

    def __init__(self):
        """初始化预处理器"""
        self.compiled_count = 0

    def process(self, config: Any) -> Any:
        """处理配置数据，预编译所有模板字符串

        Args:
            config: 配置数据（可以是字典、列表或标量值）

        Returns:
            Any: 处理后的配置数据（保持相同结构）
        """
        if isinstance(config, dict):
            return {key: self.process(value) for key, value in config.items()}

        if isinstance(config, list):
            return [self.process(item) for item in config]

        if isinstance(config, str):
            if TEMPLATE_PATTERN.search(config):
                self.compiled_count += 1
                return TemplateExpr.compile(config)
            return config

        # 其他类型（数字、布尔等）保持不变
        return config

    def process_inplace(self, config: Dict) -> None:
        """就地处理配置字典

        直接修改传入的字典，不创建新对象。

        Args:
            config: 要处理的配置字典
        """
        for key, value in list(config.items()):
            if isinstance(value, dict):
                self.process_inplace(value)
            elif isinstance(value, list):
                config[key] = self._process_list(value)
            elif isinstance(value, str):
                if TEMPLATE_PATTERN.search(value):
                    self.compiled_count += 1
                    config[key] = TemplateExpr.compile(value)

    def _process_list(self, items: List) -> List:
        """处理列表中的模板字符串

        Args:
            items: 列表项

        Returns:
            List: 处理后的列表
        """
        result = []
        for item in items:
            if isinstance(item, dict):
                self.process_inplace(item)
                result.append(item)
            elif isinstance(item, list):
                result.append(self._process_list(item))
            elif isinstance(item, str):
                if TEMPLATE_PATTERN.search(item):
                    self.compiled_count += 1
                    result.append(TemplateExpr.compile(item))
                else:
                    result.append(item)
            else:
                result.append(item)
        return result


def is_template(value: Any) -> bool:
    """检查值是否是模板字符串

    Args:
        value: 要检查的值

    Returns:
        bool: 如果是包含 ${...} 的字符串则返回 True
    """
    return isinstance(value, str) and TEMPLATE_PATTERN.search(value) is not None


def evaluate_config_value(value: Any, context: EvalContext) -> Any:
    """求值配置值

    如果值是 TemplateExpr，则在给定上下文中求值；
    否则原样返回。

    Args:
        value: 配置值（可能是 TemplateExpr 或其他类型）
        context: 求值上下文

    Returns:
        Any: 求值结果
    """
    if isinstance(value, TemplateExpr):
        return value.evaluate(context)
    return value
