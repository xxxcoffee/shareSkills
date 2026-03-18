"""HTML报告生成器"""

from pathlib import Path
from typing import Union
from datetime import datetime

from echecker.types import ValidationReport, Severity
from echecker.reports.base import BaseReporter


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Excel配置检查报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 28px; margin-bottom: 10px; }
        .header .timestamp { opacity: 0.9; font-size: 14px; }

        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            padding: 20px;
            background: #f8f9fa;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .summary-card .number {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .summary-card .label { color: #666; font-size: 14px; }
        .summary-card.success .number { color: #28a745; }
        .summary-card.error .number { color: #dc3545; }
        .summary-card.warning .number { color: #ffc107; }
        .summary-card.info .number { color: #17a2b8; }

        .content { padding: 20px; }
        .section-title {
            font-size: 20px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
        }

        .error-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .error-table th,
        .error-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        .error-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
        }
        .error-table tr:hover { background: #f8f9fa; }
        .error-table .severity {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .severity-error {
            background: #fee2e2;
            color: #dc2626;
        }
        .severity-warning {
            background: #fef3c7;
            color: #d97706;
        }

        .no-errors {
            text-align: center;
            padding: 60px 20px;
            color: #28a745;
        }
        .no-errors svg {
            width: 80px;
            height: 80px;
            margin-bottom: 20px;
        }

        .filters {
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-btn {
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .filter-btn:hover,
        .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Excel配置检查报告</h1>
            <div class="timestamp">生成时间: {{timestamp}}</div>
        </div>

        <div class="summary">
            <div class="summary-card info">
                <div class="number">{{total_rules}}</div>
                <div class="label">总规则数</div>
            </div>
            <div class="summary-card info">
                <div class="number">{{total_cells}}</div>
                <div class="label">校验单元格</div>
            </div>
            <div class="summary-card success">
                <div class="number">{{passed}}</div>
                <div class="label">通过</div>
            </div>
            <div class="summary-card error">
                <div class="number">{{errors}}</div>
                <div class="label">错误</div>
            </div>
            <div class="summary-card warning">
                <div class="number">{{warnings}}</div>
                <div class="label">警告</div>
            </div>
        </div>

        <div class="content">
            {{content}}
        </div>

        <div class="footer">
            由 eChecker 生成 | 高性能Excel配置检查工具
        </div>
    </div>

    <script>
        function filterBySeverity(severity) {
            const rows = document.querySelectorAll('.error-table tbody tr');
            rows.forEach(row => {
                if (severity === 'all' || row.dataset.severity === severity) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });

            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""


class HtmlReporter(BaseReporter):
    """HTML报告生成器"""

    def generate(self, report: ValidationReport, output_path: Union[str, Path] = None) -> str:
        """生成HTML报告"""
        output_path = Path(output_path) if output_path else Path("validation_report.html")

        summary = report.summary

        # 生成错误表格
        if report.errors:
            error_rows = []
            for error in report.errors:
                severity_class = "severity-error" if error.severity == Severity.ERROR else "severity-warning"
                error_rows.append(f"""
                <tr data-severity="{error.severity.value}">
                    <td><span class="severity {severity_class}">{error.severity.value.upper()}</span></td>
                    <td>{error.sheet_name}</td>
                    <td><code>{error.cell_ref}</code></td>
                    <td>{error.message}</td>
                    <td>{error.expected if error.expected else '-'}</td>
                    <td>{error.actual if error.actual else '-'}</td>
                </tr>
                """)

            content = f"""
            <h2 class="section-title">❌ 发现问题 ({len(report.errors)}个)</h2>
            <div class="filters">
                <button class="filter-btn active" onclick="filterBySeverity('all')">全部</button>
                <button class="filter-btn" onclick="filterBySeverity('error')">仅错误</button>
                <button class="filter-btn" onclick="filterBySeverity('warning')">仅警告</button>
            </div>
            <table class="error-table">
                <thead>
                    <tr>
                        <th>严重程度</th>
                        <th>Sheet</th>
                        <th>单元格</th>
                        <th>消息</th>
                        <th>期望值</th>
                        <th>实际值</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(error_rows)}
                </tbody>
            </table>
            """
        else:
            content = """
            <div class="no-errors">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <h2>✅ 恭喜！未发现任何问题</h2>
                <p>所有校验规则均已通过，Excel数据符合预期。</p>
            </div>
            """

        # 渲染模板
        html = HTML_TEMPLATE.replace("{{timestamp}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html = html.replace("{{total_rules}}", str(summary.total_rules))
        html = html.replace("{{total_cells}}", str(summary.total_cells_checked))
        html = html.replace("{{passed}}", str(summary.passed_count))
        html = html.replace("{{errors}}", str(summary.error_count))
        html = html.replace("{{warnings}}", str(summary.warning_count))
        html = html.replace("{{content}}", content)

        output_path.write_text(html, encoding='utf-8')
        return str(output_path)
