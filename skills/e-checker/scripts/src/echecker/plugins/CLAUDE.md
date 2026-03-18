# eChecker 插件系统 (V2 - 已迁移至V3 Pipeline)

## 概述

⚠️ **重要提示**: V2 插件系统已迁移至 V3 Pipeline 操作符架构。

此目录保留以下组件用于向后兼容：
- `ExternalDataManager` - 外部数据管理（V3引擎仍使用）
- 基础类文件 - 保留以避免导入错误

新的校验逻辑请使用 **operators/** 目录下的 Pipeline 操作符。

## 架构变更

### V2 (已弃用) → V3 (当前)

| V2 插件 | V3 Pipeline 等效 |
|---------|-----------------|
| `format` | `regex_match` |
| `range` | `range_check` |
| `cross_file` | `exists_in` + `lookup` |
| `conditional` | `lookup` + `where` + `eq` |
| `count_match` | `split` + `count` + `eq` |
| `derived_set` | `lookup` + `union` + `unique` + `eq` |
| `list_length` | `split` + `count` + `range_check` |
| `sequential_id` | `collect` + `sequential` |
| `previous_row` | `collect` + `previous` |
| `containment` | `in` |
| `chain_lookup` | `lookup` + `get` + `all_exist_in` |
| `sheet_exists` | `sheet_exists` |

## 保留组件

### ExternalDataManager (外部数据管理)

`ExternalDataManager` 仍用于管理跨文件引用的 Excel 数据，V3 引擎继续使用此组件。

### 基础类 (向后兼容)

基础类保留但不再推荐使用：
- `ValidationPlugin` - 插件基类
- `PluginContext` - 插件上下文
- `PluginManager` - 插件管理器

## 目录结构

```
src/echecker/plugins/
├── __init__.py           # 导出核心类
├── base.py               # ValidationPlugin 基类（保留兼容）
├── context.py            # PluginContext 上下文（保留兼容）
├── manager.py            # PluginManager 管理器（保留兼容）
├── external_data.py      # ExternalDataManager（V3仍使用）
└── cross_sheet/          # 跨表引用插件（保留）
```

## 新开发请使用 Operators

添加新校验逻辑请参见 [operators/CLAUDE.md](../operators/CLAUDE.md)。

## 关键文件路径

| 用途 | 路径 |
|------|------|
| 外部数据管理 | `plugins/external_data.py` |
| Pipeline 操作符 | `operators/` |
