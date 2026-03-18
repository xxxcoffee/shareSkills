"""插件执行上下文"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from echecker.plugins.external_data import ExternalDataManager


@dataclass
class PluginContext:
    """插件执行上下文

    提供插件执行时所需的所有上下文信息，包括：
    - 基础位置信息（文件、工作表、单元格）
    - 行数据访问（支持@row.X语法）
    - 外部数据访问（跨文件引用）
    - 缓存共享

    示例:
        # 获取同行其他列的值
        value = context.get_row_value("H")
        value = context.get_row_value("@row.H")  # 等价

        # 获取外部数据源
        source = context.get_external_data("element_pass_new")
    """

    # 基础位置信息
    excel_path: Path  # Excel文件路径
    current_sheet: str  # 当前工作表名
    current_cell: str  # 当前单元格引用（如"A1"）
    current_row: int  # 当前行号（1-based）
    current_col: int  # 当前列号（1-based）

    # 内部数据（通过属性访问）
    _row_data: Dict[str, Any] = field(default_factory=dict)  # 整行数据缓存
    _external_data: Optional["ExternalDataManager"] = field(default=None)  # 外部数据管理器
    _cache: Dict[str, Any] = field(default_factory=dict)  # 插件共享缓存

    def get_row_value(self, column: str) -> Any:
        """获取同行其他列的值

        支持@row.X语法，例如：
        - get_row_value("H") -> 获取同行H列的值
        - get_row_value("@row.H") -> 同上

        Args:
            column: 列标识（如"H"或"@row.H"）

        Returns:
            Any: 列值，不存在则返回None
        """
        # 处理 @row.X 语法
        if column.startswith("@row."):
            column = column[5:]

        # 处理列字母（统一转为大写）
        column = column.upper()

        return self._row_data.get(column)

    def get_external_data(self, ref_name: str) -> "ExternalDataManager":
        """获取外部数据管理器

        Args:
            ref_name: 数据源名称（在refs中定义）

        Returns:
            ExternalDataManager: 外部数据管理器

        Raises:
            KeyError: 数据源不存在时抛出
        """
        if self._external_data is None:
            raise RuntimeError("外部数据管理器未配置")

        return self._external_data

    def set_external_data(self, manager: "ExternalDataManager") -> None:
        """设置外部数据管理器

        Args:
            manager: 外部数据管理器实例
        """
        self._external_data = manager

    def get_cache(self, key: str) -> Any:
        """获取缓存值

        Args:
            key: 缓存键

        Returns:
            Any: 缓存值，不存在则返回None
        """
        return self._cache.get(key)

    def set_cache(self, key: str, value: Any) -> None:
        """设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
        """
        self._cache[key] = value

    @property
    def cell_ref(self) -> str:
        """获取完整单元格引用（如"Sheet1.A1"）"""
        return f"{self.current_sheet}.{self.current_cell}"
