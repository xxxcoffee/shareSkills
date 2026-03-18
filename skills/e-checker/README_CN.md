# e-checker

Excel 配置检查工具 - 基于 YAML 规则验证 Excel 数据。

## 简介

e-checker 是一个强大的 Excel 数据验证工具，使用基于 YAML 的规则文件来验证数据完整性。它采用灵活的 Pipeline 架构，内置 25+ 操作符，支持各种验证场景。

## 功能特性

- **YAML 规则**：使用人类可读的 YAML 格式定义验证规则
- **25+ 操作符**：丰富的操作符集合，支持验证、转换、查找和集合操作
- **Pipeline 架构**：链式组合多个操作，实现复杂验证逻辑
- **跨表验证**：引用其他工作表或文件的数据
- **表达式支持**：使用 `${...}` 语法进行动态计算
- **变量系统**：使用 `@变量名` 语法存储和复用中间结果
- **详细报告**：获取带上下文的清晰错误信息

## 安装

```bash
# 复制到 Claude Code skills 目录
cp -r skills/e-checker ~/.claude/skills/
```

## 使用方法

### 基本用法

```bash
# 默认：使用当前目录下的 checker_rules.yaml
python validate.py

# 指定自定义规则文件
python validate.py rules.yaml

# 显示详细信息
python validate.py rules.yaml -v

# 列出所有可用操作符
python validate.py --list-operators
```

### 规则文件结构

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

# 验证规则
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_item_format"
    description: "验证物品格式"
    validations:
      - pipeline:
          - source: "@value"
          - split: "|"
          - match_structure:
              type: "regex"
              pattern: "^(ItemA|ItemB|Category)"
              mode: "each"
        message: "物品格式无效"
```

## 操作符列表

### 数据源操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `source` | 获取单元格值 | `source: "@row.H"` |
| `as` | 保存到变量 | `as: "var_name"` |
| `use` | 使用变量 | `use: "@var_name"` |

### 转换操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `split` | 分割字符串 | `split: "\|"` |
| `extract` | 提取部分值 | `extract: {delimiter: ":", index: 0}` |
| `filter` | 过滤数组 | `filter: {type: "regex", pattern: "^[A-Z]"}` |
| `map` | 映射操作 | `map: {operation: "strip"}` |
| `flatten` | 扁平化嵌套列表 | `flatten` |
| `slice` | 切片数组 | `slice: 3` 或 `slice: {start: 1, end: 4}` |
| `trim` | 去除空白 | `trim` |
| `to_number` | 转为数字 | `to_number` |
| `count` | 计数 | `count` |
| `unique` | 去重 | `unique: true` |
| `math` | 数学运算 | `math: {op: "+", value: 1}` |
| `round` | 四舍五入 | `round: 2` |
| `floor` | 向下取整 | `floor` |
| `ceil` | 向上取整 | `ceil` |

### 查找操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `lookup` | 跨表查找 | `lookup: "ref[id].col"` |
| `where` | 条件过滤 | `where: "level == 1"` |
| `get` | 获取属性 | `get: "field_name"` |
| `row_count` | 获取行数 | `row_count: {sheet: "Sheet1", skip_rows: 4}` |
| `sheet_exists` | 检查工作表存在 | `sheet_exists: "Sheet({value})"` |

### 集合操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `union` | 集合并集 | `union: ["@var1", "@var2"]` |
| `intersect` | 集合交集 | `intersect: ["@var1", "@var2"]` |

### 聚合操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `collect` | 跨行收集数据 | `collect: "key"` |
| `sequential` | 顺序ID检查 | `sequential: {prefix: "id", start_from: 1}` |
| `previous` | 跨行引用 | `previous: {ref_column: "A"}` |

### 验证操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `eq` | 等于 | `eq: 1` 或 `eq: "@row.D"` |
| `lt` / `lte` | 小于 / 小于等于 | `lt: 10` |
| `gt` / `gte` | 大于 / 大于等于 | `gt: 0` |
| `ne` | 不等于 | `ne: 0` |
| `all` | 全部满足 | `all: [{lt: 10}]` |
| `same` | 真假性一致 | `same: "@row.I"` |
| `in` | 包含 | `in: "@list"` |
| `exists_in` | 存在于引用表 | `exists_in: "ref.id"` |
| `match_structure` | 模式匹配 | `match_structure: {type: "regex", pattern: "^[A-Z]"}` |
| `range_check` | 范围检查 | `range_check: {min: 0, max: 100}` |

## 变量引用

| 语法 | 说明 | 示例 |
|------|------|------|
| `@value` | 当前单元格值 | `source: "@value"` |
| `@row.X` | 同行第X列 | `source: "@row.H"` |
| `@var_name` | Pipeline 变量 | `use: "@series_h"` |

## 表达式语法

使用 `${...}` 进行动态计算：

```yaml
- eq: "${@row.A + @row.B * 2}"      # 数学运算
- eq: "${len(@var)}"                 # 函数调用
- eq: "${max(@row.A, @row.B, 100)}"  # 多参数函数
```

## 示例

### 验证数组元素格式

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_items"
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
        message: "物品必须是 ItemA、ItemB 或以 Category 开头"
```

### 跨表引用验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_id_exists"
    validations:
      - pipeline:
          - exists_in: "product_ref.id"
        message: "ID 不存在于引用表中"
```

### 数值范围验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.B1:*"
    id: "check_percentage"
    validations:
      - pipeline:
          - to_number
          - range_check:
              min: 0
              max: 100
        message: "数值必须在 0 到 100 之间"
```

### 顺序 ID 验证

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_sequence"
    validations:
      - pipeline:
          - collect: "ids"
          - sequential:
              prefix: "item"
              start_from: 1
        message: "ID 必须是连续的"
```

## 项目结构

```
e-checker/
├── SKILL.md              # Claude Code skill 定义
├── README.md             # 英文文档
├── README_CN.md          # 中文文档
└── scripts/
    ├── validate.py       # 主验证脚本
    └── src/
        └── echecker/     # 核心库
            ├── core/     # 引擎实现
            ├── operators/# 操作符定义
            ├── rules/    # 规则解析器
            └── ...
```

## 开源协议

MIT License
