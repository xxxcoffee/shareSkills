# eChecker 规则系统 (rules)

## 模块概述

规则系统负责解析和管理 V3 格式的校验规则。

**核心职责：**
- **规则解析**: 将 YAML 规则文件解析为内部数据结构
- **Pipeline 配置**: 解析 Pipeline 操作符链
- **外部引用**: 管理跨文件数据引用（refs）配置

## 项目结构

```
rules/
├── __init__.py      # 模块导出（V3组件）
└── v3_parser.py     # V3 规则解析器
```

## V3 规则系统

### 数据模型 (v3_parser.py)

| 类名 | 说明 |
|------|------|
| `ExternalDataSourceConfig` | 外部数据源配置 |
| `PipelineStep` | Pipeline 步骤 |
| `V3ValidationConfig` | V3 验证配置 |
| `V3Rule` | V3 规则 |
| `V3RuleSet` | V3 规则集 |

### 解析器 (v3_parser.py)

`V3RuleParser` 解析 V3 格式规则：

```python
parser = V3RuleParser()
ruleset = parser.parse_file("v3_rules.yaml")  # 返回 V3RuleSet
```

**Pipeline 语法支持：**

| 语法 | 说明 | 示例 |
|------|------|------|
| `operator: config` | 基本操作符调用 | `split: "\|"` |
| `as: "var"` | 保存结果到变量 | `as: "series_h"` |
| `use: "@var"` | 使用变量 | `use: "@series_h"` |
| `@value` | 当前单元格值 | `eq: "@value"` |
| `@row.X` | 同行第X列 | `source: "@row.H"` |
| `lookup: "ref[col].attr"` | 跨表查找 | `lookup: "data[id].name"` |

## 规则数据结构说明

### 字段说明

| 概念 | 字段 | 说明 |
|------|------|------|
| 目标范围 | `target` | 单元格范围，如 "Sheet1.A1:C10" |
| 规则ID | `id` | 可选，默认生成 MD5 前8位 |
| 启用状态 | `enabled` | 默认 true |
| Pipeline | `pipeline` | 操作符链列表 |
| 错误消息 | `message` | 自定义提示 |

### Target 格式规范

```
格式: <工作表>.<范围>
示例:
  - "Sheet1.A1"           # 单个单元格
  - "Sheet1.A1:C10"       # 连续范围
  - "PassNewList.H5:H100" # 特定工作表
  - "PassNewList.A5:*"    # 动态范围（从A5到数据末尾）
```

#### 动态范围支持

使用 `*` 作为结束标记，系统会在验证时自动检测该列的实际数据行数。

动态范围检测逻辑：从起始行向下扫描，遇到连续3个空行后停止。

## Pipeline 操作符列表

### 数据源操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `source` | 指定数据源 | `source: "@row.H"` |
| `as` | 保存变量 | `as: "var_name"` |
| `use` | 使用变量 | `use: "@var_name"` |

### 转换操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `split` | 分割字符串 | `split: "\|"` |
| `extract` | 提取子串 | `extract: ":0"` |
| `count` | 计数 | `count` |
| `unique` | 去重 | `unique: true` |
| `flatten` | 扁平化 | `flatten: true` |

### 查找操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `lookup` | 跨表查找 | `lookup: "ref[id].col"` |
| `where` | 条件过滤 | `where: "level == 1"` |
| `get` | 获取属性 | `get: "field_name"` |
| `sheet_exists` | Sheet检查 | `sheet_exists: "Sheet({value})"` |

### 集合操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `union` | 并集 | `union: ["@var1", "@var2"]` |
| `intersect` | 交集 | `intersect: ["@var1", "@var2"]` |

### 聚合操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `collect` | 收集数据 | `collect: "ids"` |
| `sequential` | 顺序验证 | `sequential: {prefix: "id", start_from: 1}` |
| `previous` | 跨行引用 | `previous: {ref_column: "A", row_offset: 1}` |

### 验证操作符

| 操作符 | 用途 | 示例 |
|--------|------|------|
| `exists` | 存在验证 | `exists: true` |
| `exists_in` | 存在集合 | `exists_in: "ref.id"` |
| `eq` | 等于 | `eq: "@expected"` |
| `in` | 包含 | `in: "@list"` |
| `all_exist_in` | 全存在 | `all_exist_in: "@target"` |
| `range_check` | 范围 | `range_check: {min: 0, max: 100}` |
| `regex_match` | 正则 | `regex_match: "^\d+$"` |
| `same` | 真假性一致 | `same: "@target"` |

## 关键文件路径

| 用途 | 路径 |
|------|------|
| V3 解析器 | `rules/v3_parser.py` |

## 依赖项

- `pyyaml`: YAML 文件解析
- `dataclasses`: 数据结构定义（Python 3.7+）
