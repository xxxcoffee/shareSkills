"""词法分析器"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List, Optional


class TokenType(Enum):
    """词法单元类型"""
    CELL_REF = auto()       # Sheet1.A1
    CELL_RANGE = auto()     # Sheet1.A1:B10
    NUMBER = auto()         # 123, 3.14
    STRING = auto()         # "text"
    IDENTIFIER = auto()     # split, lookup
    PIPE = auto()           # |
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    COMMA = auto()          # ,
    EQUALS = auto()         # =
    PLUS = auto()           # +
    MINUS = auto()          # -
    COLON = auto()          # :
    IN = auto()             # in
    WHERE = auto()          # where
    COLUMN = auto()         # column
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    # 数学运算符
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    DOUBLE_STAR = auto()    # **
    # 比较运算符
    EQ = auto()             # ==
    NE = auto()             # !=
    LT = auto()             # <
    GT = auto()             # >
    LE = auto()             # <=
    GE = auto()             # >=
    # 模板语法
    DOLLAR = auto()         # $
    # 变量引用
    VAR_REF = auto()        # @value, @row.X, @var_name
    EOF = auto()            # 结束


@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: str
    position: int = 0


class Lexer:
    """词法分析器"""

    KEYWORDS = {
        'in': TokenType.IN,
        'where': TokenType.WHERE,
        'column': TokenType.COLUMN,
        'lookup': TokenType.IDENTIFIER,
    }

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def tokenize(self) -> List[Token]:
        """将文本转换为词法单元列表"""
        tokens = []
        while self.pos < self.length:
            char = self.text[self.pos]

            if char.isspace():
                self._skip_whitespace()
                continue

            if char.isdigit():
                tokens.append(self._read_number())
                continue

            if char == '"' or char == "'":
                tokens.append(self._read_string())
                continue

            if char.isalpha() or char == '_':
                token = self._read_identifier_or_cell_ref()
                tokens.append(token)
                continue

            if char == '@':
                token = self._read_var_ref()
                tokens.append(token)
                continue

            # 处理运算符（包括多字符运算符）
            operator_token = self._match_operator()
            if operator_token:
                tokens.append(operator_token)
                continue

            raise SyntaxError(f"Unexpected character '{char}' at position {self.pos}")

        tokens.append(Token(TokenType.EOF, '', self.pos))
        return tokens

    def _skip_whitespace(self) -> None:
        """跳过空白字符"""
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def _match_operator(self) -> Optional[Token]:
        """匹配运算符（包括多字符运算符）"""
        if self.pos >= self.length:
            return None

        char = self.text[self.pos]
        start = self.pos

        # 多字符运算符优先检查
        if self.pos + 1 < self.length:
            two_char = char + self.text[self.pos + 1]
            multi_char_ops = {
                '**': TokenType.DOUBLE_STAR,
                '==': TokenType.EQ,
                '!=': TokenType.NE,
                '<=': TokenType.LE,
                '>=': TokenType.GE,
            }
            if two_char in multi_char_ops:
                self.pos += 2
                return Token(multi_char_ops[two_char], two_char, start)

        # 单字符运算符
        single_tokens = {
            '|': TokenType.PIPE,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            ',': TokenType.COMMA,
            '=': TokenType.EQUALS,
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            ':': TokenType.COLON,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '$': TokenType.DOLLAR,
        }

        if char in single_tokens:
            self.pos += 1
            return Token(single_tokens[char], char, start)

        return None

    def _read_number(self) -> Token:
        """读取数字"""
        start = self.pos
        has_dot = False

        while self.pos < self.length:
            char = self.text[self.pos]
            if char.isdigit():
                self.pos += 1
            elif char == '.' and not has_dot:
                has_dot = True
                self.pos += 1
            else:
                break

        return Token(TokenType.NUMBER, self.text[start:self.pos], start)

    def _read_string(self) -> Token:
        """读取字符串"""
        start = self.pos
        quote = self.text[self.pos]
        self.pos += 1

        while self.pos < self.length and self.text[self.pos] != quote:
            if self.text[self.pos] == '\\' and self.pos + 1 < self.length:
                self.pos += 2
            else:
                self.pos += 1

        if self.pos >= self.length:
            raise SyntaxError(f"Unterminated string at position {start}")

        value = self.text[start + 1:self.pos]
        self.pos += 1

        return Token(TokenType.STRING, value, start)

    def _read_identifier_or_cell_ref(self) -> Token:
        """读取标识符或单元格引用"""
        start = self.pos

        while self.pos < self.length:
            char = self.text[self.pos]
            if char.isalnum() or char in '_':
                self.pos += 1
            elif char == '.':
                # 检查是否是单元格引用 (Sheet.A1 或 Sheet.A1:B10)
                self.pos += 1
                if self.pos < self.length:
                    next_char = self.text[self.pos]
                    if next_char.isalpha() or next_char == '$':
                        return self._read_cell_ref(start)
                # 不是单元格引用，回退
                self.pos -= 1
                break
            else:
                break

        value = self.text[start:self.pos]
        token_type = self.KEYWORDS.get(value.lower(), TokenType.IDENTIFIER)
        return Token(token_type, value, start)

    def _read_cell_ref(self, start: int) -> Token:
        """读取单元格引用"""
        # Sheet名已经被读取
        while self.pos < self.length and self.text[self.pos].isalpha():
            self.pos += 1

        while self.pos < self.length and self.text[self.pos].isdigit():
            self.pos += 1

        # 检查是否是范围 (A1:B10)
        if self.pos < self.length and self.text[self.pos] == ':':
            self.pos += 1
            while self.pos < self.length and self.text[self.pos].isalpha():
                self.pos += 1
            while self.pos < self.length and self.text[self.pos].isdigit():
                self.pos += 1
            return Token(TokenType.CELL_RANGE, self.text[start:self.pos], start)

        return Token(TokenType.CELL_REF, self.text[start:self.pos], start)

    def _read_var_ref(self) -> Token:
        """读取变量引用 (@value, @row.X, @var_name)"""
        start = self.pos
        self.pos += 1  # 跳过 @

        # 读取变量名（支持字母、数字、下划线和点号）
        while self.pos < self.length:
            char = self.text[self.pos]
            if char.isalnum() or char in '_.':
                self.pos += 1
            else:
                break

        value = self.text[start:self.pos]
        if len(value) < 2:  # 只有 @，没有变量名
            raise SyntaxError(f"Invalid variable reference at position {start}")

        return Token(TokenType.VAR_REF, value, start)
