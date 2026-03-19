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
| `source` | `"@row.H"` | 从指定列获取源值 |
| `as` | `"var_name"` | 保存当前结果到变量 |
| `use` | `"@var_name"` | 使用变量作为输入 |

### TRANSFORM 类型 - 数据转换

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `split` | `"\|"` | 按分隔符分割字符串 |
| `extract` | `{delimiter: ":", index: 0}` | 提取复合值的部分 |
| `filter` | `{type: "regex", pattern: "^[A-Z]"}` | 过滤数组元素 |
| `map` | `{operation: "strip"}` | 列表映射操作 |
| `flatten` | - | 扁平化嵌套列表 |
| `slice` | `3` 或 `{start: 1, end: 4}` | 切片取子集 |
| `trim` | - | 去空格 |
| `to_number` | - | 转换为数字 |
| `count` | - | 计数 |
| `unique` | `true` | 去重 |
| `math` | `{op: "+", value: 1}` | 数学运算 |
| `round` | `2` | 四舍五入 |
| `floor` | - | 向下取整 |
| `ceil` | - | 向上取整 |
| `regex_extract` | `{pattern: "^Item(\\d+)$", group: 1}` | 正则捕获组提取 |

### LOOKUP 类型 - 数据查找

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `lookup` | `"ref[id].col"` | 跨表查找 |
| `where` | `"level == 1"` | 条件过滤 |
| `get` | `"field_name"` | 获取属性 |
| `row_count` | `{sheet: "Sheet1", skip_rows: 4}` | 获取Sheet行数 |
| `sheet_exists` | `"Sheet({value})"` | Sheet存在验证 |

### COLLECTION 类型 - 集合操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `union` | `["@var1", "@var2"]` | 集合并集 |
| `intersect` | `["@var1", "@var2"]` | 集合交集 |

### AGGREGATE 类型 - 聚合操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `collect` | `"key"` | 收集数据（跨行） |
| `sequential` | `{prefix: "id", start_from: 1}` | 顺序验证 |
| `previous` | `{ref_column: "A"}` | 跨行引用验证 |
| `no_duplicate` | `{key: "default"}` | 跨行唯一性验证 |

### VALIDATE 类型 - 验证操作

| 操作符 | 配置 | 说明 |
|--------|------|------|
| `eq` | `1` 或 `"@row.D"` | 等于验证 |
| `lt` / `lte` | `10` | 小于/小于等于 |
| `gt` / `gte` | `0` | 大于/大于等于 |
| `ne` | `0` | 不等于 |
| `all` | `[{lt: 10}]` | 全满足验证 |
| `same` | `"@row.I"` | 真假性一致验证 |
| `in` | `"@list"` | 包含验证 |
| `exists_in` | `"ref.id"` | 存在性验证 |
| `match_structure` | `{type: "regex", pattern: "^[A-Z]"}` | 结构验证 |
| `range_check` | `{min: 0, max: 100}` | 范围检查 |

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
          - to_number
          - range_check:
              min: 0
              max: 100
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
          - count
          - eq: "${@row.D}"  # 等于D列的值
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
          - eq: "${@row.B}"
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
          - no_duplicate
        message: "ID存在重复"
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

## 使用步骤

### 检查配置流程

1. 确定要检查的目录和规则文件位置
2. 默认查找 `checker_rules.yaml`，如不存在使用用户指定的规则文件
3. 运行验证命令：`python validate.py [规则文件] [-v]`
4. 解析输出结果，向用户展示错误信息

### 更新规则流程

1. 理解用户的验证需求
2. 判断需求是否可通过现有操作符实现
3. 如无法实现，列出原因并说明约束
4. 如可实现，编写或修改YAML规则文件
5. 验证规则语法正确性

## 关联脚本

本技能包含以下关联脚本：
- `scripts/validate.py` - 主验证脚本
- `scripts/src/` - eChecker 核心代码

使用技能时直接调用 `python scripts/validate.py` 执行验证。
