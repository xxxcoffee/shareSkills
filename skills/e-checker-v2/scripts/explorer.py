"""
Excel 结构查看器
用于快速查看 Excel 文件的 Sheet 列表和各 Sheet 的列名，
帮助对齐检查脚本中的字段引用。

用法:
    python scripts/explorer.py <excel_path>
"""
import sys
from pathlib import Path

import openpyxl
import pandas as pd


def explore_excel(excel_path: str | Path) -> None:
    path = Path(excel_path)
    if not path.exists():
        print(f"[错误] 文件不存在: {path}")
        return

    print(f"=" * 60)
    print(f"Excel 结构: {path}")
    print(f"=" * 60)

    # 使用 openpyxl 获取 Sheet 列表
    wb = openpyxl.load_workbook(path, read_only=True)
    sheet_names = wb.sheetnames
    print(f"\nSheet 列表 ({len(sheet_names)} 个):")
    for i, name in enumerate(sheet_names, 1):
        print(f"  {i}. {name}")
    wb.close()

    # 使用 pandas 读取每个 Sheet 的列名
    print()
    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(path, sheet_name=sheet_name, engine='openpyxl', nrows=0)
            columns = list(df.columns)
            print(f"--- Sheet: {sheet_name} ---")
            print(f"  列数: {len(columns)}")
            for col in columns:
                print(f"    - '{col}'")
            print()
        except Exception as e:
            print(f"--- Sheet: {sheet_name} ---")
            print(f"  [读取失败] {e}")
            print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/explorer.py <excel_path>")
        sys.exit(1)
    explore_excel(sys.argv[1])
