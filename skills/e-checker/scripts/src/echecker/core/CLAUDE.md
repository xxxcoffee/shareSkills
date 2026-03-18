# core 模块 - V3 Pipeline 校验引擎核心

core 模块是 eChecker 项目的核心校验引擎，采用 V3 Pipeline 操作符架构。

## 文件结构

```
core/
├── __init__.py          # 模块导出（V3引擎）
└── engine_v3.py         # V3 Pipeline 校验引擎
```

## V3 引擎 (engine_v3.py)

### 特点
- **Pipeline 架构**: 通过 `Pipeline` 管理操作符执行流程
- **操作符注册表**: 使用 `OperatorRegistry` 管理所有操作符
- **外部数据源**: 支持 `refs` 定义的外部数据（跨文件引用）
- **Pipeline 上下文**: 操作符可访问同行其他列数据（`@row.X` 语法）
- **状态管理**: Pipeline 支持状态变量（`as: "var_name"`, `use: "@var_name"`）
- **内置操作符**: 支持 22+ 种操作符类型（含 filter、match_structure 等）
- **聚合验证**: 支持 `collect` + `sequential`/`previous` 跨行验证模式
- **动态范围**: 支持 `*` 标记自动检测数据末尾

### 主要类

#### `V3ValidationEngine`
基于 Pipeline 操作符架构的校验引擎。

**方法**:
| 方法 | 说明 |
|------|------|
| `validate(excel_path, ruleset)` | 执行校验，返回 `ValidationReport` |
| `_init_external_data(ruleset)` | 初始化外部数据源 |
| `_validate_rule(rule, context)` | 校验单条规则 |
| `_get_row_data(sheet, row)` | 获取整行数据 |
| `_get_actual_end_row(cell_range)` | 获取动态范围实际结束行号 |
| `_execute_pipeline(value, validations, context)` | 执行 Pipeline 验证 |

**内置操作符**:
| 操作符 | 类型 | 说明 |
|--------|------|------|
| `source` | SOURCE | 数据源操作符 |
| `split` | TRANSFORM | 字符串分割 |
| `extract` | TRANSFORM | 提取子串 |
| `map` | TRANSFORM | 映射转换 |
| `unique` | TRANSFORM | 去重 |
| `flatten` | TRANSFORM | 扁平化 |
| `count` | TRANSFORM | 计数 |
| `lookup` | LOOKUP | 跨表查找 |
| `where` | LOOKUP | 条件过滤 |
| `get` | LOOKUP | 获取属性 |
| `attribute_match` | LOOKUP | 属性匹配 |
| `sheet_exists` | LOOKUP | Sheet存在性检查 |
| `union` | COLLECTION | 集合并集 |
| `intersect` | COLLECTION | 集合交集 |
| `collect` | AGGREGATE | 数据收集 |
| `sequential` | AGGREGATE | 顺序ID验证 |
| `previous` | AGGREGATE | 跨行引用验证 |
| `exists` | VALIDATE | 存在性验证 |
| `exists_in` | VALIDATE | 存在于集合验证 |
| `eq` | VALIDATE | 等于验证 |
| `in` | VALIDATE | 包含验证 |
| `all_exist_in` | VALIDATE | 全存在验证 |
| `range_check` | VALIDATE | 范围检查 |
| `regex_match` | VALIDATE | 正则匹配 |
| `filter` | TRANSFORM | 数组过滤（支持regex/prefix/suffix） |
| `match_structure` | VALIDATE | 结构验证（支持regex/prefix/suffix，单值/数组模式） |

### 动态范围支持

V3 引擎支持在 target 中使用 `*` 标记动态检测数据末尾：

```yaml
rules:
  - target: "Sheet1.A5:*"  # 从A5开始，自动找到最后一个非空行
```

动态范围检测逻辑：
- 从指定的起始行开始向下扫描
- 遇到连续3个空行后停止
- 返回最后一个非空行的行号

### Pipeline 执行流程

Pipeline 支持状态变量：
- `as: "var_name"` - 保存当前结果到变量
- `use: "@var_name"` - 使用变量作为输入
- `@value` - 当前单元格原始值
- `@row.X` - 同行第X列的值

## V3 vs V2 对比

| 特性 | V2 (插件) | V3 (Pipeline) |
|------|----------|---------------|
| 架构 | 插件化 | Pipeline操作符 |
| 扩展方式 | 继承Plugin基类 | 继承Operator基类 |
| 配置复杂度 | 高（嵌套深） | 低（线性流程） |
| 可读性 | 一般 | 高（流程清晰） |
| 状态管理 | 有限 | 完整（变量系统） |
