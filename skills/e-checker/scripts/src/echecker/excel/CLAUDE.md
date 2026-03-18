# eChecker Excel 模块

`echecker.excel` 包负责 Excel 文件的读写操作和单元格引用解析。

## 核心功能

- **Excel 文件读取**：通过 `ExcelProvider` 类读取单元格、行列和范围数据
- **单元格引用解析**：`CellRef` 和 `CellRange` 类支持 Excel 风格的单元格地址解析
- **错误标注**：`ExcelAnnotator` 类可在原始 Excel 文件中标注验证错误

## 核心类

### ExcelProvider

Excel 数据提供器，封装 openpyxl 提供高级读取接口。

**主要方法**

| 方法 | 说明 | 示例 |
|------|------|------|
| `open()` | 打开 Excel 文件 | `provider.open()` |
| `close()` | 关闭 Excel 文件 | `provider.close()` |
| `get_sheet_names()` | 获取所有 Sheet 名称 | `['Sheet1', 'Sheet2']` |
| `get_cell_value(ref)` | 获取单元格值 | `get_cell_value("Sheet1.A1")` |
| `get_range_values(ref)` | 获取范围值字典 | `get_range_values("Sheet1.A1:B5")` |
| `get_column_values(sheet, col)` | 获取整列值列表 | `get_column_values("Sheet1", "A")` |
| `get_row_values(sheet, row)` | 获取整行值列表 | `get_row_values("Sheet1", 1)` |
| `find_cells(sheet, predicate)` | 条件查找单元格 | `find_cells("Sheet1", lambda v: v == "OK")` |
| `get_sheet_dimensions(sheet)` | 获取 Sheet 维度 | `(max_row, max_col)` |

### CellRef

单元格引用类，表示单个单元格的位置。

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `sheet` | str | 工作表名称 |
| `row` | int | 行号（从1开始） |
| `col` | int | 列号（从1开始，A=1） |

**静态方法**

| 方法 | 说明 |
|------|------|
| `CellRef._col_to_letter(col)` | 列号转字母（1→A, 27→AA） |
| `CellRef._letter_to_col(letter)` | 字母转列号（A→1, AA→27） |

### CellRange

单元格范围类，表示矩形区域。

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `sheet` | str | 工作表名称 |
| `start_row` | int | 起始行 |
| `start_col` | int | 起始列 |
| `end_row` | int | 结束行 |
| `end_col` | int | 结束列 |

**方法**

| 方法 | 说明 |
|------|------|
| `iterate()` | 迭代生成器，产出 (row, col) 元组 |
| `contains(row, col)` | 检查坐标是否在范围内 |
| `to_cell_refs()` | 转换为 CellRef 列表 |

### ExcelAnnotator

Excel 错误标注器，在原始文件中高亮错误单元格。

**标注样式**

| 严重级别 | 背景色 | 字体 |
|----------|--------|------|
| ERROR | 红色 (#FF6B6B) | 白色粗体 |
| WARNING | 黄色 (#FFD93D) | 默认 |

标注会添加包含错误信息的批注（Comment）。

## 单元格引用格式

### 支持的格式

| 类型 | 格式 | 示例 | 说明 |
|------|------|------|------|
| 单元格 | `Sheet.列字母行号` | `Sheet1.A1` | 单个单元格 |
| 范围 | `Sheet.起始:结束` | `Sheet1.A1:B10` | 固定范围 |
| 动态范围 | `Sheet.起始:*` | `Sheet1.A5:*` | 从A5到数据末尾 |
| 整列 | `Sheet.列:列` | `Sheet1.A:C` | 整列（默认1-10000行） |
| 整行 | `Sheet.行:行` | `Sheet1.1:10` | 整行（所有列） |

### 动态范围说明

使用 `*` 作为结束标记，系统会在验证时自动检测该列的实际数据行数：

```yaml
rules:
  - target: "Sheet1.A5:*"  # 从A5开始，自动找到最后一个非空行
```

动态范围检测逻辑：
- 从指定的起始行开始向下扫描
- 遇到连续3个空行后停止
- 返回最后一个非空行的行号

### 注意事项

- Sheet 名称和单元格地址用 `.` 分隔
- 列字母大小写不敏感（A 和 a 等价）
- 整列引用时默认行范围为 1-10000
- 整行引用时默认列范围为 1-16384（Excel 最大列数）

## 依赖项

- **openpyxl**: Excel 文件读写
- **pathlib**: 路径处理

## 错误处理

| 异常类型 | 触发条件 |
|----------|----------|
| `FileNotFoundError` | Excel 文件不存在 |
| `RuntimeError` | 文件未打开时访问数据 |
| `ValueError` | Sheet 不存在或单元格引用格式无效 |
