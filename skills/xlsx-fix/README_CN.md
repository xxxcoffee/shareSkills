# xlsx-fix

Excel 文件修复工具，用于解决 openpyxl 读取时的 fill 标签错误。

## 功能概述

当使用 openpyxl 库读取 Excel (.xlsx) 文件时，如果遇到以下错误：

```
expected <class 'openpyxl.styles.fills.Fill'>
```

此工具可以自动修复该问题。

**功能特性：**
- 修复 `xl/styles.xml` 中的空 `<fill/>` 或 `<fill></fill>` 标签
- 自动创建 `.bak` 备份文件
- 支持命令行直接运行
- 支持作为 Python 模块导入使用

## 安装

### 安装 Skill

```bash
# 复制到 Claude Code skills 目录
cp -r xlsx-fix ~/.claude/skills/
```

## 使用方法

### 方式 1：命令行运行

```bash
# 修复文件（自动创建备份）
python scripts/fix_excel.py broken.xlsx

# 修复并输出到新文件
python scripts/fix_excel.py broken.xlsx fixed.xlsx
```

### 方式 2：作为 Python 模块导入

```python
import sys
sys.path.insert(0, "/path/to/xlsx-fix/scripts")
from fix_excel import fix_xlsx_empty_fills

# 修复文件
fixed_path = fix_xlsx_empty_fills("broken.xlsx")

# 使用 openpyxl 读取
import openpyxl
wb = openpyxl.load_workbook(fixed_path)
```

### 方式 3：在代码中自动处理错误

```python
import openpyxl
import subprocess
import sys
import os

def load_workbook_with_fix(file_path: str):
    """
    加载 Excel 文件，如果遇到 Fill 错误则自动修复
    """
    try:
        return openpyxl.load_workbook(file_path)
    except Exception as e:
        error_msg = str(e)
        if "expected <class 'openpyxl.styles.fills.Fill'>" in error_msg:
            print(f"检测到 Excel 文件格式错误，正在修复: {file_path}")

            # 调用修复脚本
            fix_script = "/path/to/xlsx-fix/scripts/fix_excel.py"
            result = subprocess.run(
                [sys.executable, fix_script, file_path],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("修复成功，重新加载文件...")
                return openpyxl.load_workbook(file_path)
            else:
                raise RuntimeError(f"修复失败: {result.stderr}")
        else:
            raise

# 使用
wb = load_workbook_with_fix("data.xlsx")
```

## 错误原因

这个错误通常发生在 Excel 文件的 `xl/styles.xml` 中存在空的 `<fill/>` 或 `<fill></fill>` 标签。某些工具生成的 Excel 文件可能包含这种不规范的格式，导致 openpyxl 无法正确解析。

## 修复原理

1. 将 xlsx 文件作为 zip 解压
2. 找到 `xl/styles.xml` 文件
3. 将空的 `<fill/>` 或 `<fill></fill>` 标签替换为有效的 `<fill><patternFill patternType="none"/></fill>`
4. 重新打包为 xlsx 文件
5. 自动创建 `.bak` 备份文件

## 注意事项

1. 修复脚本会自动创建 `.bak` 备份文件
2. 只支持 `.xlsx` 格式，不支持 `.xls` 或 `.xlsm`
3. 修复后的文件应该能被 openpyxl 正常读取
4. 如果修复后仍有问题，可以尝试手动检查 styles.xml 文件

## 开源协议

MIT 协议 - 查看 [LICENSE](../../LICENSE) 了解详情。
