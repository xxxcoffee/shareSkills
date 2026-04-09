"""
检查脚本模板
复制此文件到 .e-checker/ 目录，按实际需求修改。

检查描述: <修改为一句检查目的描述>
对应规则: <修改为 checker-rule.md 中的规则描述>

注意: 脚本只需将 JSON 检查结果打印到 stdout，run_all.py 会捕获并汇总。
不再需要单独保存报告文件。
"""
import json
import pandas as pd
from pathlib import Path

# === 配置区 ===
# 修改为实际 Excel 文件路径
EXCEL_PATH = Path("path/to/file.xlsx")
SHEET_NAME = "Sheet1"

# 模块名（对应 checker-rule.md 中的模块标题，如 "梦幻岛检查"）
MODULE_NAME = "模块名称"

# 检查项描述（对应具体规则描述）
CHECK_NAME = "检查项描述"

# 涉及的文件列表
FILES = ["path/to/file.xlsx"]


def check_rule(df: pd.DataFrame) -> list[dict]:
    """
    执行具体的检查逻辑。

    参数:
        df: pandas DataFrame，已从 Excel 的指定 Sheet 读取

    返回:
        失败详情列表，每项包含:
            - file: 文件名（可选）
            - sheet: 页签名（可选）
            - row: 行号（可选）
            - column: 列名（可选）
            - expected: 期望值/条件（可选）
            - actual: 实际值（可选）
            - reason: 失败原因说明
    """
    failures = []

    # 清理列名（去除首尾空格）
    df.columns = df.columns.str.strip()

    # 示例: 检查某列是否为空
    # REQUIRED_COLUMN = '目标列名'
    # if REQUIRED_COLUMN not in df.columns:
    #     return [{'reason': f'缺少必要列: {REQUIRED_COLUMN}'}]
    #
    # empty_rows = df[df[REQUIRED_COLUMN].isna()]
    # for idx in empty_rows.index:
    #     failures.append({
    #         'sheet': SHEET_NAME,
    #         'row': idx + 2,
    #         'column': REQUIRED_COLUMN,
    #         'expected': '非空',
    #         'actual': '空值',
    #         'reason': f'{REQUIRED_COLUMN} 不能为空',
    #     })

    return failures


def main():
    if not EXCEL_PATH.exists():
        result = [{
            "module": MODULE_NAME,
            "check": CHECK_NAME,
            "status": "error",
            "error": f"Excel 文件不存在: {EXCEL_PATH}"
        }]
        print(json.dumps(result, ensure_ascii=False))
        return

    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, engine='openpyxl')

    failures = check_rule(df)

    if failures:
        result = [{
            "module": MODULE_NAME,
            "check": CHECK_NAME,
            "status": "fail",
            "files": FILES,
            "details": failures,
        }]
    else:
        result = [{
            "module": MODULE_NAME,
            "check": CHECK_NAME,
            "status": "pass",
            "files": FILES,
        }]

    # 只输出 JSON 到 stdout，由 run_all.py 统一汇总
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
