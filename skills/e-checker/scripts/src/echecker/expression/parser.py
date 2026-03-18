"""表达式解析器"""

import re
from typing import List, Optional, Union

from echecker.expression.lexer import Lexer, Token, TokenType
from echecker.expression.ast_nodes import (
    ASTNode, CellRefNode, CellRangeNode, LiteralNode,
    BinaryOpNode, UnaryOpNode, PipeNode, LookupNode, ArrayNode,
    InConditionNode, FunctionCallNode, TemplateStringNode
)


class ExpressionParser:
    """表达式解析器 - 将词法单元转换为AST

    支持完整的数学表达式语法，运算符优先级（从高到低）：
    1. 括号 ()
    2. 幂运算 **
    3. 一元正负号 +x, -x
    4. 乘除取模 *, /, %
    5. 加减 +, -
    6. 比较 ==, !=, <, >, <=, >=
    7. 管道 |
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    @classmethod
    def parse(cls, text: str) -> ASTNode:
        """从文本解析表达式"""
        # 检查是否是模板字符串
        if '${' in text:
            return cls.parse_template(text)

        lexer = Lexer(text)
        tokens = lexer.tokenize()
        parser = cls(tokens)
        return parser.parse_expression()

    @classmethod
    def parse_template(cls, text: str) -> ASTNode:
        """解析模板字符串，支持 ${...} 语法"""
        parts: List[Union[str, ASTNode]] = []
        i = 0
        pattern = re.compile(r'\$\{([^}]+)\}')

        for match in pattern.finditer(text):
            # 添加匹配前的文本
            if match.start() > i:
                parts.append(text[i:match.start()])

            # 解析 ${...} 中的表达式
            expr_text = match.group(1)
            lexer = Lexer(expr_text)
            tokens = lexer.tokenize()
            parser = cls(tokens)
            expr_node = parser.parse_expression()
            parts.append(expr_node)

            i = match.end()

        # 添加剩余的文本
        if i < len(text):
            parts.append(text[i:])

        return TemplateStringNode(parts=parts)

    def current(self) -> Token:
        """获取当前词法单元"""
        return self.tokens[self.pos]

    def peek(self, offset: int = 0) -> Token:
        """查看指定位置的词法单元"""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]

    def consume(self, expected_type: Optional[TokenType] = None) -> Token:
        """消费当前词法单元"""
        token = self.current()
        if expected_type and token.type != expected_type:
            raise SyntaxError(f"Expected {expected_type}, got {token.type}")
        self.pos += 1
        return token

    def match(self, *types: TokenType) -> bool:
        """检查当前词法单元是否匹配给定类型"""
        return self.current().type in types

    def parse_expression(self) -> ASTNode:
        """解析表达式（比较运算符优先级最低）"""
        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        """解析比较表达式: ==, !=, <, >, <=, >="""
        left = self.parse_additive()

        while self.match(TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_token = self.consume()
            op = op_token.value
            right = self.parse_additive()
            left = BinaryOpNode(op=op, left=left, right=right)

        return left

    def parse_additive(self) -> ASTNode:
        """解析加减法表达式: +, -"""
        left = self.parse_multiplicative()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.consume().value
            right = self.parse_multiplicative()
            left = BinaryOpNode(op=op, left=left, right=right)

        return left

    def parse_multiplicative(self) -> ASTNode:
        """解析乘除模表达式: *, /, %"""
        left = self.parse_unary()

        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.consume().value
            right = self.parse_unary()
            left = BinaryOpNode(op=op, left=left, right=right)

        return left

    def parse_unary(self) -> ASTNode:
        """解析一元表达式: +x, -x"""
        if self.match(TokenType.PLUS, TokenType.MINUS):
            op = self.consume().value
            operand = self.parse_unary()
            return UnaryOpNode(op=op, operand=operand)

        return self.parse_power()

    def parse_power(self) -> ASTNode:
        """解析幂运算表达式: ** (右结合)"""
        left = self.parse_postfix()

        if self.match(TokenType.DOUBLE_STAR):
            op = self.consume().value
            right = self.parse_power()  # 右递归实现右结合
            return BinaryOpNode(op=op, left=left, right=right)

        return left

    def parse_postfix(self) -> ASTNode:
        """解析后缀表达式: 函数调用、管道等"""
        left = self.parse_primary()

        while True:
            # 函数调用: func(args)
            if self.match(TokenType.LPAREN) and isinstance(left, LiteralNode) and isinstance(left.value, str):
                left = self.parse_function_call(left.value)
            # 管道操作: expr | func(args)
            elif self.match(TokenType.PIPE):
                left = self.parse_pipe(left)
            else:
                break

        return left

    def parse_function_call(self, func_name: str) -> FunctionCallNode:
        """解析函数调用: func_name(args)"""
        self.consume(TokenType.LPAREN)
        args = []

        if not self.match(TokenType.RPAREN):
            args = self.parse_expression_args()

        self.consume(TokenType.RPAREN)
        return FunctionCallNode(func_name=func_name, args=args)

    def parse_expression_args(self) -> List[ASTNode]:
        """解析表达式参数列表（用于函数调用）"""
        args = [self.parse_expression()]

        while self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            args.append(self.parse_expression())

        return args

    def parse_pipe(self, source: ASTNode) -> PipeNode:
        """解析管道表达式: source | func(args)"""
        self.consume(TokenType.PIPE)
        func_name = self.consume(TokenType.IDENTIFIER).value

        args = []
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            if not self.match(TokenType.RPAREN):
                args = self.parse_literal_args()
            self.consume(TokenType.RPAREN)

        return PipeNode(source=source, func_name=func_name, args=args)

    def parse_primary(self) -> ASTNode:
        """解析基本表达式"""
        token = self.current()

        if token.type == TokenType.CELL_REF:
            return self.parse_cell_ref()

        if token.type == TokenType.CELL_RANGE:
            return self.parse_cell_range()

        if token.type == TokenType.NUMBER:
            self.consume()
            value = float(token.value) if '.' in token.value else int(token.value)
            return LiteralNode(value)

        if token.type == TokenType.STRING:
            self.consume()
            return LiteralNode(token.value)

        if token.type == TokenType.VAR_REF:
            # 变量引用 @value, @row.X, @var_name
            self.consume()
            return LiteralNode(token.value)

        if token.type == TokenType.IDENTIFIER:
            if token.value.lower() == 'lookup':
                return self.parse_lookup()
            self.consume()
            return LiteralNode(token.value)

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr

        raise SyntaxError(f"Unexpected token: {token}")

    def parse_cell_ref(self) -> CellRefNode:
        """解析单元格引用"""
        token = self.consume(TokenType.CELL_REF)
        parts = token.value.split('.')
        return CellRefNode(sheet=parts[0], cell=parts[1])

    def parse_cell_range(self) -> CellRangeNode:
        """解析单元格范围"""
        token = self.consume(TokenType.CELL_RANGE)
        parts = token.value.split('.')
        sheet = parts[0]
        range_parts = parts[1].split(':')
        return CellRangeNode(sheet=sheet, start=range_parts[0], end=range_parts[1])

    def parse_lookup(self) -> LookupNode:
        """解析lookup表达式: lookup(Sheet, column=N, where: {...})"""
        self.consume(TokenType.IDENTIFIER)  # 'lookup'
        self.consume(TokenType.LPAREN)

        sheet = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.COMMA)

        # column=3
        self.consume(TokenType.IDENTIFIER)  # 'column'
        self.consume(TokenType.EQUALS)
        column = int(self.consume(TokenType.NUMBER).value)

        conditions = {}

        if self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            self.consume(TokenType.IDENTIFIER)  # 'where'
            self.consume(TokenType.COLON)
            self.consume(TokenType.LBRACE)

            # 解析条件，如 column1 in (...)
            while not self.match(TokenType.RBRACE):
                col_spec = self.consume(TokenType.IDENTIFIER).value  # 'column1' 或 'column3'
                if col_spec.startswith('column'):
                    col_idx = int(col_spec[6:])
                else:
                    col_idx = col_spec

                self.consume(TokenType.IN)
                cond_value = self.parse_expression()
                conditions[col_idx] = cond_value

                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)

            self.consume(TokenType.RBRACE)

        self.consume(TokenType.RPAREN)

        return LookupNode(sheet=sheet, column=column, conditions=conditions)

    def parse_literal_args(self) -> List:
        """解析字面量参数列表（用于管道函数）"""
        args = []

        while True:
            if self.match(TokenType.STRING):
                args.append(self.consume(TokenType.STRING).value)
            elif self.match(TokenType.NUMBER):
                num_str = self.consume(TokenType.NUMBER).value
                args.append(float(num_str) if '.' in num_str else int(num_str))
            else:
                break

            if self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
            else:
                break

        return args
