# e-checker

Excel Configuration Checker - Validate Excel data against YAML rule definitions.

## Overview

e-checker is a powerful Excel data validation tool that uses YAML-based rule files to verify data integrity. It features a flexible pipeline architecture with 25+ built-in operators for various validation scenarios.

## Features

- **YAML-Based Rules**: Define validation rules in human-readable YAML format
- **25+ Operators**: Rich set of operators for validation, transformation, lookup, and collection
- **Pipeline Architecture**: Chain multiple operations for complex validations
- **Cross-Sheet Validation**: Reference data from other sheets or files
- **Expression Support**: Use `${...}` syntax for dynamic calculations
- **Variable System**: Store and reuse intermediate results with `@variable` syntax
- **Detailed Reporting**: Get clear error messages with context

## Installation

```bash
# Copy to Claude Code skills directory
cp -r skills/e-checker ~/.claude/skills/
```

## Usage

### Basic Usage

```bash
# Default: use checker_rules.yaml in current directory
python validate.py

# Specify custom rule file
python validate.py rules.yaml

# Verbose output
python validate.py rules.yaml -v

# List all available operators
python validate.py --list-operators
```

### Rule File Structure

```yaml
version: "3.0"

# Define external data sources (optional)
refs:
  product_ref:
    file: "reference.xlsx"
    sheet: "ProductInfo"
    columns:
      id: "A"
      type: "D"
      level: "F"

# Validation rules
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_item_format"
    description: "Validate item format"
    validations:
      - pipeline:
          - source: "@value"
          - split: "|"
          - match_structure:
              type: "regex"
              pattern: "^(ItemA|ItemB|Category)"
              mode: "each"
        message: "Invalid item format"
```

## Operators

### Source Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `source` | Get value from cell | `source: "@row.H"` |
| `as` | Save to variable | `as: "var_name"` |
| `use` | Use variable | `use: "@var_name"` |

### Transform Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `split` | Split string | `split: "\|"` |
| `extract` | Extract part | `extract: {delimiter: ":", index: 0}` |
| `filter` | Filter array | `filter: {type: "regex", pattern: "^[A-Z]"}` |
| `map` | Map operation | `map: {operation: "strip"}` |
| `flatten` | Flatten nested list | `flatten` |
| `slice` | Slice array | `slice: 3` or `slice: {start: 1, end: 4}` |
| `trim` | Trim whitespace | `trim` |
| `to_number` | Convert to number | `to_number` |
| `count` | Count elements | `count` |
| `unique` | Remove duplicates | `unique: true` |
| `math` | Math operation | `math: {op: "+", value: 1}` |
| `round` | Round number | `round: 2` |
| `floor` | Floor value | `floor` |
| `ceil` | Ceiling value | `ceil` |
| `regex_extract` | Regex capture group extraction | `regex_extract: {pattern: "^Item(\\d+)$", group: 1}` |

### Lookup Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `lookup` | Cross-sheet lookup | `lookup: "ref[id].col"` |
| `where` | Filter with condition | `where: "level == 1"` |
| `get` | Get property | `get: "field_name"` |
| `row_count` | Get sheet row count | `row_count: {sheet: "Sheet1", skip_rows: 4}` |
| `sheet_exists` | Check sheet exists | `sheet_exists: "Sheet({value})"` |

### Collection Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `union` | Set union | `union: ["@var1", "@var2"]` |
| `intersect` | Set intersection | `intersect: ["@var1", "@var2"]` |

### Aggregate Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `collect` | Collect data across rows | `collect: "key"` |
| `sequential` | Sequential ID check | `sequential: {prefix: "id", start_from: 1}` |
| `previous` | Cross-row reference | `previous: {ref_column: "A"}` |
| `no_duplicate` | Cross-row uniqueness check | `no_duplicate` |

### Validation Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equal | `eq: 1` or `eq: "@row.D"` |
| `lt` / `lte` | Less than / or equal | `lt: 10` |
| `gt` / `gte` | Greater than / or equal | `gt: 0` |
| `ne` | Not equal | `ne: 0` |
| `all` | All satisfy | `all: [{lt: 10}]` |
| `same` | Same truthiness | `same: "@row.I"` |
| `in` | Contains | `in: "@list"` |
| `exists_in` | Exists in reference | `exists_in: "ref.id"` |
| `match_structure` | Pattern match | `match_structure: {type: "regex", pattern: "^[A-Z]"}` |
| `range_check` | Range validation | `range_check: {min: 0, max: 100}` |

## Variable Reference

| Syntax | Description | Example |
|--------|-------------|---------|
| `@value` | Current cell value | `source: "@value"` |
| `@row.X` | Same row, column X | `source: "@row.H"` |
| `@var_name` | Pipeline variable | `use: "@series_h"` |

## Expression Syntax

Use `${...}` for dynamic calculations:

```yaml
- eq: "${@row.A + @row.B * 2}"      # Math operations
- eq: "${len(@var)}"                 # Function calls
- eq: "${max(@row.A, @row.B, 100)}"  # Multi-argument functions
```

## Examples

### Validate Array Element Format

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_items"
    validations:
      - pipeline:
          - split: "|"
          - extract:
              delimiter: ":"
              index: 0
          - match_structure:
              type: "regex"
              pattern: "^(ItemA|ItemB|Category)"
              mode: "each"
        message: "Item must be ItemA, ItemB, or start with Category"
```

### Cross-Sheet Reference Validation

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_id_exists"
    validations:
      - pipeline:
          - exists_in: "product_ref.id"
        message: "ID does not exist in reference table"
```

### Numeric Range Validation

```yaml
rules:
  - target: "data.xlsx:Sheet1.B1:*"
    id: "check_percentage"
    validations:
      - pipeline:
          - to_number
          - range_check:
              min: 0
              max: 100
        message: "Value must be between 0 and 100"
```

### Sequential ID Validation

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_sequence"
    validations:
      - pipeline:
          - collect: "ids"
          - sequential:
              prefix: "item"
              start_from: 1
        message: "IDs must be sequential"
```

### Regex Capture Group Extraction

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_item_number"
    validations:
      - pipeline:
          - regex_extract:
              pattern: "^Item(\\d+)$"
              group: 1
          - eq: "${@row.B}"
        message: "Item number does not match column B"
```

### Cross-Row Uniqueness Validation

```yaml
rules:
  - target: "data.xlsx:Sheet1.A1:*"
    id: "check_unique_id"
    validations:
      - pipeline:
          - collect: "ids"
          - no_duplicate
        message: "Duplicate ID found"
```

## Project Structure

```
e-checker/
├── SKILL.md              # Skill definition for Claude Code
├── README.md             # This file
├── README_CN.md          # Chinese version
└── scripts/
    ├── validate.py       # Main validation script
    └── src/
        └── echecker/     # Core library
            ├── core/     # Engine implementation
            ├── operators/# Operator definitions
            ├── rules/    # Rule parser
            └── ...
```

## License

MIT License
