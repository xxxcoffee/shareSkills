"""集合和收集操作符

实现集合操作（并集、交集）和跨行验证操作符（collect, sequential, previous）。
"""

import re
from collections import defaultdict
from typing import Any, Dict, List, Set, Optional

from echecker.operators.base import (
    PipelineOperator,
    AggregateOperator,
    PipelineContext,
    OperatorResult,
    OperatorType,
    register_operator,
)


def _resolve_value(value_ref: str, context: PipelineContext) -> Any:
    """解析值引用

    支持:
    - @var: 从pipeline_state获取变量
    - @row.X: 从同行数据获取列值

    Args:
        value_ref: 值引用字符串
        context: 管道上下文

    Returns:
        解析后的值
    """
    if not isinstance(value_ref, str):
        return value_ref

    if value_ref.startswith("@"):
        # 变量引用 @var
        if value_ref.startswith("@row."):
            return context.get_row_value(value_ref[5:])
        else:
            # 从pipeline_state获取
            var_name = value_ref[1:]
            return context.get_state(var_name)
    return value_ref


def _to_list(value: Any) -> List[Any]:
    """将值转换为列表"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip() == "":
        return []
    return [value]


@register_operator
class UnionOperator(PipelineOperator):
    """并集操作符

    将多个列表合并为一个，自动去重。

    配置:
        sources: 源列表引用数组，如 ["@var1", "@var2"]

    示例:
        - union: ["@row.H", "@row.I"]

    或使用完整配置:
        - type: union
          sources: ["@var1", "@var2", "@var3"]
    """

    name = "union"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "将多个列表合并为一个（去重）"

    config_spec = {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "源列表引用数组，如 ['@var1', '@var2']"
            }
        }
    }

    def execute(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """执行并集操作"""
        sources = config.get("sources", [])

        # 如果没有配置sources，尝试将输入值作为列表处理
        if not sources:
            input_list = _to_list(value)
            return OperatorResult(success=True, value=input_list)

        # 收集所有源列表
        result_set: Set[str] = set()

        for source_ref in sources:
            source_value = _resolve_value(source_ref, context)
            source_list = _to_list(source_value)

            # 将元素转为字符串并加入集合
            for item in source_list:
                if item is not None:
                    result_set.add(str(item).strip())

        # 转回列表
        result = sorted(list(result_set))

        return OperatorResult(success=True, value=result)


@register_operator
class IntersectOperator(PipelineOperator):
    """交集操作符

    返回多个列表的交集。

    配置:
        sources: 源列表引用数组，如 ["@var1", "@var2"]

    示例:
        - intersect: ["@row.H", "@row.I"]

    或使用完整配置:
        - type: intersect
          sources: ["@var1", "@var2"]
    """

    name = "intersect"
    operator_type = OperatorType.TRANSFORM
    version = "1.0.0"
    description = "返回多个列表的交集"

    config_spec = {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "items": {"type": "string"},
                "description": "源列表引用数组，如 ['@var1', '@var2']"
            }
        }
    }

    def execute(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """执行交集操作"""
        sources = config.get("sources", [])

        if not sources:
            return OperatorResult(success=True, value=[])

        # 解析所有源列表
        all_sets: List[Set[str]] = []

        for source_ref in sources:
            source_value = _resolve_value(source_ref, context)
            source_list = _to_list(source_value)
            item_set = {str(item).strip() for item in source_list if item is not None}
            all_sets.append(item_set)

        # 计算交集
        if not all_sets:
            return OperatorResult(success=True, value=[])

        result_set = all_sets[0]
        for s in all_sets[1:]:
            result_set = result_set & s

        result = sorted(list(result_set))

        return OperatorResult(success=True, value=result)


@register_operator
class CollectOperator(AggregateOperator):
    """收集操作符

    跨行数据收集器，将所有行的值收集到一个列表中，存入pipeline_state。
    这是一个特殊的AGGREGATE操作符，在finalize阶段才真正完成。

    配置:
        key: 存储键名（默认 "collected"）
        transform: 可选的转换函数（如 "split:|"）

    示例:
        - collect: "my_values"

    或使用完整配置:
        - type: collect
          key: "event_pass_ids"
          transform: "extract:\":0\""
    """

    name = "collect"
    operator_type = OperatorType.AGGREGATE
    version = "1.0.0"
    description = "跨行收集数据到列表"

    config_spec = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "存储键名",
                "default": "collected"
            },
            "transform": {
                "type": "string",
                "description": "可选转换，如 'split:|' 或 'extract::0'"
            }
        }
    }

    def _get_collected_key(self, config: Dict) -> str:
        """获取收集数据的存储键"""
        key = config.get("key", "collected")
        return f"_collect_{key}"

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """应用转换

        支持的格式:
        - split:| - 按|分割为列表
        - extract::0 - 按:分割，取第0部分
        - extract:-:1 - 按-分割，取第1部分
        """
        if not transform:
            return value

        if transform.startswith("split:"):
            sep = transform[6:]
            if isinstance(value, str):
                return [v.strip() for v in value.split(sep) if v.strip()]
        elif transform.startswith("extract:"):
            spec = transform[8:]  # 例如 ":0" 或 "-:1"
            # 找到最后一个:，前面是分隔符，后面是索引
            if ":" in spec:
                # spec格式: "{sep}:{idx}" 或 ":{idx}"（sep为:的情况）
                # 处理边界情况: spec = ":0" 表示 sep=":", idx="0"
                sep, idx_str = spec.rsplit(":", 1)
                # 如果sep为空，说明原始格式是 "extract::N"，表示用 ":" 分割
                if sep == "":
                    sep = ":"
                try:
                    idx = int(idx_str)
                    if isinstance(value, str) and sep in value:
                        parts = value.split(sep)
                        if 0 <= idx < len(parts):
                            return parts[idx].strip()
                except ValueError:
                    pass

        return value

    def collect(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """收集阶段 - 收集当前单元格值"""
        collected_key = self._get_collected_key(config)
        transform = config.get("transform", "")

        # 应用转换
        transformed_value = self._apply_transform(value, transform)

        # 存储到pipeline_state
        current = context.get_state(collected_key)
        if current is None:
            current = []

        # 如果转换后是列表，展开；否则添加单个值
        if isinstance(transformed_value, list):
            current.extend(transformed_value)
        else:
            current.append(transformed_value)

        return OperatorResult(
            success=True,
            state_updates={collected_key: current}
        )

    def finalize(self, context: PipelineContext, config: Dict) -> OperatorResult:
        """最终阶段 - 返回收集的数据"""
        collected_key = self._get_collected_key(config)
        key = config.get("key", "collected")

        collected = context.get_state(collected_key, [])

        # 将结果存储到用户指定的key
        return OperatorResult(
            success=True,
            value=collected,
            state_updates={key: collected}
        )


@register_operator
class SequentialOperator(AggregateOperator):
    """顺序ID验证操作符

    验证ID是否符合 prefix + number 的格式并按顺序累加。
    例如: eventpass1, eventpass2, eventpass3...

    配置:
        prefix: ID前缀（如 "eventpass"）
        start_from: 起始序号（默认1）
        allow_gap: 是否允许跳号（默认false）

    示例:
        - sequential:
            prefix: "eventpass"
            start_from: 1
            allow_gap: false
    """

    name = "sequential"
    operator_type = OperatorType.VALIDATE
    version = "1.0.0"
    description = "验证ID按顺序累加（如eventpass1,eventpass2...）"

    config_spec = {
        "type": "object",
        "required": ["prefix"],
        "properties": {
            "prefix": {
                "type": "string",
                "description": "ID前缀，如 'eventpass'"
            },
            "start_from": {
                "type": "integer",
                "description": "起始序号，默认为1",
                "default": 1
            },
            "allow_gap": {
                "type": "boolean",
                "description": "是否允许跳号，默认false",
                "default": False
            }
        }
    }

    def _get_cache_key(self, config: Dict) -> str:
        """构建缓存键"""
        prefix = config.get("prefix", "")
        return f"_sequential_{prefix}"

    def collect(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """收集阶段 - 收集和解析ID"""
        prefix = config.get("prefix", "")
        cache_key = self._get_cache_key(config)
        collected_key = f"{cache_key}_collected"

        # 获取当前收集列表
        collected = context.get_state(collected_key, [])

        # 解析当前值
        if value is None or str(value).strip() == "":
            collected.append((context.current_cell, None, "empty"))
        else:
            value_str = str(value).strip()
            pattern = f"^{re.escape(prefix)}(\\d+)$"
            match = re.match(pattern, value_str)

            if match:
                number = int(match.group(1))
                collected.append((context.current_cell, number, value_str))
            else:
                collected.append((context.current_cell, None, f"invalid:{value_str}"))

        return OperatorResult(
            success=True,
            state_updates={collected_key: collected}
        )

    def finalize(self, context: PipelineContext, config: Dict) -> OperatorResult:
        """最终验证阶段 - 检查顺序"""
        prefix = config.get("prefix", "")
        start_from = config.get("start_from", 1)
        allow_gap = config.get("allow_gap", False)

        cache_key = self._get_cache_key(config)
        collected_key = f"{cache_key}_collected"

        collected = context.get_state(collected_key, [])
        errors: List[Dict] = []

        # 过滤出有效的序号
        valid_entries = [(cell, num, val) for cell, num, val in collected if num is not None]

        if not valid_entries:
            return OperatorResult(success=True, value=[])

        # 按序号排序
        valid_entries.sort(key=lambda x: x[1])

        # 检查1: 是否从 start_from 开始
        first_num = valid_entries[0][1]
        if first_num != start_from:
            cell, _, val = valid_entries[0]
            errors.append({
                "cell": cell,
                "message": f"ID应从 {prefix}{start_from} 开始，但第一个是 {val}",
                "expected": f"{prefix}{start_from}",
                "actual": val
            })

        # 检查2: 是否有重复
        seen_numbers: Dict[int, str] = {}
        for cell, num, val in valid_entries:
            if num in seen_numbers:
                errors.append({
                    "cell": cell,
                    "message": f"ID序号 {num} 重复出现",
                    "expected": "唯一",
                    "actual": f"{val}（与 {seen_numbers[num]} 重复）"
                })
            else:
                seen_numbers[num] = cell

        # 检查3: 是否连续（如果不允许跳号）
        if not allow_gap and len(valid_entries) > 1:
            numbers = [num for _, num, _ in valid_entries]
            expected_sequence = list(range(min(numbers), max(numbers) + 1))
            missing = set(expected_sequence) - set(numbers)

            if missing:
                missing_str = ", ".join(f"{prefix}{n}" for n in sorted(missing))
                last_valid_cell = valid_entries[-1][0]
                errors.append({
                    "cell": last_valid_cell,
                    "message": f"ID序号不连续，缺少: {missing_str}",
                    "expected": f"连续序列 {prefix}{start_from}~{prefix}{max(numbers)}",
                    "actual": f"缺少 {len(missing)} 个序号"
                })

        success = len(errors) == 0
        return OperatorResult(
            success=success,
            value=[val for _, _, val in valid_entries],
            errors=errors,
            message="顺序验证通过" if success else f"发现 {len(errors)} 个顺序错误"
        )


@register_operator
class PreviousOperator(AggregateOperator):
    """跨行引用验证操作符

    验证当前行的值是否等于上一行（或指定偏移行）的某列值。
    适用于验证previousPassId等于上一行id的场景。

    配置:
        ref_column: 引用列（如 "A"）
        row_offset: 行偏移（默认1，即上一行）
        allow_empty_first: 首行是否允许为空（默认true）

    示例:
        - previous:
            ref_column: "A"
            row_offset: 1
            allow_empty_first: true
    """

    name = "previous"
    operator_type = OperatorType.VALIDATE
    version = "1.0.0"
    description = "验证当前行值等于上一行指定列的值"

    config_spec = {
        "type": "object",
        "required": ["ref_column"],
        "properties": {
            "ref_column": {
                "type": "string",
                "description": "参考的列字母（如'A'表示参考A列）"
            },
            "row_offset": {
                "type": "integer",
                "description": "行偏移量（默认1，即上一行）",
                "default": 1
            },
            "allow_empty_first": {
                "type": "boolean",
                "description": "首行是否允许为空（默认true）",
                "default": True
            }
        }
    }

    def _get_cache_key(self, config: Dict) -> str:
        """构建缓存键"""
        ref_column = config.get("ref_column", "")
        return f"_previous_{ref_column}"

    def collect(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """收集阶段 - 收集当前值和参考列值"""
        ref_column = config.get("ref_column", "")
        cache_key = self._get_cache_key(config)
        collected_key = f"{cache_key}_collected"

        # 获取参考列的值
        ref_value = context.get_row_value(ref_column)

        # 获取当前收集列表
        collected = context.get_state(collected_key, [])

        # 记录当前单元格信息
        collected.append({
            "cell": context.current_cell,
            "row": context.current_row,
            "current_value": value,
            "ref_value": ref_value
        })

        return OperatorResult(
            success=True,
            state_updates={collected_key: collected}
        )

    def finalize(self, context: PipelineContext, config: Dict) -> OperatorResult:
        """最终验证阶段 - 检查跨行引用"""
        ref_column = config.get("ref_column", "")
        row_offset = config.get("row_offset", 1)
        allow_empty_first = config.get("allow_empty_first", True)

        cache_key = self._get_cache_key(config)
        collected_key = f"{cache_key}_collected"

        collected = context.get_state(collected_key, [])
        errors: List[Dict] = []

        if not collected:
            return OperatorResult(success=True)

        # 按行号排序
        collected.sort(key=lambda x: x["row"])

        # 检查每一行
        for i, item in enumerate(collected):
            current_row = item["row"]
            current_cell = item["cell"]
            current_value = item["current_value"]

            # 前row_offset行特殊处理
            if i < row_offset:
                if not allow_empty_first and (current_value is None or str(current_value).strip() == ""):
                    errors.append({
                        "cell": current_cell,
                        "message": f"第{i+1}行{current_cell[0]}列不允许为空",
                        "expected": "非空值",
                        "actual": "空"
                    })
                continue

            # 获取偏移行的参考值
            prev_item = collected[i - row_offset]
            expected_value = prev_item["ref_value"]

            # 比较值
            current_str = str(current_value).strip() if current_value is not None else ""
            expected_str = str(expected_value).strip() if expected_value is not None else ""

            if current_str != expected_str:
                errors.append({
                    "cell": current_cell,
                    "message": f"值 '{current_str}' 不等于上一行({prev_item['cell']})的值 '{expected_str}'",
                    "expected": expected_str,
                    "actual": current_str
                })

        success = len(errors) == 0
        return OperatorResult(
            success=success,
            errors=errors,
            message="跨行引用验证通过" if success else f"发现 {len(errors)} 个跨行引用错误"
        )


@register_operator
class NoDuplicateOperator(AggregateOperator):
    """唯一性验证操作符

    跨行收集值，在 finalize 阶段检查是否有重复。
    支持每行 Pipeline 输出为单个值或列表（列表时展开收集每个元素）。
    空值/None 忽略不计。

    示例:
        - no_duplicate
    """

    name = "no_duplicate"
    operator_type = OperatorType.VALIDATE
    version = "1.0.0"
    description = "验证跨行值唯一性（无重复）"

    config_spec = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "状态存储键名（用于区分同一会话中多个 no_duplicate 规则）",
                "default": "default"
            }
        }
    }

    def _get_cache_key(self, config: Dict) -> str:
        key = config.get("key", "default")
        return f"_no_duplicate_{key}"

    def collect(self, value: Any, context: PipelineContext, config: Dict) -> OperatorResult:
        """收集阶段 - 收集当前行的值"""
        cache_key = self._get_cache_key(config)
        current: List = context.get_state(cache_key, [])

        items: List[Any]
        if isinstance(value, list):
            items = value
        else:
            items = [value]

        for item in items:
            if item is None:
                continue
            if isinstance(item, str) and item.strip() == "":
                continue
            current.append((context.current_cell, context.current_row, item))

        return OperatorResult(
            success=True,
            state_updates={cache_key: current}
        )

    def finalize(self, context: PipelineContext, config: Dict) -> OperatorResult:
        """最终验证阶段 - 检查重复值"""
        cache_key = self._get_cache_key(config)
        collected: List = context.get_state(cache_key, [])

        # 按 value 分组，找出重复项
        groups: Dict[Any, List] = defaultdict(list)
        for cell_ref, row_num, val in collected:
            groups[val].append((cell_ref, row_num))

        errors: List[Dict] = []
        for val, entries in groups.items():
            if len(entries) > 1:
                rows_str = "、".join(f"第{row}行" for _, row in entries)
                errors.append({
                    "cell": entries[0][0],
                    "message": f"值 {val} 在{rows_str}中重复出现",
                    "expected": "唯一",
                    "actual": str(val)
                })

        success = len(errors) == 0
        return OperatorResult(
            success=success,
            errors=errors,
            message="唯一性验证通过" if success else f"发现 {len(errors)} 个重复值"
        )
