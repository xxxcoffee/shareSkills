---
name: e-checker
description: |
  Excel配置检查工具，用于验证Excel文件数据是否符合YAML规则定义。使用场景：用户说"检查配置"、"验证Excel"、"检查规则"、"跑一下检查"、"验证数据"，用户想要更新规则文件、修改验证规则、添加新的检查规则，用户询问如何配置规则、某个验证怎么实现、操作符怎么用，涉及Excel数据验证、字段关联检查、跨表引用验证、格式校验等需求；重要约束：如果需求无法通过现有规则实现，必须列出原因，禁止修改validate.py或src/下的检测脚本代码，规则无法实现的情况包括：需要全新的操作符类型、需要修改引擎核心逻辑、需要自定义代码逻辑等
---

# e-checker Excel配置检查工具

基于YAML规则文件的Excel配置检查器，采用V3 Pipeline操作符架构。

## 核心功能

### 1. 检查配置
调用 validate.py 执行Excel数据验证。

**使用方法**：
```bash
# 基本用法（默认查找 checker_rules.yaml）
python validate.py

# 指定规则文件
python validate.py rules.yaml

# 显示详细信息
python validate.py rules.yaml -v

# 列出所有操作符
python validate.py --list-operators
```

### 2. 更新规则文件
根据用户需求生成或修改YAML规则文件。

## YAML规则文件结构

### 基本格式

```yaml
version: "3.0"

# 定义外部数据源（可选）
refs:
  product_ref:
    file: "reference.xlsx"
    sheet: "ProductInfo"
    columns:
      id: "A"
      type: "D"
      level: "F"

# 校验规则
rules:
  - target: "file.xlsx:Sheet.range"
    id: "规则唯一标识"
    description: "规则描述"
    validations:
      - pipeline:
          - 操作符1: 配置
          - 操作符2: 配置
        message: "验证失败时的错误信息"
```

### Target 格式

```yaml
# 完整格式
- target: "data.xlsx:Sheet1.H5:*"

# 简写格式（自动补全 .xlsx）
- target: "data:Sheet2.A5:*"

# 带括号的工作表名
- target: "reference.xlsx:Product(Data).A5:*"
```

## 操作符列表

### SOURCE 类型 - 数据源

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `source` | `{column: "H"}` | 从指定列获取源值 |
| `as` | `{name: "var_name"}` 或 `"var_name"` | 保存当前结果到变量 |

### TRANSFORM 类型 - 数据转换

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `split` | `{delimiter: "\|"}` 或 `"\|"` | 按分隔符分割字符串。输入为列表时，对每个元素分割后扁平化 |
| `extract` | `{delimiter: ":", index: 0}` | 提取复合值的部分。输入为列表时，对每个元素提取 |
| `filter` | `{type: "regex", pattern: "^[A-Z]"}` | 过滤数组元素，支持 `regex`/`prefix`/`suffix` |
| `map` | `{operation: "strip"}` | 列表映射操作，支持 `strip`/`lower`/`upper`/`int`/`float`/`str` |
| `flatten` | - | 扁平化嵌套列表 |
| `count` | `{delimiter: "\|"}` | 计算元素个数。字符串按分隔符分割后计数，列表直接返回长度 |
| `unique` | - | 去重，保持原有顺序 |
| `math` | `{op: "add", value: 1}` | 数学运算，支持 `add`/`sub`/`mul`/`div`，value 支持变量引用 |
| `round` | `{decimals: 2}` | 四舍五入到指定小数位，默认 0 位（整数） |
| `floor` | - | 向下取整 |
| `ceil` | - | 向上取整 |
| `regex_extract` | `{pattern: "^Item(\\d+)$", group: 1}` | 正则捕获组提取。`group: 0` 表示完整匹配，默认 1。输入为列表时，对每个元素处理，不匹配的元素会被过滤 |

**注意**：以下操作符目前**尚未实现**：`slice`、`trim`、`to_number`

### LOOKUP 类型 - 数据查找

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `lookup` | `{ref_source: "ref", column: "id"}` | 跨表查找 |
| `where` | `{ref_source: "ref", match_column: "id", conditions: [...]}` | 条件过滤查找 |
| `get` | `{column: "field"}` | 获取记录属性 |
| `sheet_exists` | `{sheet_pattern: "Sheet({value})"}` | Sheet存在验证（详见下方详细说明） |
| `row_count` | `{sheet: "Sheet1", skip_rows: 4}` | 获取Sheet行数（待实现） |

**注意**：`row_count` 操作符目前**尚未实现**

#### `sheet_exists` 详细说明

验证指定Sheet是否存在于Excel文件中。支持多个占位符变量和备选文件搜索。

**配置参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `sheet_pattern` | string | 是 | - | Sheet名称模式，支持占位符 |
| `search_in` | string | 否 | 当前文件 | 主搜索文件路径 |
| `extra_refs` | array | 否 | `[]` | 备选文件路径列表 |
| `case_sensitive` | boolean | 否 | `false` | 是否区分大小写 |
| `split_by` | string | 否 | - | 分隔符，用于拆分单元格值为多个值 |

**占位符变量**：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{value}` | 当前单元格值 | `Config({value})` → `Config(A)` |
| `{value:lower}` | 当前单元格值（小写） | `Config({value:lower})` → `Config(a)` |
| `{value:upper}` | 当前单元格值（大写） | `Config({value:upper})` → `Config(A)` |
| `{@row.X}` | 同行第X列的值 | `Config({@row.B})` → 使用B列值 |

**使用示例**：

```yaml
# 基础用法：验证 Sheet 存在
- sheet_exists:
    sheet_pattern: "Config({value})"

# 多文件搜索（先搜当前文件，再搜备选文件）
- sheet_exists:
    sheet_pattern: "Level({value})"
    search_in: "main.xlsx"
    extra_refs:
      - "fallback1.xlsx"
      - "fallback2.xlsx"
    case_sensitive: true

# 使用其他列的值
- sheet_exists:
    sheet_pattern: "{value:upper}_{@row.B}"

# 验证多个值（用分隔符拆分）
- sheet_exists:
    sheet_pattern: "Tab({value})"
    split_by: "|"
```

**错误输出**：验证失败时返回错误信息，包含：
- `sheet_name`: 查找的Sheet名称
- `searched_files`: 搜索过的文件列表

### COLLECTION 类型 - 集合操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `union` | `{sources: ["@var1", "@var2"]}` | 集合并集，自动去重，结果排序 |
| `intersect` | `{sources: ["@var1", "@var2"]}` | 集合交集，结果排序 |

### AGGREGATE 类型 - 聚合操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `collect` | `{key: "ids", transform: "split:\|"}` | 跨行收集数据。支持 `transform` 转换： `"split:分隔符"`、`"extract:分隔符:索引"` |
| `sequential` | `{prefix: "id", start_from: 1, allow_gap: false}` | 顺序ID验证，检查ID是否按 prefix + number 格式顺序累加 |
| `previous` | `{ref_column: "A", row_offset: 1, allow_empty_first: true}` | 跨行引用验证，验证当前行值是否等于偏移行指定列的值 |
| `no_duplicate` | `{key: "default"}` | 跨行唯一性验证，空值/None 忽略不计 |

### VALIDATE 类型 - 验证操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `match_structure` | `{type: "regex", pattern: "^[A-Z]", mode: "each"}` | 结构验证。`mode`: `each`（验证每个元素）或 `single`（整体验证）。支持 `regex`/`prefix`/`suffix` |
| `exists_in` | `"ref.id"` | 存在性验证（待实现） |
| `eq` | `{value: "@row.D"}` 或数值 | 等于验证（待实现） |
| `in` | `{values: ["a", "b", "c"]}` | 包含验证（待实现） |
| `range_check` | `{min: 0, max: 100}` | 范围检查（待实现） |

**注意**：以下操作符目前**尚未实现**：`exists`、`all_exist_in`、`validate`、`regex_match`、`lt`、`lte`、`gt`、`gte`、`ne`、`all`、`same`

## 变量引用语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `@value` | 当前单元格值 | `source: "@value"` |
| `@row.X` | 同行第X列 | `source: "@row.H"` |
| `@var_name` | Pipeline变量 | `use: "@series_h"` |

## 表达式语法

支持 `${...}` 模板语法：

```yaml
- eq: "${@row.A + @row.B * 2}"  # 数学运算
- eq: "${len(@var)}"             # 函数调用
- eq: "${max(@row.A, @row.B, 100)}"  # 多参数函数
```

## 常见验证场景示例

### 1. 验证数组元素格式

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_item_format"
    validations:
      - pipeline:
          - split: "|"
          - extract:
              delimiter: ":"
              index: 0
          - match_structure:
              type: "regex"
              pattern: "^(ItemA|ItemB|Category)"
              mode: "each"
              message: "商品名必须是ItemA、ItemB或以Category开头"
        message: "格式不正确"
```

### 2. 跨表引用验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_exists"
    validations:
      - pipeline:
          - exists_in: "ref_data.id"
        message: "ID不存在于引用表"
```

### 3. 数值范围验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.B1:*"
    id: "check_range"
    validations:
      - pipeline:
          - match_structure:
              type: "regex"
              pattern: "^[0-9]+$"
          # 或使用 range_check（待实现）
          # - range_check:
          #     min: 0
          #     max: 100
        message: "数值必须在0-100之间"
```

### 4. 数组长度验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.C1:*"
    id: "check_length"
    validations:
      - pipeline:
          - split: "|"
          - count:
              delimiter: "|"
          # 与期望值比较需要 eq 操作符实现
        message: "数组长度不匹配"
```

### 5. 顺序ID验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_sequential"
    validations:
      - pipeline:
          - collect: "ids"
          - sequential:
              prefix: "item"
              start_from: 1
              allow_gap: false
        message: "ID必须按顺序累加"
```

### 6. 正则捕获组提取验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_item_number"
    validations:
      - pipeline:
          - regex_extract:
              pattern: "^Item(\\d+)$"
              group: 1
          # 与B列比较需要 eq 操作符实现
        message: "Item编号与B列值不匹配"
```

### 7. 跨行唯一性验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_unique_id"
    validations:
      - pipeline:
          - collect: "ids"
          - no_duplicate:
              key: "default"
        message: "ID存在重复"
```

### 8. 集合并集验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_union"
    validations:
      - pipeline:
          - split: "|"
          - as: "list_a"
          - source: "@row.B"
          - split: "|"
          - as: "list_b"
          - union:
              sources: ["@list_a", "@list_b"]
        message: "并集验证失败"
```

### 9. Sheet存在性验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_sheet_exists"
    validations:
      - pipeline:
          - sheet_exists:
              sheet_pattern: "Config({value:upper})"
              search_in: "main.xlsx"
              extra_refs:
                - "fallback.xlsx"
              case_sensitive: false
              split_by: "|"
        message: "对应Sheet不存在"
```

## 重要约束

### 规则无法实现的情况

以下情况无法通过规则实现，必须说明原因：

1. **需要全新的操作符类型** - 如果现有操作符无法组合实现需求
2. **需要修改引擎核心逻辑** - 如修改Pipeline执行流程、添加新的操作符类型分类
3. **需要自定义Python代码** - 如复杂的业务逻辑计算、外部API调用等
4. **需要修改validate.py或src/下的脚本** - 严禁修改检测引擎代码

### 可实现的替代方案

如果需求看似无法实现，考虑以下替代方案：

1. **组合现有操作符** - 大部分复杂验证可以通过多个操作符组合实现
2. **修改数据源** - 在Excel中添加辅助列简化验证逻辑
3. **拆分验证规则** - 将复杂验证拆分为多个简单规则

### 未实现操作符清单

以下操作符在文档中有定义但**尚未实现**，使用时将不生效：

**TRANSFORM 类型**：`slice`、`trim`、`to_number`

**LOOKUP 类型**：`row_count`

**VALIDATE 类型**：`exists`、`exists_in`、`eq`、`in`、`all_exist_in`、`validate`、`regex_match`、`lt`、`lte`、`gt`、`gte`、`ne`、`all`、`same`、`range_check`

## 使用步骤

### 检查配置流程

1. 确定要检查的目录和规则文件位置
2. 默认查找 `checker_rules.yaml`，如不存在使用用户指定的规则文件
3. 运行验证命令：`python validate.py [规则文件] [-v]`
4. 解析输出结果，向用户展示错误信息

### 更新规则流程

1. 理解用户的验证需求
2. 判断需求是否可通过现有操作符实现（注意检查操作符实现状态）
3. 如无法实现，列出原因并说明约束
4. 如可实现，编写或修改YAML规则文件
5. 验证规则语法正确性

## 关联脚本

本技能包含以下关联脚本：
- `scripts/validate.py` - 主验证脚本
- `scripts/src/` - eChecker 核心代码

使用技能时直接调用 `python scripts/validate.py` 执行验证。
