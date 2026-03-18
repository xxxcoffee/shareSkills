"""V2到V3规则迁移工具

将V2格式的YAML规则文件迁移到V3格式的操作符管道配置。

用法:
    python -m echecker.migrate input_v2_rules.yaml -o output_v3_rules.yaml
    python -m echecker.migrate input_v2_rules.yaml --dry-run
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def load_v2_rules(yaml_file: str) -> Dict[str, Any]:
    """加载V2规则文件

    Args:
        yaml_file: V2规则文件路径

    Returns:
        Dict: 解析后的规则数据

    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML解析错误
    """
    path = Path(yaml_file)
    if not path.exists():
        raise FileNotFoundError(f"规则文件不存在: {yaml_file}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def convert_validation(validation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换单个V2验证规则为V3操作符管道步骤

    Args:
        validation: V2验证配置，包含type和其他配置参数

    Returns:
        List[Dict]: V3操作符步骤列表

    映射关系:
        - cross_file → split + lookup + exists_in
        - conditional → split + where + exists
        - derived_set → source + split + lookup + union + unique
        - count_match → split + count + range_check
        - list_length → split + count + range_check
        - sequential_id → collect + sequential
        - previous_row → collect + previous
        - containment → split + all_exist_in
        - chain_lookup → extract + lookup + get + split + all_exist_in
        - sheet_exists → sheet_exists
    """
    val_type = validation.get("type", "")
    config = {k: v for k, v in validation.items() if k not in ["type", "message"]}
    message = validation.get("message")

    converters = {
        "cross_file": _convert_cross_file,
        "conditional": _convert_conditional,
        "derived_set": _convert_derived_set,
        "count_match": _convert_count_match,
        "list_length": _convert_list_length,
        "sequential_id": _convert_sequential_id,
        "previous_row": _convert_previous_row,
        "containment": _convert_containment,
        "chain_lookup": _convert_chain_lookup,
        "sheet_exists": _convert_sheet_exists,
        "format": _convert_format,
        "range": _convert_range,
    }

    converter = converters.get(val_type)
    if converter:
        steps = converter(config)
    else:
        # 未知类型，创建通用转换步骤
        steps = [_create_unknown_step(val_type, config)]

    # 添加消息到第一个步骤（如果有）
    if message and steps:
        steps[0]["message"] = message

    return steps


def _convert_cross_file(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换cross_file插件

    V2: cross_file验证值是否存在于外部数据源
    V3: split + lookup + exists_in
    """
    steps = []

    # 1. 如果有split_by，先split
    if config.get("split_by"):
        steps.append({
            "operator": "split",
            "config": {"by": config["split_by"]}
        })

    # 2. lookup操作
    lookup_config = {
        "ref_source": config.get("ref_source"),
        "column": config.get("match_column", config.get("column")),
    }

    # 处理复合值提取
    if config.get("extract_by"):
        lookup_config["extract_by"] = config["extract_by"]
        lookup_config["extract_index"] = config.get("extract_index", 0)

    steps.append({
        "operator": "lookup",
        "config": lookup_config
    })

    # 3. exists_in验证
    steps.append({
        "operator": "exists_in",
        "config": {}
    })

    return steps


def _convert_conditional(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换conditional插件

    V2: conditional条件过滤验证
    V3: split + where + exists
    """
    steps = []

    # 1. 如果有split_by，先split
    if config.get("split_by"):
        steps.append({
            "operator": "split",
            "config": {"by": config["split_by"]}
        })

    # 2. where操作 - 条件过滤
    conditions = config.get("conditions", [])
    if conditions:
        where_config = {
            "ref_source": config.get("ref_source"),
            "match_column": config.get("match_column"),
            "conditions": conditions
        }
        steps.append({
            "operator": "where",
            "config": where_config
        })

    # 3. exists验证
    steps.append({
        "operator": "exists",
        "config": {}
    })

    return steps


def _convert_derived_set(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换derived_set插件

    V2: derived_set派生集合
    V3: source + split + lookup + union + unique
    """
    steps = []
    derive_from = config.get("derive_from", [])

    # 为每个源字段创建子管道
    sub_pipelines = []
    for source_config in derive_from:
        sub_steps = []

        # 1. source操作 - 获取源值
        sub_steps.append({
            "operator": "source",
            "config": {
                "column": source_config.get("column")
            }
        })

        # 2. 如果有split_by，split
        if source_config.get("split_by"):
            sub_steps.append({
                "operator": "split",
                "config": {"by": source_config["split_by"]}
            })

        # 3. lookup操作
        lookup = source_config.get("lookup", {})
        lookup_config = {
            "ref_source": lookup.get("ref_source"),
            "column": lookup.get("return_column", lookup.get("match_column")),
        }

        # 处理复合值提取
        if lookup.get("extract_by"):
            lookup_config["extract_by"] = lookup["extract_by"]
            lookup_config["extract_index"] = lookup.get("extract_index", 0)

        sub_steps.append({
            "operator": "lookup",
            "config": lookup_config
        })

        sub_pipelines.append(sub_steps)

    # 合并所有子管道结果
    if len(sub_pipelines) == 1:
        steps.extend(sub_pipelines[0])
    elif len(sub_pipelines) > 1:
        # 使用union合并多个源
        steps.append({
            "operator": "union",
            "config": {
                "pipelines": sub_pipelines
            }
        })

    # 4. unique操作
    if config.get("set_operation") == "union":
        steps.append({
            "operator": "unique",
            "config": {}
        })

    return steps


def _convert_count_match(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换count_match插件

    V2: count_match数量匹配
    V3: split + count + range_check
    """
    steps = []

    # 1. split操作
    if config.get("split_by"):
        steps.append({
            "operator": "split",
            "config": {"by": config["split_by"]}
        })

    # 2. count操作
    steps.append({
        "operator": "count",
        "config": {}
    })

    # 3. range_check操作
    compare_with = config.get("compare_with", {})
    if compare_with:
        range_config = {}

        # 解析比较目标
        target = compare_with.get("target", "")
        if target.startswith("@row."):
            range_config["target_column"] = target.replace("@row.", "")

        # 处理比较操作符
        operator = compare_with.get("operator", "eq")
        if operator == "eq":
            range_config["exact"] = None  # 将在运行时从目标列获取
        elif operator == "gte":
            range_config["min"] = None
        elif operator == "lte":
            range_config["max"] = None
        elif operator == "gt":
            range_config["min"] = None
            range_config["exclusive_min"] = True
        elif operator == "lt":
            range_config["max"] = None
            range_config["exclusive_max"] = True

        steps.append({
            "operator": "range_check",
            "config": range_config
        })

    return steps


def _convert_list_length(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换list_length插件

    V2: list_length列表长度
    V3: split + count + range_check
    """
    steps = []

    # 1. split操作
    split_by = config.get("split_by", "|")
    steps.append({
        "operator": "split",
        "config": {"by": split_by}
    })

    # 2. count操作
    steps.append({
        "operator": "count",
        "config": {}
    })

    # 3. range_check操作
    range_config = {}
    if "min_count" in config:
        range_config["min"] = config["min_count"]
    if "max_count" in config:
        range_config["max"] = config["max_count"]

    if range_config:
        steps.append({
            "operator": "range_check",
            "config": range_config
        })

    return steps


def _convert_sequential_id(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换sequential_id插件

    V2: sequential_id顺序ID校验
    V3: collect + sequential
    """
    steps = []

    # 1. collect操作 - 跨行收集数据
    steps.append({
        "operator": "collect",
        "config": {
            "key": "id_sequence",
            "group_by": "sheet"
        }
    })

    # 2. sequential操作 - 验证连续性
    seq_config = {
        "prefix": config.get("prefix", ""),
        "start_from": config.get("start_from", 1),
        "allow_gap": config.get("allow_gap", False)
    }

    steps.append({
        "operator": "sequential",
        "config": seq_config
    })

    return steps


def _convert_previous_row(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换previous_row插件

    V2: previous_row跨行引用校验
    V3: collect + previous
    """
    steps = []

    # 1. collect操作 - 跨行收集数据
    collect_config = {
        "key": "previous_row_check",
        "group_by": "sheet",
        "columns": [config.get("ref_column")]
    }

    steps.append({
        "operator": "collect",
        "config": collect_config
    })

    # 2. previous操作 - 验证与上一行的关系
    prev_config = {
        "ref_column": config.get("ref_column"),
        "row_offset": config.get("row_offset", 1),
        "allow_empty_first": config.get("allow_empty_first", True)
    }

    steps.append({
        "operator": "previous",
        "config": prev_config
    })

    return steps


def _convert_containment(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换containment插件

    V2: containment值包含校验
    V3: split + all_exist_in
    """
    steps = []

    # 1. split操作
    if config.get("split_by"):
        steps.append({
            "operator": "split",
            "config": {"by": config["split_by"]}
        })

    # 2. all_exist_in操作
    steps.append({
        "operator": "all_exist_in",
        "config": {
            "target_column": config.get("target_column"),
            "split_by": config.get("split_by", "|")
        }
    })

    return steps


def _convert_chain_lookup(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换chain_lookup插件

    V2: chain_lookup链式查找校验
    V3: extract + lookup + get + split + all_exist_in
    """
    steps = []

    source_config = config.get("source", {})
    primary_lookup = config.get("primary_lookup", {})
    related_ids = config.get("related_ids", {})
    containment = config.get("containment", {})

    # 1. extract操作 - 提取源值
    if source_config.get("extract_by"):
        steps.append({
            "operator": "extract",
            "config": {
                "by": source_config["extract_by"],
                "index": source_config.get("extract_index", 0)
            }
        })

    # 2. lookup操作 - 主数据源查找
    steps.append({
        "operator": "lookup",
        "config": {
            "ref_source": primary_lookup.get("ref_source"),
            "column": primary_lookup.get("match_column")
        }
    })

    # 3. get操作 - 获取关联ID列
    steps.append({
        "operator": "get",
        "config": {
            "column": related_ids.get("from_column")
        }
    })

    # 4. split操作 - 拆分关联ID
    if related_ids.get("split_by"):
        steps.append({
            "operator": "split",
            "config": {"by": related_ids["split_by"]}
        })

    # 5. extract操作 - 提取关联ID
    if related_ids.get("extract_by"):
        steps.append({
            "operator": "extract",
            "config": {
                "by": related_ids["extract_by"],
                "index": related_ids.get("extract_index", 0)
            }
        })

    # 6. all_exist_in操作 - 验证包含性
    steps.append({
        "operator": "all_exist_in",
        "config": {
            "target_column": containment.get("target_column"),
            "split_by": containment.get("split_by", "|")
        }
    })

    # 7. attribute_match操作（如果有）
    attr_match = config.get("attribute_match")
    if attr_match:
        steps.append({
            "operator": "attribute_match",
            "config": {
                "related_element_source": attr_match.get("related_element_source"),
                "related_match_column": attr_match.get("related_match_column"),
                "related_attr_column": attr_match.get("related_attr_column"),
                "primary_attr_column": attr_match.get("primary_attr_column")
            }
        })

    return steps


def _convert_sheet_exists(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换sheet_exists插件

    V2: sheet_exists Sheet存在性校验
    V3: sheet_exists（保持原名）
    """
    steps = []

    sheet_exists_config = {
        "sheet_pattern": config.get("sheet_pattern")
    }

    if config.get("search_in"):
        sheet_exists_config["search_in"] = config["search_in"]
    if config.get("extra_refs"):
        sheet_exists_config["extra_refs"] = config["extra_refs"]
    if config.get("case_sensitive") is not None:
        sheet_exists_config["case_sensitive"] = config["case_sensitive"]
    if config.get("split_by"):
        sheet_exists_config["split_by"] = config["split_by"]

    steps.append({
        "operator": "sheet_exists",
        "config": sheet_exists_config
    })

    return steps


def _convert_format(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换format插件

    V2: format格式校验
    V3: validate（使用pattern）
    """
    return [{
        "operator": "validate",
        "config": {
            "pattern": config.get("pattern"),
            "type": config.get("type", "regex")
        }
    }]


def _convert_range(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """转换range插件

    V2: range范围校验
    V3: range_check
    """
    range_config = {}

    if "min" in config:
        range_config["min"] = config["min"]
    if "max" in config:
        range_config["max"] = config["max"]
    if "exclusive_min" in config:
        range_config["exclusive_min"] = config["exclusive_min"]
    if "exclusive_max" in config:
        range_config["exclusive_max"] = config["exclusive_max"]

    return [{
        "operator": "range_check",
        "config": range_config
    }]


def _create_unknown_step(val_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """为未知类型创建通用步骤"""
    return {
        "operator": "unknown",
        "config": {
            "original_type": val_type,
            **config
        }
    }


def convert_rule(rule: Dict[str, Any]) -> Dict[str, Any]:
    """转换单个V2规则为V3规则

    Args:
        rule: V2规则配置

    Returns:
        Dict: V3规则配置
    """
    v3_rule = {
        "target": rule.get("target"),
        "id": rule.get("id"),
        "description": rule.get("description"),
        "enabled": rule.get("enabled", True),
    }

    # 移除None值
    v3_rule = {k: v for k, v in v3_rule.items() if v is not None}

    # 转换所有验证
    pipeline = []
    validations = rule.get("validations", [])

    for validation in validations:
        steps = convert_validation(validation)
        pipeline.extend(steps)

    v3_rule["pipeline"] = pipeline

    return v3_rule


def convert_refs(refs: Dict[str, Any]) -> Dict[str, Any]:
    """转换refs为V3格式

    V3格式与V2基本相同，但可能需要调整一些字段名
    """
    v3_refs = {}

    for name, ref_config in refs.items():
        v3_refs[name] = {
            "file": str(ref_config.get("file", "")),
            "sheet": ref_config.get("sheet"),
            "columns": ref_config.get("columns", {})
        }

    return v3_refs


def save_v3_rules(rules: Dict[str, Any], output_file: str) -> None:
    """保存V3规则到文件

    Args:
        rules: V3规则数据
        output_file: 输出文件路径
    """
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(rules, f, allow_unicode=True, sort_keys=False, indent=2)


def migrate_v2_to_v3(v2_data: Dict[str, Any]) -> Dict[str, Any]:
    """将V2规则数据转换为V3格式

    Args:
        v2_data: V2规则数据

    Returns:
        Dict: V3规则数据
    """
    v3_data = {
        "version": "3.0",
        "description": f"从V2迁移的规则 (原版本: {v2_data.get('version', '2.0')})"
    }

    # 转换refs
    if "refs" in v2_data:
        v3_data["refs"] = convert_refs(v2_data["refs"])

    # 转换rules
    v3_rules = []
    for rule in v2_data.get("rules", []):
        v3_rule = convert_rule(rule)
        v3_rules.append(v3_rule)

    v3_data["rules"] = v3_rules

    return v3_data


def print_conversion_log(v2_data: Dict[str, Any], v3_data: Dict[str, Any]) -> None:
    """打印转换日志"""
    print("=" * 60)
    print("V2 → V3 规则迁移日志")
    print("=" * 60)

    # 统计信息
    v2_rules = v2_data.get("rules", [])
    v3_rules = v3_data.get("rules", [])

    print(f"\n📊 统计信息:")
    print(f"  原规则数量: {len(v2_rules)}")
    print(f"  转换后规则数量: {len(v3_rules)}")

    if "refs" in v2_data:
        print(f"  外部数据源: {len(v2_data['refs'])}")

    # 详细转换信息
    print(f"\n📝 规则转换详情:")
    for i, (v2_rule, v3_rule) in enumerate(zip(v2_rules, v3_rules), 1):
        print(f"\n  规则 {i}: {v3_rule.get('id', 'N/A')}")
        print(f"    目标: {v2_rule.get('target')}")
        print(f"    原始验证: {len(v2_rule.get('validations', []))} 个")
        print(f"    转换后步骤: {len(v3_rule.get('pipeline', []))} 个")

        # 显示每个验证的转换
        for val in v2_rule.get("validations", []):
            val_type = val.get("type", "unknown")
            print(f"      - {val_type} → ", end="")

            # 找到对应的V3步骤
            steps = convert_validation(val)
            step_names = [s.get("operator", "unknown") for s in steps]
            print(f"{' → '.join(step_names)}")

    print("\n" + "=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="将V2规则文件迁移到V3格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m echecker.migrate input_v2_rules.yaml -o output_v3_rules.yaml
  python -m echecker.migrate input_v2_rules.yaml --dry-run
        """
    )

    parser.add_argument(
        "input",
        help="V2规则文件路径"
    )

    parser.add_argument(
        "-o", "--output",
        help="V3规则文件输出路径"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印转换结果，不保存文件"
    )

    args = parser.parse_args()

    try:
        # 加载V2规则
        print(f"📂 加载V2规则文件: {args.input}")
        v2_data = load_v2_rules(args.input)

        # 转换为V3
        print("🔄 转换为V3格式...")
        v3_data = migrate_v2_to_v3(v2_data)

        # 打印转换日志
        print_conversion_log(v2_data, v3_data)

        if args.dry_run:
            print("🔍 干运行模式，不保存文件")
            print("\n生成的V3规则预览:")
            print("-" * 40)
            print(yaml.dump(v3_data, allow_unicode=True, sort_keys=False, indent=2))
        elif args.output:
            save_v3_rules(v3_data, args.output)
            print(f"✅ 已保存V3规则到: {args.output}")
        else:
            # 如果没有指定输出，生成默认文件名
            input_path = Path(args.input)
            default_output = input_path.parent / f"{input_path.stem}_v3{input_path.suffix}"
            save_v3_rules(v3_data, str(default_output))
            print(f"✅ 已保存V3规则到: {default_output}")

        return 0

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"❌ YAML解析错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ 转换失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
