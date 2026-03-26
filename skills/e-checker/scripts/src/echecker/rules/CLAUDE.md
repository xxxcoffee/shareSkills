# eChecker 规则系统 (rules)

## 模块概述

规则系统负责解析和管理 V3 格式的校验规则。

**核心职责：**
- **规则解析**: 将 YAML 规则文件解析为内部数据结构
- **Pipeline 配置**: 解析 Pipeline 操作符链
- **外部引用**: 管理跨文件数据引用（refs）配置
- **文件夹通配符展开**: 支持批量验证文件夹中的 Excel 文件

## 项目结构

```
rules/
├── __init__.py          # 模块导出（V3组件）
├── v3_parser.py         # V3 规则解析器
└── folder_expander.py   # 文件夹通配符展开器
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
格式: <文件>:<工作表>.<范围>
示例:
  - "file.xlsx:Sheet1.A1"           # 单个单元格
  - "file.xlsx:Sheet1.A1:C10"       # 连续范围
  - "file.xlsx:PassNewList.H5:H100" # 特定工作表
  - "file.xlsx:PassNewList.A5:*"    # 动态范围（从A5到数据末尾）
  - "data/*.xlsx:Sheet1.A1:*"       # 文件夹通配符
```

#### 动态范围支持

使用 `*` 作为结束标记，系统会在验证时自动检测该列的实际数据行数。

动态范围检测逻辑：从起始行向下扫描，遇到连续3个空行后停止。

### 文件夹通配符支持（新增）

target 支持使用通配符批量匹配文件夹中的 Excel 文件：

| 类型 | 格式 | 示例 | 说明 |
|------|------|------|------|
| 文件通配 | `folder/*.xlsx:Sheet.range` | `data/*.xlsx:Sheet1.A1:*` | 匹配文件夹下所有xlsx |
| 递归通配 | `folder/**/*.xlsx:Sheet.range` | `data/**/*.xlsx:*.A1:*` | 递归匹配子文件夹 |
| Sheet通配 | `file:*.range` | `data.xlsx:*.A1:*` | 匹配所有Sheet |
| 组合通配 | `folder/**/*.xlsx:*.range` | `data/**/*.xlsx:*.A1:*` | 文件和Sheet都通配 |

## 文件夹通配符展开器 (folder_expander.py)

`FolderExpander` 支持使用通配符批量匹配文件夹中的 Excel 文件，并为每个匹配的文件+Sheet组合创建独立的规则副本。

### 使用方式

```python
from echecker.rules.folder_expander import FolderExpander
from echecker.rules.v3_parser import V3RuleParser

# 解析规则文件
parser = V3RuleParser()
ruleset = parser.parse_file("rules.yaml")

# 展开通配符规则
expander = FolderExpander(base_path=".")
expanded_rules = expander.expand(ruleset.rules)

# expanded_rules 包含所有展开后的具体规则
for rule in expanded_rules:
    print(f"Target: {rule.target}")
```

### API 参考

#### FolderExpander 类

```python
class FolderExpander:
    def __init__(self, base_path: Optional[str] = None):
        """初始化展开器

        Args:
            base_path: 基础路径，默认为当前目录
        """

    def is_wildcard_target(self, target: str) -> bool:
        """判断 target 是否包含通配符

        检测文件路径中的 `*`、`?`、`**` 以及 Sheet 名称中的通配符。
        """

    def expand(self, rules: List[V3Rule]) -> List[V3Rule]:
        """展开所有包含通配符的规则

        为每个匹配的文件+Sheet组合创建新的 V3Rule，
        保持原有规则的所有字段（validations, description, enabled等）。

        Returns:
            展开后的规则列表（不包含通配符的具体规则）
        """

    def expand_target_string(self, target: str) -> List[str]:
        """展开 target 字符串为具体的目标字符串列表

        便捷方法，用于直接展开 target 而不需要完整的规则对象。
        """
```

#### ExpandedTarget 数据类

```python
@dataclass
class ExpandedTarget:
    file_path: str       # 展开后的文件路径
    sheet_name: str      # 展开后的 Sheet 名称
    range_str: str       # 范围字符串（保持不变）
    original_target: str # 原始通配符 target
```

### 展开行为说明

1. **规则复制模式**：
   - 通配符展开发生在规则解析阶段
   - 每个匹配的文件和 Sheet 组合生成独立的验证任务
   - 所有副本共享相同的 pipeline 和验证逻辑
   - 为新规则生成唯一的 ID（原ID添加后缀）

2. **文件匹配**：
   - 使用 `pathlib.Path.glob()` 进行非递归匹配
   - 使用 `pathlib.Path.rglob()` 进行递归匹配
   - 支持 `*`（匹配任意字符）和 `?`（匹配单个字符）

3. **Sheet 匹配**：
   - 使用 `openpyxl` 读取 Excel 文件获取所有 Sheet 名称
   - 使用 `fnmatch` 进行 Sheet 名称模式匹配

## 文件夹批量验证

当 target 使用通配符时，系统会为每个匹配的文件+Sheet组合创建独立的规则副本，验证逻辑保持一致。

**规则复制模式：**
- 通配符展开发生在规则解析阶段
- 每个匹配的文件和Sheet组合生成独立的验证任务
- 所有副本共享相同的 pipeline 和验证逻辑
- 验证报告会汇总所有匹配项的结果

**使用示例：**

```yaml
# 示例1：验证 data 文件夹下所有 xlsx 文件的 Sheet1 表
rules:
  - target: "data/*.xlsx:Sheet1.A1:*"
    validate:
      - exists: true

# 示例2：递归验证所有子文件夹中的文件
rules:
  - target: "data/**/*.xlsx:*.A1:*"
    validate:
      - regex_match: "^\\d+$"

# 示例3：验证所有 Sheet 的 A 列
rules:
  - target: "config.xlsx:*.A1:*"
    validate:
      - exists: true
```

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
| 文件夹展开器 | `rules/folder_expander.py` |

## 依赖项

- `pyyaml`: YAML 文件解析
- `dataclasses`: 数据结构定义（Python 3.7+）
- `openpyxl`: Excel 文件读取（用于 Sheet 名称匹配）
- `fnmatch`: Unix shell 风格通配符匹配
