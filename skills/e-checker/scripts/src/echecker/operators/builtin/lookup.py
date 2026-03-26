"""查找操作符

提供外部数据查找相关的操作符。
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from echecker.operators.base import (
    Operator,
    OperatorContext,
    OperatorResult,
    OperatorType,
    register_operator,
)


@register_operator
class LookupOperator(Operator):
    """数据查找操作符

    在外部数据源中查找指定列的值。

    配置:
        ref_source: 外部数据源名称
        column: 要查找的列名
        extract_by: 可选，分隔符用于提取部分值
        extract_index: 可选，提取部分的索引
    """

    name = "lookup"
    operator_type = OperatorType.LOOKUP
    description = "在外部数据源中查找值"
    config_spec = {
        "type": "object",
        "properties": {
            "ref_source": {"type": "string", "description": "外部数据源名称"},
            "column": {"type": "string", "description": "要查找的列名"},
            "extract_by": {"type": "string", "description": "分隔符（可选）"},
            "extract_index": {"type": "integer", "description": "提取部分索引（默认0）"},
        },
        "required": ["ref_source", "column"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class WhereOperator(Operator):
    """条件过滤操作符

    根据条件过滤外部数据。

    配置:
        ref_source: 外部数据源名称
        match_column: 匹配列名
        conditions: 条件列表，每个条件包含column, operator, value
    """

    name = "where"
    operator_type = OperatorType.LOOKUP
    description = "根据条件过滤数据"
    config_spec = {
        "type": "object",
        "properties": {
            "ref_source": {"type": "string", "description": "外部数据源名称"},
            "match_column": {"type": "string", "description": "匹配列名"},
            "conditions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "column": {"type": "string"},
                        "operator": {"type": "string", "enum": ["eq", "ne", "gt", "lt", "gte", "lte", "in"]},
                        "value": {"type": ["string", "number", "boolean", "array"]}
                    }
                }
            }
        },
        "required": ["ref_source", "match_column", "conditions"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class GetOperator(Operator):
    """获取列值操作符

    从查找结果中获取指定列的值。

    配置:
        column: 列名
    """

    name = "get"
    operator_type = OperatorType.LOOKUP
    description = "获取指定列的值"
    config_spec = {
        "type": "object",
        "properties": {
            "column": {"type": "string", "description": "列名"}
        },
        "required": ["column"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class AttributeMatchOperator(Operator):
    """属性匹配操作符

    验证关联元素的属性是否与主记录匹配。

    配置:
        related_element_source: 关联元素数据源
        related_match_column: 关联元素匹配列
        related_attr_column: 关联元素属性列
        primary_attr_column: 主数据属性列
    """

    name = "attribute_match"
    operator_type = OperatorType.VALIDATE
    description = "验证关联元素属性匹配"
    config_spec = {
        "type": "object",
        "properties": {
            "related_element_source": {"type": "string"},
            "related_match_column": {"type": "string"},
            "related_attr_column": {"type": "string"},
            "primary_attr_column": {"type": "string"},
        },
        "required": ["related_element_source", "related_match_column",
                    "related_attr_column", "primary_attr_column"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 待实现
        return OperatorResult.ok(input_data)


@register_operator
class SheetExistsOperator(Operator):
    """Sheet存在性校验操作符

    验证指定Sheet是否存在于Excel文件中。

    配置:
        sheet_pattern: Sheet名称模式，使用{value}占位符
        search_in: 可选，主搜索文件路径（默认当前文件）
        extra_refs: 可选，额外的备选文件路径列表
        case_sensitive: 可选，是否区分大小写（默认False）
        split_by: 可选，分隔符用于拆分单元格值
    """

    name = "sheet_exists"
    operator_type = OperatorType.VALIDATE
    description = "验证Sheet是否存在"
    config_spec = {
        "type": "object",
        "properties": {
            "sheet_pattern": {"type": "string", "description": "Sheet名称模式，如'Config({value})'"},
            "search_in": {"type": "string", "description": "主搜索文件路径（可选，默认当前文件）"},
            "extra_refs": {"type": "array", "items": {"type": "string"}, "description": "备选文件路径列表"},
            "case_sensitive": {"type": "boolean", "description": "是否区分大小写", "default": False},
            "split_by": {"type": "string", "description": "分隔符用于拆分单元格值"},
        },
        "required": ["sheet_pattern"],
    }

    def execute(self, input_data: Any, context: OperatorContext, config: Dict) -> OperatorResult:
        # 获取配置值
        sheet_pattern = config.get("sheet_pattern", "")
        search_in = config.get("search_in")
        extra_refs = config.get("extra_refs", []) or []
        case_sensitive = config.get("case_sensitive", False)
        split_by = config.get("split_by")

        # 处理输入值（支持分隔符拆分）
        values_to_check = self._split_input(input_data, split_by)

        errors = []

        for value in values_to_check:
            # 生成Sheet名称
            sheet_name = self._generate_sheet_name(sheet_pattern, value, context)

            # 搜索Sheet
            found, searched_files = self._search_sheet(
                sheet_name, search_in, extra_refs, context, case_sensitive
            )

            if not found:
                files_str = ", ".join(str(f) for f in searched_files)
                errors.append({
                    "message": f"Sheet '{sheet_name}' 不存在于以下文件中: {files_str}",
                    "sheet_name": sheet_name,
                    "searched_files": [str(f) for f in searched_files],
                })

        if errors:
            return OperatorResult.error(f"Sheet存在性验证失败", errors)

        return OperatorResult.ok(input_data)

    def _split_input(self, input_data: Any, split_by: Optional[str]) -> List[str]:
        """拆分输入值为列表"""
        if input_data is None:
            return [""]

        input_str = str(input_data).strip()

        if not input_str:
            return [""]

        if split_by:
            # 过滤空值
            return [v.strip() for v in input_str.split(split_by) if v.strip()]

        return [input_str]

    def _generate_sheet_name(self, pattern: str, value: str, context: OperatorContext) -> str:
        """根据模式生成Sheet名称

        支持:
        - {value}: 当前单元格值
        - {value:lower}: 转小写
        - {value:upper}: 转大写
        - {@row.X}: 同行X列的值
        """
        result = pattern

        # 处理 {@row.X} 占位符
        import re
        row_pattern = r'\{@row\.(\w+)\}'
        for match in re.finditer(row_pattern, result):
            col_ref = match.group(1)
            row_value = context.get_row_value(col_ref)
            if row_value is None:
                row_value = ""
            result = result.replace(match.group(0), str(row_value))

        # 处理 {value} 和变体
        if "{value:lower}" in result:
            result = result.replace("{value:lower}", str(value).lower())
        elif "{value:upper}" in result:
            result = result.replace("{value:upper}", str(value).upper())
        elif "{value}" in result:
            result = result.replace("{value}", str(value))

        return result

    def _search_sheet(
        self,
        sheet_name: str,
        search_in: Optional[str],
        extra_refs: List[str],
        context: OperatorContext,
        case_sensitive: bool,
    ) -> tuple[bool, List]:
        """在指定文件中搜索Sheet

        Returns:
            (是否找到, 搜索过的文件列表)
        """
        from pathlib import Path
        from echecker.excel.provider import ExcelProvider

        # 确定要搜索的文件列表
        files_to_search = []

        # 主文件
        if search_in:
            # 解析路径（支持相对路径和变量）
            search_path = self._resolve_path(search_in, context)
            files_to_search.append(search_path)
        elif context.excel_path:
            files_to_search.append(context.excel_path)

        # 备选文件
        for ref in extra_refs:
            ref_path = self._resolve_path(ref, context)
            if ref_path not in files_to_search:
                files_to_search.append(ref_path)

        searched_files = []

        for file_path in files_to_search:
            searched_files.append(file_path)

            if not file_path.exists():
                continue

            try:
                with ExcelProvider(file_path) as provider:
                    sheet_names = provider.get_sheet_names()

                    if self._match_sheet_name(sheet_name, sheet_names, case_sensitive):
                        return True, searched_files
            except Exception:
                # 文件读取失败，继续搜索下一个
                continue

        return False, searched_files

    def _resolve_path(self, path_str: str, context: OperatorContext) -> Path:
        """解析路径字符串为Path对象

        支持:
        - 绝对路径
        - 相对路径（相对于当前Excel文件目录）
        - {@value} 等变量引用
        """
        from pathlib import Path

        # 处理变量引用
        path_str = self._replace_variables(path_str, context)

        path = Path(path_str)

        # 如果是绝对路径，直接返回
        if path.is_absolute():
            return path

        # 相对于当前Excel文件的目录
        if context.excel_path:
            base_dir = context.excel_path.parent
            return base_dir / path

        # 默认为当前工作目录
        return path.resolve()

    def _replace_variables(self, text: str, context: OperatorContext) -> str:
        """替换文本中的变量引用"""
        result = text

        # 替换 {@value}
        if "{@value}" in result:
            result = result.replace("{@value}", str(context.cell_value or ""))

        # 替换 {@row.X}
        import re
        row_pattern = r'\{@row\.(\w+)\}'
        for match in re.finditer(row_pattern, result):
            col_ref = match.group(1)
            row_value = context.get_row_value(col_ref)
            if row_value is None:
                row_value = ""
            result = result.replace(match.group(0), str(row_value))

        return result

    def _match_sheet_name(
        self, target: str, sheet_names: List[str], case_sensitive: bool
    ) -> bool:
        """检查目标Sheet名称是否存在于Sheet列表中"""
        if case_sensitive:
            return target in sheet_names

        target_lower = target.lower()
        return any(s.lower() == target_lower for s in sheet_names)
