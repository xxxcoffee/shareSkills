"""AST节点定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


class ASTNode(ABC):
    """AST节点基类"""

    @abstractmethod
    def accept(self, visitor):
        pass


@dataclass
class CellRefNode(ASTNode):
    """单元格引用节点"""
    sheet: str
    cell: str

    def accept(self, visitor):
        return visitor.visit_cell_ref(self)


@dataclass
class CellRangeNode(ASTNode):
    """单元格范围节点"""
    sheet: str
    start: str
    end: str

    def accept(self, visitor):
        return visitor.visit_cell_range(self)


@dataclass
class LiteralNode(ASTNode):
    """字面量节点"""
    value: Any

    def accept(self, visitor):
        return visitor.visit_literal(self)


@dataclass
class BinaryOpNode(ASTNode):
    """二元操作节点"""
    op: str
    left: ASTNode
    right: ASTNode

    def accept(self, visitor):
        return visitor.visit_binary_op(self)


@dataclass
class UnaryOpNode(ASTNode):
    """一元操作节点"""
    op: str
    operand: ASTNode

    def accept(self, visitor):
        return visitor.visit_unary_op(self)


@dataclass
class PipeNode(ASTNode):
    """管道操作节点 (|)"""
    source: ASTNode
    func_name: str
    args: List[Any] = field(default_factory=list)

    def accept(self, visitor):
        return visitor.visit_pipe(self)


@dataclass
class LookupNode(ASTNode):
    """查找操作节点"""
    sheet: str
    column: int
    conditions: Dict[str, ASTNode] = field(default_factory=dict)

    def accept(self, visitor):
        return visitor.visit_lookup(self)


@dataclass
class InConditionNode(ASTNode):
    """IN条件节点"""
    column: Union[int, str]
    values: ASTNode

    def accept(self, visitor):
        return visitor.visit_in_condition(self)


@dataclass
class ArrayNode(ASTNode):
    """数组节点"""
    elements: List[ASTNode] = field(default_factory=list)

    def accept(self, visitor):
        return visitor.visit_array(self)


@dataclass
class FunctionCallNode(ASTNode):
    """函数调用节点"""
    func_name: str
    args: List[ASTNode] = field(default_factory=list)

    def accept(self, visitor):
        return visitor.visit_function_call(self)


@dataclass
class TemplateStringNode(ASTNode):
    """模板字符串节点 ${...}"""
    parts: List[Union[str, ASTNode]] = field(default_factory=list)

    def accept(self, visitor):
        return visitor.visit_template_string(self)
