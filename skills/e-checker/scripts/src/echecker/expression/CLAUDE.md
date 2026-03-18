# expression - 表达式引擎

## 模块概述

expression 包是 eChecker 的表达式引擎，负责解析和求值 Excel 相关的表达式语法。

支持完整的数学表达式、变量引用、函数调用和模板字符串。

## 架构设计

```
表达式文本 → Lexer(词法分析) → Tokens → Parser(语法分析) → AST → Evaluator(求值) → 结果
```

### 核心组件

| 文件 | 职责 |
|------|------|
| `lexer.py` | 词法分析，将表达式文本转换为 Token 列表 |
| `parser.py` | 语法分析，将 Token 列表解析为 AST |
| `ast_nodes.py` | 定义 AST 节点类型 |
| `evaluator.py` | 遍历 AST 并求值 |
| `context.py` | 表达式求值上下文，支持变量解析 |
| `exceptions.py` | 表达式求值异常定义 |

## 表达式语法

### 支持的语法元素

| 语法 | 示例 | 说明 |
|------|------|------|
| 单元格引用 | `Sheet1.A1` | 引用指定工作表的单元格 |
| 单元格范围 | `Sheet1.A1:B10` | 引用单元格范围 |
| 字符串 | `"text"` 或 `'text'` | 字符串字面量 |
| 数字 | `123`, `3.14` | 整数或浮点数 |
| 变量引用 | `@value`, `@row.A`, `@var_name` | 当前值、同行数据、变量 |
| 函数调用 | `func(args)` | 直接函数调用 |
| 管道操作 | `expr \| func(args)` | 将表达式结果传递给函数 |
| 算术运算 | `+`, `-`, `*`, `/`, `%`, `**` | 加减乘除、取模、幂运算 |
| 比较运算 | `==`, `!=`, `<`, `>`, `<=`, `>=` | 相等、大小比较 |
| 模板字符串 | `"prefix${expr}suffix"` | 表达式插值 |
| 查找操作 | `lookup(Sheet, column=N, where: {...})` | 条件查找 |

### 变量引用

| 变量 | 示例 | 说明 |
|------|------|------|
| `@value` | `@value > 100` | 当前单元格值 |
| `@row.X` | `@row.A + @row.B` | 同行第X列的值 |
| `@var_name` | `@total * 0.1` | Pipeline状态中的变量 |

### 算术运算符

| 运算符 | 优先级 | 示例 | 说明 |
|--------|--------|------|------|
| `**` | 1 (最高) | `2 ** 3` → 8 | 幂运算（右结合） |
| `+x`, `-x` | 2 | `-5`, `+3` | 一元正负号 |
| `*`, `/`, `%` | 3 | `a * b`, `a / b`, `a % b` | 乘除取模 |
| `+`, `-` | 4 | `a + b`, `a - b` | 加减（支持字符串拼接） |
| `\|` | 5 (最低) | `expr \| func` | 管道操作 |

### 比较运算符

| 运算符 | 示例 | 说明 |
|--------|------|------|
| `==` | `@value == 100` | 等于 |
| `!=` | `@value != 0` | 不等于 |
| `<` | `@value < 100` | 小于 |
| `>` | `@value > 0` | 大于 |
| `<=` | `@value <= 100` | 小于等于 |
| `>=` | `@value >= 0` | 大于等于 |

### 模板字符串

使用 `${...}` 语法在字符串中嵌入表达式：

```
"当前值是 ${@value}"
"总和: ${@row.A + @row.B}"
"结果: ${max(@value, 100)}"
```

### 内置函数

| 函数 | 示例 | 说明 |
|------|------|------|
| `len(x)` | `len(@value)` | 返回列表/字符串长度 |
| `abs(x)` | `abs(@value)` | 绝对值 |
| `max(a, b, ...)` | `max(1, 2, 3)` | 最大值 |
| `min(a, b, ...)` | `min(1, 2, 3)` | 最小值 |
| `sum(x)` | `sum([1, 2, 3])` | 求和 |

### 内置管道函数

| 函数 | 示例 | 说明 |
|------|------|------|
| `split` | `Sheet1.A1 \| split("\|")` | 按分隔符分割字符串 |
| `strip` | `Sheet1.A1 \| strip` | 去除首尾空白 |
| `lower` | `Sheet1.A1 \| lower` | 转换为小写 |
| `upper` | `Sheet1.A1 \| upper` | 转换为大写 |
| `len` | `@value \| len` | 返回列表/字符串长度 |
| `abs` | `@value \| abs` | 绝对值 |
| `sum` | `@list \| sum` | 求和 |
| `max` | `@list \| max` 或 `@list \| max(10)` | 最大值（可传额外参数） |
| `min` | `@list \| min` 或 `@list \| min(0)` | 最小值（可传额外参数） |

### 查找表达式

```
lookup(SheetName, column=3, where: {column1 in ("A", "B")})
```

- `SheetName`: 目标工作表名称
- `column=3`: 返回第 3 列的值
- `where`: 查询条件，`columnN` 表示第 N 列，`in` 表示包含于集合

## Lexer - 词法分析器

### TokenType 枚举

| Token 类型 | 说明 |
|------------|------|
| `CELL_REF` | Sheet.A1 |
| `CELL_RANGE` | Sheet.A1:B10 |
| `NUMBER` | 数字 |
| `STRING` | 字符串 |
| `IDENTIFIER` | 标识符 |
| `PIPE` | \| |
| `LPAREN/RPAREN` | () |
| `COMMA` | , |
| `EQUALS` | = |
| `PLUS` | + |
| `MINUS` | - |
| `COLON` | : |
| `IN` | in 关键字 |
| `WHERE` | where 关键字 |
| `COLUMN` | column 关键字 |
| `LBRACE/RBRACE` | {} |
| `DOLLAR` | $ |
| `EOF` | 结束标记 |
| **数学运算符** | |
| `STAR` | * (乘法) |
| `SLASH` | / (除法) |
| `PERCENT` | % (取模) |
| `DOUBLE_STAR` | ** (幂运算) |
| **比较运算符** | |
| `EQ` | == (等于) |
| `NE` | != (不等于) |
| `LT` | < (小于) |
| `GT` | > (大于) |
| `LE` | <= (小于等于) |
| `GE` | >= (大于等于) |

### 词法规则

1. **空白字符**: 自动跳过
2. **数字**: 整数或小数
3. **字符串**: 双引号或单引号包裹（支持转义）
4. **单元格引用**: `SheetName.ColumnRow` 格式
5. **单元格范围**: `SheetName.Start:End` 格式
6. **关键字**: `in`, `where`, `column`, `lookup` 区分大小写
7. **多字符运算符**: `**`, `==`, `!=`, `<=`, `>=` 优先匹配

## Parser - 语法分析器

### 语法优先级（从高到低）

```
expression    → comparison
comparison    → additive (("==" | "!=" | "<" | ">" | "<=" | ">=") additive)*
additive      → multiplicative (("+" | "-") multiplicative)*
multiplicative→ unary (("*" | "/" | "%") unary)*
unary         → ("+" | "-") unary | power
power         → postfix ("**" power)?          # 右结合
postfix       → primary ("(" args ")" | "|" IDENTIFIER ("(" args ")")?)*
primary       → CELL_REF | CELL_RANGE | NUMBER | STRING | IDENTIFIER | "(" expression ")"
              | lookup

lookup        → "lookup" "(" IDENTIFIER "," "column" "=" NUMBER ("," "where" ":" "{" conditions "}")? ")"
conditions    → (COLUMN "in" expression ("," COLUMN "in" expression)*)?
args          → expression ("," expression)*
```

### 模板字符串解析

解析器支持模板字符串语法 `${...}`：

```python
# 解析模板字符串
parser.parse_template("prefix${expr}suffix")

# 或使用 parse 方法自动检测
parser.parse("prefix${@value + 1}suffix")
```

### 函数调用语法

支持直接函数调用和管道调用两种方式：

```
# 直接调用
max(1, 2, 3)
len(@value)
abs(@row.A)

# 管道调用（函数接收左操作数作为第一个参数）
@list | max
@value | abs
@list | sum
```

## AST Nodes - 抽象语法树节点

所有 AST 节点继承自 `ASTNode` 基类，使用访问者模式实现求值。

### 节点类型

| 节点类 | 属性 | 说明 |
|--------|------|------|
| `CellRefNode` | `sheet`, `cell` | 单元格引用 |
| `CellRangeNode` | `sheet`, `start`, `end` | 单元格范围 |
| `LiteralNode` | `value` | 字面量（数字、字符串、变量引用） |
| `BinaryOpNode` | `op`, `left`, `right` | 二元操作（+、-、*、/、%、**、比较） |
| `UnaryOpNode` | `op`, `operand` | 一元操作（+、-、not） |
| `PipeNode` | `source`, `func_name`, `args` | 管道操作 |
| `LookupNode` | `sheet`, `column`, `conditions` | 查找操作 |
| `InConditionNode` | `column`, `values` | IN 条件 |
| `ArrayNode` | `elements` | 数组字面量 |
| `FunctionCallNode` | `func_name`, `args` | 函数调用 |
| `TemplateStringNode` | `parts` | 模板字符串（混合文本和表达式） |

## Evaluator - 表达式求值器

### 求值逻辑

| 节点类型 | 求值行为 |
|----------|----------|
| `CellRefNode` | 从 ExcelProvider 获取单元格值 |
| `CellRangeNode` | 获取范围内所有单元格值，返回列表 |
| `LiteralNode` | 直接返回字面量值，以 `@` 开头的字符串作为变量引用解析 |
| `BinaryOpNode` | 递归求值左右子节点，执行算术或比较操作 |
| `UnaryOpNode` | 递归求值操作数，执行一元操作（取正负、逻辑非） |
| `PipeNode` | 先求值 source，再应用管道函数 |
| `FunctionCallNode` | 求值所有参数，调用对应内置函数 |
| `TemplateStringNode` | 拼接模板各部分，表达式节点求值后转为字符串 |
| `LookupNode` | 遍历目标 sheet 所有行，匹配条件后返回指定列值 |
| `ArrayNode` | 求值所有元素，返回列表 |

### 变量解析

| 变量引用 | 解析来源 |
|----------|----------|
| `@value` | `context.cell_value` |
| `@row.X` | `context.row_data[X]` |
| `@var_name` | `context.pipeline_state[var_name]` |

### 算术运算

| 运算符 | 行为 | 类型检查 |
|--------|------|----------|
| `+` | 数字相加或字符串/列表拼接 | 数字或序列类型 |
| `-` | 数字相减 | 要求数字类型 |
| `*` | 数字相乘 | 要求数字类型 |
| `/` | 数字相除 | 要求数字类型，除数不为零 |
| `%` | 取模运算 | 要求数字类型，除数不为零 |
| `**` | 幂运算 | 要求数字类型 |

### 比较运算

| 运算符 | 行为 | 类型检查 |
|--------|------|----------|
| `==`, `!=` | 相等/不等比较 | 支持任意类型 |
| `<`, `>`, `<=`, `>=` | 大小比较 | 要求数字类型 |

### 内置函数

| 函数 | 参数 | 返回值 |
|------|------|--------|
| `len(x)` | 字符串、列表、元组、字典、集合 | 元素个数 |
| `abs(x)` | 数字 | 绝对值 |
| `max(a, b, ...)` 或 `max(iterable)` | 多个值或可迭代对象 | 最大值 |
| `min(a, b, ...)` 或 `min(iterable)` | 多个值或可迭代对象 | 最小值 |
| `sum(x)` | 可迭代对象（数字） | 求和 |

## EvalContext - 求值上下文

`EvalContext` 类提供表达式求值时的变量解析功能。

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `cell_value` | Any | 当前单元格值，对应 `@value` |
| `row_data` | Dict[str, Any] | 行数据字典，对应 `@row.X` |
| `variables` | Dict[str, Any] | 变量字典，对应 `@var_name` |

### 方法

| 方法 | 说明 |
|------|------|
| `resolve(name: str)` | 解析变量引用（`@value`, `@row.X`, `@var`） |
| `get_row_value(col_ref: str)` | 获取同行指定列的值 |
| `get_variable(name: str)` | 获取变量值 |
| `set_variable(name: str, value: Any)` | 设置变量值 |
| `from_operator_context(ctx)` | 从 OperatorContext 创建 EvalContext |

### 使用示例

```python
from echecker.expression.context import EvalContext

ctx = EvalContext(
    cell_value=100,
    row_data={"A": 1, "B": 2},
    variables={"total": 300}
)

ctx.resolve("@value")      # 100
ctx.resolve("@row.A")      # 1
ctx.resolve("@total")      # 300
```

## 异常处理

表达式引擎定义了专门的异常类，用于严格模式错误处理：

| 异常类 | 说明 | 触发场景 |
|--------|------|----------|
| `ExpressionError` | 基础异常 | 所有表达式异常的基类 |
| `ExpressionTypeError` | 类型错误 | 操作数类型不匹配 |
| `ExpressionZeroDivisionError` | 除零错误 | 除法或取模时除数为零 |
| `ExpressionNameError` | 未定义变量 | 引用未定义的变量 |
| `ExpressionValueError` | 值错误 | 值本身不合法或无法处理 |

### 使用示例

```python
from echecker.expression.exceptions import (
    ExpressionTypeError,
    ExpressionZeroDivisionError,
)

# 类型检查
if not isinstance(value, (int, float)):
    raise ExpressionTypeError(f"要求数字类型，实际为: {type(value).__name__}")

# 除零检查
if divisor == 0:
    raise ExpressionZeroDivisionError("除零错误")
```

## 使用示例

### 数学表达式

```python
from echecker.expression.lexer import Lexer
from echecker.expression.parser import ExpressionParser
from echecker.expression.evaluator import ExpressionEvaluator

# 解析表达式
text = "(@row.A + @row.B) * 0.1 + 100"
lexer = Lexer(text)
tokens = lexer.tokenize()
parser = ExpressionParser(tokens)
ast = parser.parse_expression()

# 求值
evaluator = ExpressionEvaluator(provider, context)
result = evaluator.evaluate(ast)
```

### 模板字符串

```python
# 在规则配置中使用模板字符串
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    validate:
      - eq: "当前值是 ${@value}，同行A列是 ${@row.A}"
```

### 函数调用

```python
# 直接调用
max(@row.A, @row.B, 100)
sum([1, 2, 3])

# 管道调用
@list | max
@value | abs
```

## 注意事项

1. **空值处理**: 管道函数对 `None` 值有保护处理
2. **列号转换**: 使用 `_col_letter()` 方法将数字列号转换为字母
3. **查找性能**: `lookup` 操作会遍历整个工作表，大数据集时需谨慎使用
4. **错误处理**: 解析错误抛出 `SyntaxError`，求值错误抛出 `ExpressionError` 子类
5. **严格类型检查**: 算术运算要求数字类型，比较运算要求类型兼容
6. **右结合幂运算**: `**` 运算符是右结合的，即 `2 ** 3 ** 2` = `2 ** (3 ** 2)` = 512
