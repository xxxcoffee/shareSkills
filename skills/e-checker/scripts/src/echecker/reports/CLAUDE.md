# reports - 报告生成模块

## 模块概述

报告生成模块负责将校验结果输出为多种格式的报告，支持控制台、Excel标注、HTML美观三种输出形式。

## 架构设计

```
reports/
├── base.py              # 抽象基类 BaseReporter
├── console_reporter.py  # 控制台报告 ConsoleReporter
├── excel_reporter.py    # Excel标注报告 ExcelReporter
├── html_reporter.py     # HTML美观报告 HtmlReporter
└── __init__.py          # 模块导出
```

## 核心类

### BaseReporter

报告生成器的抽象基类，定义统一接口。

## 报告生成器

### ConsoleReporter

控制台报告生成器，将校验结果输出到终端。

**特点：**
- 按 Sheet 分组显示错误
- 使用 emoji 图标区分严重程度（❌错误、⚠️警告）
- 显示期望值与实际值对比
- 自动打印到 stdout

### ExcelReporter

Excel 标注报告生成器，在原 Excel 文件中标注错误单元格并生成摘要 Sheet。

**特点：**
- 支持在原文件基础上标注（保留原有格式和数据）
- 错误单元格使用红色填充（#FF6B6B），警告使用黄色（#FFD93D）
- 为错误单元格添加批注（Comment）
- 自动创建 "ValidationReport" 摘要 Sheet

**构造函数：**
```python
ExcelReporter(source_excel: Union[str, Path] = None)
```
- `source_excel`: 源 Excel 文件路径，用于标注原文件；为 None 时创建新文件

### HtmlReporter

HTML 美观报告生成器，生成可交互的网页报告。

**特点：**
- 响应式设计，支持移动端查看
- 渐变色彩头部，卡片式摘要统计
- 交互式筛选：可按严重程度过滤
- 无错误时显示成功页面

**摘要卡片：**
- 总规则数（蓝色）
- 校验单元格数（蓝色）
- 通过数（绿色）
- 错误数（红色）
- 警告数（黄色）

## 根据场景选择报告类型

| 场景 | 推荐报告 | 原因 |
|------|----------|------|
| 命令行工具/CI | ConsoleReporter | 即时反馈，无需额外文件 |
| 给业务人员查看 | ExcelReporter | 在原文件上直观标注 |
| 存档/分享 | HtmlReporter | 美观，可交互，跨平台 |
| 自动化流程 | ExcelReporter | 便于下游处理标注文件 |

## 扩展指南

### 自定义报告生成器

继承 `BaseReporter` 实现新的报告格式。

## 相关类型

### ValidationReport

报告输入数据类型，包含校验结果。

| 属性 | 说明 |
|------|------|
| `errors` | 错误列表 |
| `summary` | 摘要统计 |

### ValidationError

单个错误记录。

| 属性 | 说明 |
|------|------|
| `rule_id` | 规则ID |
| `sheet_name` | Sheet名 |
| `cell_ref` | 单元格引用 |
| `error_type` | 错误类型 |
| `severity` | 严重程度 |
| `message` | 错误消息 |
| `expected` | 期望值 |
| `actual` | 实际值 |

### Severity

严重程度枚举：ERROR, WARNING

## 注意事项

1. **ExcelReporter 依赖 openpyxl**: 需要安装 `openpyxl>=3.0.0`
2. **批注长度限制**: Excel 单元格批注有长度限制，超长消息会被截断
3. **HTML 编码**: HtmlReporter 输出 UTF-8 编码文件
4. **线程安全**: 报告生成器无状态，可在多线程环境中复用实例
