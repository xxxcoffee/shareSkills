"""外部数据管理器

用于管理跨文件引用的Excel数据，提供统一的查询接口。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd


@dataclass
class ExternalDataSource:
    """外部数据源定义

    Attributes:
        name: 数据源名称（用于引用）
        file: Excel文件路径
        sheet: 工作表名
        columns: 列定义 {列名: 列索引/字母}
        key_column: 主键列名（用于lookup）
    """
    name: str
    file: Path
    sheet: str
    columns: Dict[str, str]  # {name: column_letter}
    key_column: Optional[str] = None


class ExternalDataManager:
    """外部数据管理器

    统一管理外部文件数据，支持：
    - 多数据源注册
    - 数据缓存（避免重复加载）
    - 按主键查找（lookup）
    - 条件查询（query）

    示例:
        manager = ExternalDataManager()
        manager.register_source(ExternalDataSource(
            name="elements",
            file=Path("data.xlsx"),
            sheet="Sheet1",
            columns={"id": "A", "name": "B"},
            key_column="id"
        ))

        # 查找单条记录
        record = manager.lookup("elements", "id", "123")

        # 条件查询
        results = manager.query("elements", {"level": 1})
    """

    def __init__(self):
        self._sources: Dict[str, ExternalDataSource] = {}
        self._cache: Dict[str, pd.DataFrame] = {}
        self._index_cache: Dict[str, Dict[str, Dict]] = {}  # 用于加速lookup

    def register_source(self, source: ExternalDataSource) -> None:
        """注册数据源

        Args:
            source: 数据源定义
        """
        self._sources[source.name] = source
        # 清除缓存（如果存在）
        self._cache.pop(source.name, None)
        self._index_cache.pop(source.name, None)

    def get_source(self, name: str) -> ExternalDataSource:
        """获取数据源定义

        Args:
            name: 数据源名称

        Returns:
            ExternalDataSource: 数据源定义

        Raises:
            KeyError: 数据源不存在
        """
        if name not in self._sources:
            raise KeyError(f"数据源 '{name}' 未注册")
        return self._sources[name]

    def _load_data(self, source_name: str) -> pd.DataFrame:
        """加载数据（带缓存）

        Args:
            source_name: 数据源名称

        Returns:
            pd.DataFrame: 数据
        """
        if source_name in self._cache:
            return self._cache[source_name]

        source = self._sources[source_name]

        # 读取Excel
        df = pd.read_excel(
            source.file,
            sheet_name=source.sheet,
            header=None  # 不自动解析表头
        )

        # 根据列定义设置列名
        # columns定义为 {name: column_letter}
        col_mapping = {}
        for col_name, col_letter in source.columns.items():
            col_idx = self._column_letter_to_index(col_letter)
            if col_idx < len(df.columns):
                col_mapping[col_idx] = col_name

        # 重命名列
        df = df.rename(columns=col_mapping)

        # 缓存
        self._cache[source_name] = df

        return df

    def _build_index(self, source_name: str, column: str) -> Dict[str, Dict]:
        """构建索引用于加速lookup

        Args:
            source_name: 数据源名称
            column: 索引列名

        Returns:
            Dict[str, Dict]: {值: 记录}
        """
        cache_key = f"{source_name}:{column}"
        if cache_key in self._index_cache:
            return self._index_cache[cache_key]

        df = self._load_data(source_name)

        # 构建索引
        index = {}
        for _, row in df.iterrows():
            value = row.get(column)
            if pd.notna(value):
                key = str(value).strip()
                index[key] = row.to_dict()

        self._index_cache[cache_key] = index
        return index

    def lookup(
        self,
        source_name: str,
        column: str,
        value: Any
    ) -> Optional[Dict[str, Any]]:
        """查找单条记录

        Args:
            source_name: 数据源名称
            column: 查找列名
            value: 查找值

        Returns:
            Optional[Dict]: 记录字典，不存在则返回None

        示例:
            record = manager.lookup("elements", "id", "123")
            if record:
                series = record.get("series")
        """
        index = self._build_index(source_name, column)
        return index.get(str(value).strip())

    def query(
        self,
        source_name: str,
        conditions: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """条件查询

        Args:
            source_name: 数据源名称
            conditions: 查询条件 {列名: 期望值}

        Returns:
            pd.DataFrame: 查询结果

        示例:
            # 查询level=1的所有记录
            results = manager.query("elements", {"level": 1})
        """
        df = self._load_data(source_name)

        if not conditions:
            return df

        # 应用条件过滤
        mask = pd.Series([True] * len(df))
        for col, expected in conditions.items():
            if col in df.columns:
                mask = mask & (df[col] == expected)

        return df[mask]

    def exists(self, source_name: str, column: str, value: Any) -> bool:
        """检查值是否存在

        Args:
            source_name: 数据源名称
            column: 列名
            value: 要检查的值

        Returns:
            bool: 是否存在
        """
        return self.lookup(source_name, column, value) is not None

    def get_values(
        self,
        source_name: str,
        column: str,
        unique: bool = True
    ) -> List[Any]:
        """获取列的所有值

        Args:
            source_name: 数据源名称
            column: 列名
            unique: 是否去重

        Returns:
            List[Any]: 值列表
        """
        df = self._load_data(source_name)

        if column not in df.columns:
            return []

        values = df[column].dropna()

        if unique:
            values = values.unique()

        return values.tolist()

    def clear_cache(self, source_name: Optional[str] = None) -> None:
        """清除缓存

        Args:
            source_name: 数据源名称，None表示清除所有
        """
        if source_name is None:
            self._cache.clear()
            self._index_cache.clear()
        else:
            self._cache.pop(source_name, None)
            # 清除相关索引
            keys_to_remove = [
                k for k in self._index_cache.keys()
                if k.startswith(f"{source_name}:")
            ]
            for k in keys_to_remove:
                self._index_cache.pop(k, None)

    @staticmethod
    def _column_letter_to_index(letter: str) -> int:
        """将Excel列字母转换为0-based索引

        Args:
            letter: 列字母（如"A", "BC"）

        Returns:
            int: 0-based列索引
        """
        letter = letter.upper()
        result = 0
        for char in letter:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1  # 转为0-based

    @staticmethod
    def _column_index_to_letter(index: int) -> str:
        """将0-based索引转换为Excel列字母

        Args:
            index: 0-based索引

        Returns:
            str: 列字母
        """
        result = ""
        index += 1  # 转为1-based
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            result = chr(ord('A') + remainder) + result
        return result
