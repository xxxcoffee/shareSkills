---
name: e-checker-v2
description: Excel 表格数据检查技能 V2。通过编写和执行 Python 脚本来验证 Excel 表数据及 Sheet 之间的关系，并生成检查报告。适用于：数据校验、表间关系验证、数据完整性检查、字段格式验证等场景。当用户提到"检查表格"、"验证 Excel"、"数据检查"、"sheet 关系检查"、"e-checker-v2"、"checker-rule"，或者提供了 checker-rule.md 规则文件、.e-checker 脚本目录时，务必使用此技能。即使只是需要快速检查某个 Excel 的列值是否符合规则，也应该使用。
---

# E-Checker: Excel 表格数据检查技能

## 概览

本技能通过以下步骤系统化地检查 Excel 表格数据：

1. **分析需求** — 从 checker-rule.md 文件或用户描述中提取检查规则
2. **匹配现有脚本** — 检查 `.e-checker/` 目录是否已有对应脚本
3. **字段对齐验证** — 确认脚本中的字段引用与实际表格列名一致
4. **执行并报告** — 运行脚本，生成结构化检查报告

> ★ 提示：如果需求来自文件，需逐行解析文件中的每一条规则并实现检查。

## 步骤 1: 分析需求

### 需求来源

需求可能来自两个渠道，按优先级：

1. **规则文件** (`checker-rule.md`) — 最常见的需求来源。该文件通常位于工作目录根路径，逐行列出检查需求。
2. **用户描述** — 用户直接口头描述需要检查的内容。

### 操作方法

```bash
# 查找规则文件
find . -name "checker-rule.md" -maxdepth 2

# 读取规则文件
cat checker-rule.md
```

读取后，**逐行解析**每条规则，将其转化为具体的检查逻辑：
- 涉及哪个 Excel 文件？
- 涉及哪个 Sheet？
- 检查哪个/哪些列？
- 检查条件是什么（格式、范围、关联、唯一性等）？

将解析后的规则整理为清单，等待用户确认或直接进入下一步。

## 步骤 2: 检查现有脚本

所有 Python 检查脚本统一存储在 `.e-checker/` 目录（工作目录下的隐藏文件夹）。

```bash
# 查看已有脚本
ls .e-checker/

# 查看脚本内容
cat .e-checker/<script_name>.py
```

### 匹配逻辑

将步骤 1 中解析的规则与已有脚本进行对照：
- 脚本是否覆盖了该规则？
- 脚本的检查逻辑是否正确表达了规则要求？

如果某个规则已有对应脚本，进入步骤 3 验证；如果没有，需要新建脚本。

## 步骤 3: 字段对齐验证

**这是最容易出错的环节** — 脚本中硬编码的列名可能因 Excel 版本更新而失效。

### 操作方法

```bash
# 使用脚本快速查看 Excel 的 Sheet 和列名
python scripts/explorer.py <excel_path>
```

该脚本会输出所有 Sheet 名称及其列名。将其与检查脚本中引用的列名逐一对比，确保：
- 引用的 Sheet 存在
- 引用的列名拼写完全一致（包括大小写、空格）
- 没有遗漏新增的必要列

如果发现不匹配，**必须先修复脚本**再执行。

## 步骤 4: 执行脚本并生成报告

### 执行检查脚本

```bash
# 执行单个检查脚本
python .e-checker/<script_name>.py

# 执行全部检查脚本
python scripts/run_all.py
```

### 报告格式

每个检查脚本应输出结构化报告，格式如下：

```
====================================
检查报告: <脚本名称>
====================================
数据源: <Excel 文件路径>
Sheet: <Sheet 名称>
检查时间: <时间戳>
------------------------------------
总记录数: XXX
通过: XXX
失败: XXX
失败率: X.XX%
------------------------------------
失败详情:
  行号 | 字段 | 期望值 | 实际值 | 原因
  ...
====================================
```

脚本应当：
- 使用 `openpyxl` 读取 `.xlsx` 文件（保留格式信息）
- 使用 `pandas` 进行数据处理和批量检查
- 将检查结果同时打印到控制台和保存为 `.e-checker/reports/` 下的报告文件

## 脚本编写规范

### 依赖

```python
import openpyxl  # 用于读取 Excel 文件结构和格式
import pandas as pd  # 用于数据处理和检查逻辑
```

### 目录约定

```
.e-checker/
├── *.py              # 检查脚本
├── reports/          # 检查报告输出
│   └── <script>_<timestamp>.txt
└── README.md         # 脚本说明（可选）
```

### 脚本模板

每个检查脚本应遵循以下结构：

```python
"""
检查描述: <一句话说明检查目的>
对应规则: <checker-rule.md 中的规则编号或描述>
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# === 配置 ===
EXCEL_PATH = Path("path/to/file.xlsx")
SHEET_NAME = "Sheet1"
REPORTS_DIR = Path(".e-checker/reports")

def check_<rule_name>(df: pd.DataFrame) -> list[dict]:
    """
    执行具体的检查逻辑。
    返回: 失败记录列表，每项包含行号、字段、期望值、实际值、原因
    """
    failures = []
    # 实现检查逻辑
    return failures

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 读取数据
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, engine='openpyxl')
    
    # 执行检查
    failures = check_<rule_name>(df)
    
    # 输出报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"<script>_{timestamp}.txt"
    # ... 打印并保存报告

if __name__ == "__main__":
    main()
```

## 工具脚本

- `scripts/explorer.py` — 快速查看 Excel 文件的 Sheet 列表和列名，用于字段对齐
- `scripts/run_all.py` — 批量执行 `.e-checker/` 下所有检查脚本
- `scripts/template.py` — 新检查脚本的模板，可复制使用

## 常见检查类型参考

| 类型 | 说明 | 示例 |
|------|------|------|
| 列存在性 | 必需的列是否存在 | `assert '主键字段' in df.columns` |
| 非空检查 | 关键列不能为空/NaN | `df[df['必填字段'].isna()]` |
| 格式检查 | 值必须符合特定格式 | 编号、邮箱、日期格式 |
| 范围检查 | 数值在合理范围内 | 数量 >= 0, 比例 0-100 |
| 唯一性检查 | 列值不能重复 | `df.duplicated(subset=['主键'])` |
| 关联检查 | Sheet 间外键关系 | 子表的外键必须在父表中存在 |
| 一致性检查 | 多列之间的逻辑关系 | 起始值 <= 终止值 |

## 注意事项

1. **字段名敏感性**: Excel 列名可能有前导/尾随空格，读取时建议使用 `.str.strip()` 清理
2. **多 Sheet 关联**: 跨 Sheet 检查时，分别读取后通过公共键关联
3. **大数据量**: 超过 10 万行时考虑使用 `openpyxl` 的 `read_only=True` 模式
4. **中文编码**: 文件名和列名可能包含中文，确保路径处理使用 `Path` 对象
5. **规则文件优先**: 当存在 `checker-rule.md` 时，以文件中的规则为准，用户的口头描述作为补充

