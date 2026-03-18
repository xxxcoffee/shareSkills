"""单元格引用解析"""

import re
from dataclasses import dataclass
from typing import Iterator, List, Optional, Tuple, Union


@dataclass
class CellRef:
    """单元格引用"""
    sheet: str
    row: int
    col: int

    def __str__(self) -> str:
        col_str = self._col_to_letter(self.col)
        return f"{self.sheet}.{col_str}{self.row}"

    @staticmethod
    def _col_to_letter(col: int) -> str:
        """将列号转换为字母 (1 -> A, 27 -> AA)"""
        result = ""
        col = col
        while col > 0:
            col, rem = divmod(col - 1, 26)
            result = chr(65 + rem) + result
        return result

    @staticmethod
    def _letter_to_col(letter: str) -> int:
        """将列字母转换为号 (A -> 1, AA -> 27)"""
        result = 0
        for char in letter.upper():
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result

    @classmethod
    def from_string(cls, ref: str) -> "CellRef":
        """从字符串解析单元格引用"""
        parts = ref.split('.')
        if len(parts) != 2:
            raise ValueError(f"无效的单元格引用: {ref}")

        sheet = parts[0]
        cell = parts[1]

        match = re.match(r'^([A-Z]+)(\d+)$', cell, re.IGNORECASE)
        if not match:
            raise ValueError(f"无效的单元格地址: {cell}")

        col_letter, row_str = match.groups()
        row = int(row_str)
        col = cls._letter_to_col(col_letter)

        return cls(sheet=sheet, row=row, col=col)


@dataclass
class CellRange:
    """单元格范围"""
    sheet: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    _dynamic_end_row: bool = False  # 标记是否为动态末尾（运行时确定）

    def __str__(self) -> str:
        start = CellRef._col_to_letter(None, self.start_col) + str(self.start_row)
        end = CellRef._col_to_letter(None, self.end_col) + str(self.end_row)
        return f"{self.sheet}.{start}:{end}"

    @staticmethod
    def _col_to_letter(_, col: int) -> str:
        """静态方法版本的列号转字母"""
        result = ""
        c = col
        while c > 0:
            c, rem = divmod(c - 1, 26)
            result = chr(65 + rem) + result
        return result

    @classmethod
    def from_string(cls, ref: str) -> "CellRange":
        """从字符串解析单元格范围"""
        parts = ref.split('.')
        if len(parts) != 2:
            raise ValueError(f"无效的单元格范围: {ref}")

        sheet = parts[0]
        range_str = parts[1]

        if ':' not in range_str:
            raise ValueError(f"范围必须包含冒号: {ref}")

        start_cell, end_cell = range_str.split(':')

        # 支持整列引用 (A:A) 和整行引用 (1:10)
        # 支持动态末尾标记 (* 或 **)
        # 格式可以是: A1, A, 1, A1:*, A:*, *
        start_match = re.match(r'^([A-Z]*)(\d*)$', start_cell, re.IGNORECASE)
        end_match = re.match(r'^([A-Z]*)(\d*|\*+)$', end_cell, re.IGNORECASE)

        if not start_match or not end_match:
            raise ValueError(f"无效的单元格范围: {ref}")

        start_col_letter, start_row_str = start_match.groups()
        end_col_letter, end_row_str = end_match.groups()

        # 标记是否为动态末尾（需要在运行时根据实际数据确定）
        is_dynamic_end = end_row_str in ('*', '**')

        # 处理动态末尾标记 (如 A5:*)
        if is_dynamic_end:
            if not start_row_str:
                raise ValueError(f"动态范围必须指定起始行: {ref}")
            start_row = int(start_row_str)
            end_row = None  # 运行时确定
            if start_col_letter:
                start_col = CellRef._letter_to_col(start_col_letter)
                end_col = CellRef._letter_to_col(end_col_letter) if end_col_letter else start_col
            else:
                start_col, end_col = 1, 1
        # 处理整列引用 (如 A:A) - 只有列字母
        elif start_col_letter and end_col_letter and not start_row_str and not end_row_str:
            start_row, end_row = 1, 10000
            start_col = CellRef._letter_to_col(start_col_letter)
            end_col = CellRef._letter_to_col(end_col_letter)
        # 处理整行引用 (如 1:10) - 只有行号
        elif start_row_str and end_row_str and not start_col_letter and not end_col_letter:
            start_row = int(start_row_str)
            end_row = int(end_row_str)
            start_col, end_col = 1, 16384  # Excel最大列数
        else:
            # 标准范围 (如 A1:B10)
            start_row = int(start_row_str) if start_row_str else 1
            end_row = int(end_row_str) if end_row_str else 10000
            start_col = CellRef._letter_to_col(start_col_letter) if start_col_letter else 1
            end_col = CellRef._letter_to_col(end_col_letter) if end_col_letter else 1

        return cls(
            sheet=sheet,
            start_row=start_row,
            start_col=start_col,
            end_row=end_row if end_row else 0,  # 动态范围暂时设为0
            end_col=end_col,
            _dynamic_end_row=is_dynamic_end
        )

    def iterate(self) -> Iterator[Tuple[int, int]]:
        """迭代范围内的所有单元格"""
        for row in range(self.start_row, self.end_row + 1):
            for col in range(self.start_col, self.end_col + 1):
                yield (row, col)

    def contains(self, row: int, col: int) -> bool:
        """检查指定单元格是否在范围内"""
        return (self.start_row <= row <= self.end_row and
                self.start_col <= col <= self.end_col)

    def to_cell_refs(self) -> List[CellRef]:
        """将范围转换为单元格引用列表"""
        refs = []
        for row, col in self.iterate():
            refs.append(CellRef(sheet=self.sheet, row=row, col=col))
        return refs


def parse_cell_ref(ref: str) -> Union[CellRef, CellRange]:
    """解析单元格引用或范围"""
    if ':' in ref.split('.')[-1]:
        return CellRange.from_string(ref)
    else:
        return CellRef.from_string(ref)
