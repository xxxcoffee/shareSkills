# 常见检查模式参考

## 1. 列存在性检查

```python
def check_columns_exist(df: pd.DataFrame, required_columns: list[str]) -> list[dict]:
    failures = []
    df.columns = df.columns.str.strip()
    for col in required_columns:
        if col not in df.columns:
            failures.append({
                'row': '-', 'field': col,
                'expected': '列存在', 'actual': '列不存在',
                'reason': f'缺少必要列: {col}'
            })
    return failures
```

## 2. 非空检查

```python
def check_not_null(df: pd.DataFrame, column: str) -> list[dict]:
    failures = []
    df.columns = df.columns.str.strip()
    if column not in df.columns:
        return [{'row': '-', 'field': column, 'expected': '列存在', 'actual': '列不存在', 'reason': f'列 {column} 不存在'}]
    empty_mask = df[column].isna() | (df[column].astype(str).str.strip() == '')
    for idx in df[empty_mask].index:
        failures.append({
            'row': idx + 2, 'field': column,
            'expected': '非空', 'actual': '空值',
            'reason': f'{column} 不能为空'
        })
    return failures
```

## 3. 格式检查（正则匹配）

```python
import re

def check_format(df: pd.DataFrame, column: str, pattern: str, description: str) -> list[dict]:
    failures = []
    df.columns = df.columns.str.strip()
    valid_mask = df[column].astype(str).str.match(pattern, na=False)
    invalid_mask = ~valid_mask & df[column].notna()
    for idx in df[invalid_mask].index:
        failures.append({
            'row': idx + 2, 'field': column,
            'expected': f'匹配格式: {description}', 'actual': str(df.at[idx, column]),
            'reason': f'{column} 格式不符合 {description}'
        })
    return failures

# 常用格式:
# 编码:  r'^[A-Z]{2,4}-\d{4,8}$'
# 邮箱:  r'^[\w\.-]+@[\w\.-]+\.\w+$'
# 日期:  r'^\d{4}-\d{2}-\d{2}$'
# 纯数字: r'^\d+$'
```

## 4. 数值范围检查

```python
def check_range(df: pd.DataFrame, column: str, min_val: float, max_val: float) -> list[dict]:
    failures = []
    df.columns = df.columns.str.strip()
    numeric = pd.to_numeric(df[column], errors='coerce')
    out_of_range = (numeric < min_val) | (numeric > max_val)
    for idx in df[out_of_range].index:
        failures.append({
            'row': idx + 2, 'field': column,
            'expected': f'{min_val} ~ {max_val}', 'actual': str(df.at[idx, column]),
            'reason': f'{column} 超出有效范围 [{min_val}, {max_val}]'
        })
    return failures
```

## 5. 唯一性检查

```python
def check_unique(df: pd.DataFrame, column: str) -> list[dict]:
    failures = []
    df.columns = df.columns.str.strip()
    duplicates = df[df.duplicated(subset=[column], keep='first')]
    for idx in duplicates.index:
        failures.append({
            'row': idx + 2, 'field': column,
            'expected': '唯一值', 'actual': str(df.at[idx, column]),
            'reason': f'{column} 值重复: {df.at[idx, column]}'
        })
    return failures
```

## 6. 跨 Sheet 关联检查（外键）

```python
def check_foreign_key(
    df_child: pd.DataFrame, child_col: str,
    df_parent: pd.DataFrame, parent_col: str,
    relation_name: str
) -> list[dict]:
    failures = []
    df_child.columns = df_child.columns.str.strip()
    df_parent.columns = df_parent.columns.str.strip()
    parent_values = set(df_parent[parent_col].dropna().unique())
    for idx, row in df_child.iterrows():
        if pd.notna(row[child_col]) and row[child_col] not in parent_values:
            failures.append({
                'row': idx + 2, 'field': child_col,
                'expected': f'在父表 {relation_name} 中存在', 'actual': str(row[child_col]),
                'reason': f'{child_col} 值在父表 {relation_name} 中不存在'
            })
    return failures
```

## 7. 多列一致性检查

```python
def check_consistency(df: pd.DataFrame, col_start: str, col_end: str) -> list[dict]:
    """检查 col_start 的值 <= col_end 的值（常用于日期范围）。"""
    failures = []
    df.columns = df.columns.str.strip()
    start = pd.to_datetime(df[col_start], errors='coerce')
    end = pd.to_datetime(df[col_end], errors='coerce')
    invalid = start > end
    for idx in df[invalid].index:
        failures.append({
            'row': idx + 2, 'field': f'{col_start}/{col_end}',
            'expected': f'{col_start} <= {col_end}',
            'actual': f'{df.at[idx, col_start]} > {df.at[idx, col_end]}',
            'reason': f'{col_start} 不能晚于 {col_end}'
        })
    return failures
```
