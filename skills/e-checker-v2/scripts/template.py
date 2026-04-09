"""
检查脚本模板
复制此文件到 .e-checker/ 目录，按实际需求修改。

检查描述: <修改为一句检查目的描述>
对应规则: <修改为 checker-rule.md 中的规则引用>

注意: 脚本只需将检查报告打印到 stdout，run_all.py 会捕获并汇总。
不再需要单独保存报告文件。
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# === 配置区 ===
# 修改为实际 Excel 文件路径
EXCEL_PATH = Path("path/to/file.xlsx")
SHEET_NAME = "Sheet1"


def check_rule(df: pd.DataFrame) -> list[dict]:
    """
    执行具体的检查逻辑。

    参数:
        df: pandas DataFrame，已从 Excel 的指定 Sheet 读取

    返回:
        失败记录列表，每项包含:
            - row: 行号 (从1开始)
            - field: 字段名
            - expected: 期望值/条件
            - actual: 实际值
            - reason: 失败原因说明
    """
    failures = []

    # 清理列名（去除首尾空格）
    df.columns = df.columns.str.strip()

    # 示例: 检查某列是否为空
    # REQUIRED_COLUMN = '目标列名'
    # if REQUIRED_COLUMN not in df.columns:
    #     return [{'row': '-', 'field': REQUIRED_COLUMN,
    #              'expected': '列存在', 'actual': '列不存在',
    #              'reason': f'缺少必要列: {REQUIRED_COLUMN}'}]
    #
    # empty_rows = df[df[REQUIRED_COLUMN].isna()]
    # for idx in empty_rows.index:
    #     failures.append({
    #         'row': idx + 2,  # +2: pandas索引从0开始 + Excel表头占1行
    #         'field': REQUIRED_COLUMN,
    #         'expected': '非空',
    #         'actual': '空值',
    #         'reason': f'{REQUIRED_COLUMN} 不能为空',
    #     })

    return failures


def generate_report(failures: list[dict], total_rows: int, script_name: str) -> str:
    """生成格式化的检查报告文本。"""
    passed = total_rows - len(failures)
    fail_rate = len(failures) / total_rows * 100 if total_rows > 0 else 0

    lines = [
        f"数据源: {EXCEL_PATH}",
        f"Sheet: {SHEET_NAME}",
        f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-" * 60,
        f"总记录数: {total_rows}",
        f"通过: {passed}",
        f"失败: {len(failures)}",
        f"失败率: {fail_rate:.2f}%",
        "-" * 60,
    ]

    if failures:
        lines.append("失败详情:")
        lines.append(f"  {'行号':>6} | {'字段':<15} | {'期望':<15} | {'实际':<15} | 原因")
        lines.append(f"  {'-' * 6}-+-{'-' * 15}-+-{'-' * 15}-+-{'-' * 15}-+-")
        for f in failures:
            lines.append(
                f"  {str(f['row']):>6} | {str(f['field']):<15} | "
                f"{str(f['expected']):<15} | {str(f['actual']):<15} | {f['reason']}"
            )
    else:
        lines.append("全部通过")

    return "\n".join(lines)


def main():
    if not EXCEL_PATH.exists():
        print(f"[错误] Excel 文件不存在: {EXCEL_PATH}")
        return

    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, engine='openpyxl')
    total_rows = len(df)

    failures = check_rule(df)
    script_name = Path(__file__).stem
    report = generate_report(failures, total_rows, script_name)

    # 只输出到 stdout，由 run_all.py 统一汇总
    print(report)


if __name__ == "__main__":
    main()
