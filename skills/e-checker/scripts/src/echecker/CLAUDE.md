# eChecker 主包

`echecker` 是项目的根包，提供 Excel 配置检查的核心功能。该包采用 V3 Pipeline 操作符架构。

## 常用命令

- `pytest tests/ -v` - 运行所有测试
- `black src/ tests/` - 代码格式化
- `ruff check src/ tests/` - 代码检查
- `mypy src/echecker/` - 类型检查
- `pip install -e ".[dev]"` - 安装开发依赖
- `python validate.py rules.yaml` - CLI 验证（YAML配置驱动）
- `python validate.py rules.yaml -v` - 显示详细验证信息
- `python validate.py --list-operators` - 列出所有操作符

## 包结构

```
echecker/
├── __init__.py          # 包版本信息
├── cli.py               # 命令行入口
├── types.py             # 共享类型定义（ErrorType, Severity等）
├── config/              # 配置管理（中央配置、规则合并）
├── core/                # 校验引擎（V3 Pipeline引擎）
├── excel/               # Excel文件操作和单元格引用解析
├── expression/          # 表达式引擎（lexer/parser/evaluator）
├── operators/           # V3 Pipeline操作符系统
├── reports/             # 报告生成（控制台/Excel/HTML）
├── rules/               # 规则解析（V3格式）
└── validators/          # V1校验器（保留兼容）
```

## YAML 配置驱动验证

V3 版本采用 YAML 完全驱动验证，规则文件指定验证什么文件、什么 Sheet、什么范围。

### Target 格式

```yaml
rules:
  - target: "file.xlsx:Sheet.range"   # 完整格式
  - target: "file:Sheet.range"        # 简写格式（自动补全 .xlsx）
```

示例：
```yaml
- target: "data.xlsx:Sheet1.A1:*"      # 验证 data.xlsx 的 Sheet1 表 A1 列
- target: "data:Sheet2.B2:*"           # 简写，自动补全为 data.xlsx
- target: "reference.xlsx:Product(Data).A1:*"  # 带括号的 Sheet 名
```

### 多文件验证

单个 YAML 文件可以配置多个 Excel 文件的验证规则，系统会自动按文件分组、逐个验证并合并报告。

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    # ... 验证规则
  - target: "reference.xlsx:Product(Data).A1:*"
    # ... 验证规则
```

## 架构概览

### V3 Pipeline 操作符架构

**核心流程：**
1. `V3RuleParser` 解析 YAML 为 `V3RuleSet`
2. `V3ValidationEngine` 初始化操作符注册表
3. 遍历规则，对每个单元格执行 Pipeline 验证
4. 操作符通过 `PipelineContext` 访问行数据和外部数据
5. 生成 `ValidationReport` 报告

### 内置操作符类型

| 操作符 | 类型 | 用途 |
|--------|------|------|
| `source` | SOURCE | 数据源 |
| `split` | TRANSFORM | 分割字符串 |
| `extract` | TRANSFORM | 提取子串/列表元素 |
| `map` | TRANSFORM | 列表映射 |
| `flatten` | TRANSFORM | 扁平化列表 |
| `slice` | TRANSFORM | 切片取子集 |
| `trim` | TRANSFORM | 去空格 |
| `to_number` | TRANSFORM | 转数字 |
| `lookup` | LOOKUP | 跨表查找 |
| `where` | LOOKUP | 条件过滤 |
| `get` | LOOKUP | 获取属性 |
| `row_count` | LOOKUP | 获取Sheet行数 |
| `count` | TRANSFORM | 计数 |
| `unique` | TRANSFORM | 去重 |
| `union` | COLLECTION | 并集 |
| `collect` | AGGREGATE | 收集数据 |
| `sequential` | AGGREGATE | 顺序验证 |
| `previous` | AGGREGATE | 跨行引用 |
| `eq` | VALIDATE | 等于验证 |
| `lt` | VALIDATE | 小于验证 |
| `lte` | VALIDATE | 小于等于验证 |
| `gt` | VALIDATE | 大于验证 |
| `gte` | VALIDATE | 大于等于验证 |
| `ne` | VALIDATE | 不等于验证 |
| `all` | VALIDATE | 全满足验证 |
| `same` | VALIDATE | 真假性一致验证 |
| `in` | VALIDATE | 包含验证 |
| `exists_in` | VALIDATE | 存在性验证 |
| `sheet_exists` | VALIDATE | Sheet存在 |

## 原子化设计理念

V3 Pipeline 架构的核心原则是**通过原子操作符的组合实现复杂需求，而非创建高度定制化的操作符**。

**设计原则：**
1. **单一职责**：每个操作符只做一件事（分割、提取、转换、验证）
2. **可组合性**：通过 Pipeline 将简单操作符串联成复杂流程
3. **通用性**：避免场景特定的操作符，优先考虑通用转换操作
4. **可测试性**：原子操作符易于单独测试

## 关键文件路径

| 用途 | 路径 |
|------|------|
| 操作符基类 | `operators/base.py` |
| V3引擎 | `core/engine_v3.py` |
| 规则解析 | `rules/v3_parser.py` |
| 操作符注册 | `operators/registry.py` |
| 单元格引用 | `excel/cell_ref.py` |
| 表达式解析 | `expression/parser.py` |

## 测试

- 单元测试：`tests/unit/`
- 集成测试：`tests/integration/`
- 测试固件：`tests/fixtures/`
- 使用 `pytest` 运行

## 依赖

- `openpyxl`: Excel 读写
- `pandas`: 外部数据管理
- `pyyaml`: YAML 解析
- `click`: CLI 框架
- `jinja2`: 报告模板
- `pydantic`: 类型验证

## 子包文档

- [config/CLAUDE.md](config/CLAUDE.md) - 配置管理
- [core/CLAUDE.md](core/CLAUDE.md) - 校验引擎
- [excel/CLAUDE.md](excel/CLAUDE.md) - Excel操作
- [expression/CLAUDE.md](expression/CLAUDE.md) - 表达式引擎
- [operators/CLAUDE.md](operators/CLAUDE.md) - Pipeline操作符系统
- [reports/CLAUDE.md](reports/CLAUDE.md) - 报告生成
- [rules/CLAUDE.md](rules/CLAUDE.md) - 规则系统
