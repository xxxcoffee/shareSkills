# eChecker V3 Pipeline 操作符系统

operators 模块是 eChecker V3 架构的核心，实现 Pipeline 操作符模式。

## 架构特点

- **Pipeline 模式**: 数据按顺序流经多个操作符
- **统一接口**: 所有操作符继承 `PipelineOperator` 基类
- **状态管理**: Pipeline 支持变量存储和复用 (`as:`, `use:`)
- **注册机制**: 使用装饰器自动注册操作符
- **类型分类**: SOURCE, TRANSFORM, LOOKUP, COLLECTION, AGGREGATE, VALIDATE

## 项目结构

```
operators/
├── __init__.py           # 模块导出
├── base.py               # 操作符基类和上下文
├── registry.py           # 操作符注册中心
├── builtin/              # 内置操作符
│   ├── __init__.py
│   ├── source.py         # 数据源操作符 (source)
│   ├── transform.py      # 转换操作符 (split, extract, map, unique, flatten)
│   ├── math.py           # 数学运算操作符 (math, round, floor, ceil)
│   ├── lookup.py         # 查找操作符 (lookup, where, get, sheet_exists)
│   ├── collection.py     # 集合操作符 (union, intersect, collect, sequential, previous)
│   └── validate.py       # 验证操作符 (eq, in, exists_in, all_exist_in)
```

## 操作符类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `SOURCE` | 数据源 | `source` |
| `TRANSFORM` | 数据转换 | `split`, `extract`, `map` |
| `LOOKUP` | 数据查找 | `lookup`, `where`, `get` |
| `COLLECTION` | 集合操作 | `union`, `intersect` |
| `AGGREGATE` | 聚合操作 | `collect`, `sequential`, `previous` |
| `VALIDATE` | 验证操作 | `eq`, `in`, `exists_in` |

## 内置操作符

### 数据源操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `source` | `"@row.X"` 或 `"@var"` | 从指定源获取数据 |
| `as` | `"var_name"` | 将当前值保存到变量 |
| `use` | `"@var_name"` | 使用变量 |

### 转换操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `split` | `"\|"` | 按分隔符分割字符串 |
| `extract` | `":0"` | 提取复合值的部分 |
| `count` | - | 计算列表元素个数 |
| `unique` | `true` | 去重 |
| `flatten` | `true` | 扁平化嵌套列表 |
| `slice` | `3` | 取前N个元素 |
| `to_number` | - | 转换为数字 |
| `sum` | - | 求和 |
| `filter` | `{type: "regex", pattern: "^Prop"}` | 过滤数组元素（支持regex/prefix/suffix） |

### 数学运算操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `math` | `{op: "add", value: 1}` | 数学运算（add/sub/mul/div）|
| `round` | `2` | 四舍五入到指定小数位 |
| `floor` | - | 向下取整 |
| `ceil` | - | 向上取整 |

### 查找操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `lookup` | `"ref[id].col"` | 跨表查找 |
| `where` | `"level == 1"` | 条件过滤 |
| `get` | `"field_name"` | 获取记录属性 |
| `exists_in` | `"ref.id"` | 存在于集合验证 |
| `sheet_exists` | `"Sheet({value})"` | Sheet存在检查 |
| `row_count` | `{sheet: "...", skip_rows: N}` | 获取Sheet行数 |

### 集合操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `union` | `["@var1", "@var2"]` | 集合并集 |
| `intersect` | `["@var1", "@var2"]` | 集合交集 |

### 聚合操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `collect` | `"key"` | 收集所有值（跨行验证） |
| `sequential` | `{prefix: "id", start_from: 1}` | 验证顺序累加 |
| `previous` | `{ref_column: "A", row_offset: 1}` | 验证等于上一行 |

### 验证操作符
| 操作符 | 配置 | 说明 |
|--------|------|------|
| `exists` | `true` | 存在验证 |
| `exists_in` | `"ref.id"` | 存在于集合 |
| `eq` | `"@expected"` 或值 | 等于验证 |
| `in` | `"@list"` | 包含验证 |
| `all_exist_in` | `"@target"` | 全存在验证 |
| `range_check` | `{min: 0, max: 100}` | 范围验证 |
| `regex_match` | `"^\d+$"` | 正则匹配 |
| `match_structure` | `{type: "regex", pattern: "^Prop"}` | 结构验证（支持regex/prefix/suffix，mode: each/single） |
| `same` | `"@target"` | 真假性一致验证 |
| `lt`/`lte`/`gt`/`gte` | `"@target"` 或值 | 比较验证 |

## 变量系统

Pipeline 支持变量存储和复用：
- `as: "var_name"` - 保存当前结果到变量
- `use: "@var_name"` - 使用变量作为输入

内置变量：
| 变量 | 说明 |
|------|------|
| `@value` | 当前单元格原始值 |
| `@row.X` | 同行第X列的值 |

## 关键文件路径

| 用途 | 路径 |
|------|------|
| 操作符基类 | `operators/base.py` |
| 注册中心 | `operators/registry.py` |
| 内置操作符 | `operators/builtin/` |
