#!/usr/bin/env python3
"""
修复损坏的 Excel (.xlsx) 文件
支持修复空 fill 标签等问题

使用方法:
    python fix_excel.py <输入文件> [输出文件]

示例:
    python fix_excel.py broken.xlsx          # 覆盖源文件（自动创建 .bak 备份）
    python fix_excel.py broken.xlsx fixed.xlsx  # 输出到指定文件
"""

import os
import re
import shutil
import sys
import zipfile


def fix_xlsx_empty_fills(filepath: str, output_path: str = None) -> str:
    """
    修复 xlsx 文件中的空 <fill/> 标签问题

    Args:
        filepath: 输入的 xlsx 文件路径
        output_path: 输出的修复文件路径，默认为输入文件路径加 _fixed 后缀

    Returns:
        修复后的文件路径
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 默认覆盖源文件，会先创建备份
    overwrite_mode = output_path is None
    if output_path is None:
        output_path = filepath

    # 确保输出目录存在
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 覆盖模式：创建备份
    backup_path = None
    if overwrite_mode:
        backup_path = filepath + '.bak'
        shutil.copy2(filepath, backup_path)
        print(f"📦 已创建备份: {backup_path}")

    temp_dir = '.temp_xlsx_fix'

    try:
        # 解压 xlsx（xlsx 实际上是 zip 格式）
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        styles_path = os.path.join(temp_dir, 'xl', 'styles.xml')
        if os.path.exists(styles_path):
            # 读取并修复 styles.xml
            with open(styles_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 替换空的 <fill/> 或 <fill></fill> 标签为有效的 PatternFill
            content = re.sub(
                r'<fill\s*/>',
                '<fill><patternFill patternType="none"/></fill>',
                content
            )
            # 同时处理 <fill></fill> 空标签
            content = re.sub(
                r'<fill>\s*</fill>',
                '<fill><patternFill patternType="none"/></fill>',
                content
            )

            with open(styles_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ 已修复 styles.xml 中的空 fill 标签")
        else:
            print(f"⚠️ 未找到 styles.xml，可能不是标准的 xlsx 文件")

        # 重新打包为 xlsx
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        if overwrite_mode:
            print(f"✅ 修复完成，已覆盖原文件")
        else:
            print(f"✅ 修复完成: {output_path}")
        return output_path

    finally:
        # 清理临时文件
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n❌ 错误: 缺少输入文件路径")
        print("用法: python fix_excel.py <输入文件> [输出文件]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # 检查文件扩展名
    if not input_file.lower().endswith('.xlsx'):
        print(f"⚠️ 警告: 输入文件 '{input_file}' 不是 .xlsx 格式")
        confirm = input("是否继续? (y/n): ")
        if confirm.lower() != 'y':
            sys.exit(0)

    try:
        result = fix_xlsx_empty_fills(input_file, output_file)
        print(f"\n🎉 文件修复成功!")
        if output_file is None:
            print(f"   原文件: {input_file}")
            print(f"   备份: {input_file}.bak")
        else:
            print(f"   输入: {input_file}")
            print(f"   输出: {result}")
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
