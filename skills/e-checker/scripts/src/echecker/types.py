"""共享类型定义"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class ErrorType(Enum):
    """错误类型"""
    FORMAT_ERROR = auto()
    RANGE_ERROR = auto()
    REFERENCE_NOT_FOUND = auto()
    CONTAINMENT_ERROR = auto()
    LOOKUP_ERROR = auto()
    EXPRESSION_ERROR = auto()
    CONFIG_ERROR = auto()
    SEQUENCE_ERROR = auto()  # 顺序错误（如ID不连续）
    ATTRIBUTE_ERROR = auto()  # 属性不匹配错误


class Severity(Enum):
    """错误严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    """校验错误"""
    rule_id: str
    cell_ref: str
    error_type: ErrorType
    message: str
    severity: Severity = Severity.ERROR
    expected: Any = None
    actual: Any = None
    sheet_name: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.cell_ref}: {self.message}"


@dataclass
class ValidationWarning:
    """校验警告"""
    rule_id: str
    cell_ref: str
    message: str
    sheet_name: str = ""

    def __str__(self) -> str:
        return f"[WARNING] {self.cell_ref}: {self.message}"


@dataclass
class ReportSummary:
    """报告摘要"""
    total_rules: int = 0
    total_cells_checked: int = 0
    error_count: int = 0
    warning_count: int = 0
    passed_count: int = 0
    duration_seconds: float = 0.0


@dataclass
class ValidationReport:
    """校验报告"""
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    summary: ReportSummary = field(default_factory=ReportSummary)

    def add_error(self, error: ValidationError) -> None:
        self.errors.append(error)
        if error.severity == Severity.ERROR:
            self.summary.error_count += 1
        elif error.severity == Severity.WARNING:
            self.summary.warning_count += 1

    def add_warning(self, warning: ValidationWarning) -> None:
        self.warnings.append(warning)
        self.summary.warning_count += 1

    def has_errors(self) -> bool:
        return any(e.severity == Severity.ERROR for e in self.errors)


@dataclass
class ValidationContext:
    """校验上下文"""
    excel_path: Path
    current_sheet: str
    current_cell: str
    cell_values: Dict[str, Any] = field(default_factory=dict)
    current_row: int = 0
    current_col: int = 0

    def get_cached_value(self, cell_ref: str) -> Any:
        return self.cell_values.get(cell_ref)

    def set_cached_value(self, cell_ref: str, value: Any) -> None:
        self.cell_values[cell_ref] = value


# 类型别名
CellValue = Union[str, int, float, bool, None]
RuleDict = Dict[str, Any]
