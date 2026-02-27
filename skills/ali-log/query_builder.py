"""
阿里云日志查询构建器
提供便捷的查询构建功能，支持查询语句和SQL分析语句的构建
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union


class QueryBuilder:
    """日志查询语句构建器"""

    def __init__(self):
        self._conditions = []
        self._query = "*"

    def keyword(self, keyword: str) -> "QueryBuilder":
        """添加关键词查询"""
        self._conditions.append(keyword)
        return self

    def field(self, field_name: str, value: Any, operator: str = ":") -> "QueryBuilder":
        """
        添加字段查询

        Args:
            field_name: 字段名
            value: 字段值
            operator: 操作符 (:, >, >=, <, <=, =)
        """
        if isinstance(value, str):
            # 如果值包含空格或特殊字符，使用双引号包裹
            if any(c in value for c in [' ', ':', '-', '"', "'", '(', ')', '[', ']']):
                value = f'"{value}"'
        self._conditions.append(f"{field_name}{operator}{value}")
        return self

    def range_field(self, field_name: str, start: Union[int, float], end: Union[int, float]) -> "QueryBuilder":
        """添加范围查询（支持数值类型字段）"""
        self._conditions.append(f"{field_name} in [{start} {end}]")
        return self

    def time_range(self, from_time: datetime, to_time: Optional[datetime] = None) -> "QueryBuilder":
        """添加时间范围条件"""
        # 时间范围通常通过API参数传递，这里可以作为注释
        return self

    def and_(self) -> "QueryBuilder":
        """添加AND连接符"""
        if self._conditions:
            self._conditions.append("and")
        return self

    def or_(self) -> "QueryBuilder":
        """添加OR连接符"""
        if self._conditions:
            self._conditions.append("or")
        return self

    def not_(self) -> "QueryBuilder":
        """添加NOT连接符"""
        self._conditions.append("not")
        return self

    def wildcard(self, field_name: str, pattern: str) -> "QueryBuilder":
        """
        添加通配符查询

        Args:
            field_name: 字段名
            pattern: 通配符模式 (* 匹配任意字符，? 匹配单个字符)
        """
        self._conditions.append(f"{field_name}:{pattern}")
        return self

    def phrase(self, phrase: str) -> "QueryBuilder":
        """
        添加短语查询（精确匹配）

        Args:
            phrase: 要匹配的短语
        """
        self._conditions.append(f'#{phrase}')
        return self

    def exists(self, field_name: str) -> "QueryBuilder":
        """查询字段存在的日志"""
        self._conditions.append(f"{field_name}:*")
        return self

    def not_exists(self, field_name: str) -> "QueryBuilder":
        """查询字段不存在的日志"""
        self._conditions.append(f"not {field_name}:*")
        return self

    def build(self) -> str:
        """构建查询语句"""
        if not self._conditions:
            return "*"
        return " ".join(self._conditions)

    def __str__(self) -> str:
        return self.build()


class SQLBuilder:
    """SQL分析语句构建器"""

    def __init__(self, query: str = "*"):
        self._query = query
        self._select = []
        self._where = []
        self._group_by = []
        self._order_by = []
        self._limit = 100
        self._having = []

    def select(self, *fields: str) -> "SQLBuilder":
        """添加SELECT字段"""
        self._select.extend(fields)
        return self

    def select_count(self, alias: str = "count") -> "SQLBuilder":
        """添加COUNT(*)"""
        self._select.append(f"count(*) as {alias}")
        return self

    def select_sum(self, field: str, alias: str) -> "SQLBuilder":
        """添加SUM聚合"""
        self._select.append(f"sum({field}) as {alias}")
        return self

    def select_avg(self, field: str, alias: str) -> "SQLBuilder":
        """添加AVG聚合"""
        self._select.append(f"avg({field}) as {alias}")
        return self

    def select_max(self, field: str, alias: str) -> "SQLBuilder":
        """添加MAX聚合"""
        self._select.append(f"max({field}) as {alias}")
        return self

    def select_min(self, field: str, alias: str) -> "SQLBuilder":
        """添加MIN聚合"""
        self._select.append(f"min({field}) as {alias}")
        return self

    def select_distinct(self, field: str) -> "SQLBuilder":
        """添加DISTINCT字段"""
        self._select.append(f"distinct {field}")
        return self

    def select_time_series(
        self,
        time_field: str = "__time__",
        window: str = "1m",
        format_str: str = "%Y-%m-%d %H:%i:%s",
        padding: str = "0"
    ) -> "SQLBuilder":
        """
        添加时间序列字段

        Args:
            time_field: 时间字段
            window: 时间窗口 (如 1m, 5m, 1h)
            format_str: 时间格式
            padding: 缺失数据填充方式 (0, null, last, next, avg)
        """
        self._select.append(f"time_series({time_field}, '{window}', '{format_str}', '{padding}') as ts")
        return self

    def where(self, condition: str) -> "SQLBuilder":
        """添加WHERE条件"""
        self._where.append(condition)
        return self

    def where_time_range(
        self,
        from_time: datetime,
        to_time: Optional[datetime] = None,
        time_field: str = "__time__"
    ) -> "SQLBuilder":
        """添加时间范围条件"""
        from_ts = int(from_time.timestamp())
        if to_time:
            to_ts = int(to_time.timestamp())
            self._where.append(f"{time_field} >= {from_ts} and {time_field} <= {to_ts}")
        else:
            self._where.append(f"{time_field} >= {from_ts}")
        return self

    def where_today(self, time_field: str = "__time__") -> "SQLBuilder":
        """添加今天的时间范围"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.where_time_range(today, tomorrow, time_field)

    def where_yesterday(self, time_field: str = "__time__") -> "SQLBuilder":
        """添加昨天的时间范围"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        return self.where_time_range(yesterday, today, time_field)

    def where_last_hours(self, hours: int, time_field: str = "__time__") -> "SQLBuilder":
        """添加最近N小时的时间范围"""
        now = datetime.now()
        past = now - timedelta(hours=hours)
        return self.where_time_range(past, now, time_field)

    def group_by(self, *fields: str) -> "SQLBuilder":
        """添加GROUP BY字段"""
        self._group_by.extend(fields)
        return self

    def group_by_time(
        self,
        unit: str = "minute",
        time_field: str = "__time__",
        format_str: Optional[str] = None
    ) -> "SQLBuilder":
        """
        按时间分组

        Args:
            unit: 时间单位 (millisecond, second, minute, hour, day, week, month)
            time_field: 时间字段
            format_str: 格式化字符串
        """
        if format_str:
            time_expr = f"date_format(date_trunc('{unit}', {time_field}), '{format_str}')"
        else:
            time_expr = f"date_trunc('{unit}', {time_field})"
        self._select.append(f"{time_expr} as time")
        self._group_by.append("time")
        return self

    def order_by(self, field: str, desc: bool = True) -> "SQLBuilder":
        """添加ORDER BY"""
        direction = "desc" if desc else "asc"
        self._order_by.append(f"{field} {direction}")
        return self

    def limit(self, n: int) -> "SQLBuilder":
        """设置LIMIT"""
        self._limit = n
        return self

    def having(self, condition: str) -> "SQLBuilder":
        """添加HAVING条件"""
        self._having.append(condition)
        return self

    def build(self) -> str:
        """构建SQL语句"""
        sql_parts = []

        # SELECT
        if self._select:
            sql_parts.append(f"SELECT {', '.join(self._select)}")
        else:
            sql_parts.append("SELECT *")

        # FROM
        sql_parts.append("FROM log")

        # WHERE
        if self._where:
            sql_parts.append(f"WHERE {' AND '.join(self._where)}")

        # GROUP BY
        if self._group_by:
            sql_parts.append(f"GROUP BY {', '.join(self._group_by)}")

        # HAVING
        if self._having:
            sql_parts.append(f"HAVING {' AND '.join(self._having)}")

        # ORDER BY
        if self._order_by:
            sql_parts.append(f"ORDER BY {', '.join(self._order_by)}")

        # LIMIT
        sql_parts.append(f"LIMIT {self._limit}")

        sql = " ".join(sql_parts)
        return f"{self._query} | {sql}"

    def __str__(self) -> str:
        return self.build()


class QueryTemplates:
    """常用查询模板"""

    @staticmethod
    def error_logs(level_field: str = "level", error_levels: List[str] = None) -> str:
        """错误日志查询"""
        if error_levels is None:
            error_levels = ["ERROR", "FATAL", "CRITICAL"]
        conditions = " or ".join([f"{level_field}:{level}" for level in error_levels])
        return conditions

    @staticmethod
    def slow_requests(time_field: str = "request_time", threshold: float = 1.0) -> str:
        """慢请求查询"""
        return f"{time_field}>{threshold}"

    @staticmethod
    def status_code_range(start: int = 200, end: int = 299) -> str:
        """HTTP状态码范围查询"""
        return f"status in [{start} {end}]"

    @staticmethod
    def json_field(json_field_path: str, value: str) -> str:
        """JSON字段查询"""
        return f'{json_field_path}:"{value}"'

    @staticmethod
    def sql_pv_trend(
        time_field: str = "__time__",
        unit: str = "minute",
        format_str: str = "%H:%i"
    ) -> str:
        """PV趋势SQL"""
        return f"""* |
SELECT
    date_format(date_trunc('{unit}', {time_field}), '{format_str}') as time,
    count(*) as pv
GROUP BY time
ORDER BY time
LIMIT 10000"""

    @staticmethod
    def sql_top_urls(
        uri_field: str = "request_uri",
        top_n: int = 10
    ) -> str:
        """TOP URL访问统计"""
        return f"""* |
SELECT
    {uri_field},
    count(*) as pv
GROUP BY {uri_field}
ORDER BY pv desc
LIMIT {top_n}"""

    @staticmethod
    def sql_error_rate(
        status_field: str = "status",
        error_threshold: int = 500
    ) -> str:
        """错误率统计SQL"""
        return f"""* |
SELECT
    sum(CASE WHEN {status_field}>={error_threshold} THEN 1 ELSE 0 END) * 100.0 / count(*) as error_rate,
    count(*) as total
FROM log"""

    @staticmethod
    def sql_percentile(
        field: str,
        percentiles: List[int] = None
    ) -> str:
        """分位数统计"""
        if percentiles is None:
            percentiles = [50, 90, 99]
        parts = []
        for p in percentiles:
            parts.append(f"approx_percentile({field}, {p/100}) as p{p}")
        return f"* | SELECT {', '.join(parts)} FROM log"

    @staticmethod
    def sql_compare_today_yesterday(
        metric: str = "count(*)",
        alias: str = "pv"
    ) -> str:
        """今日与昨日对比"""
        return f"""* |
SELECT
    diff[1] as today,
    diff[2] as yesterday,
    diff[3] as ratio
FROM (
    SELECT compare({alias}, 86400) as diff
    FROM (
        SELECT {metric} as {alias}
        FROM log
    )
)"""

    @staticmethod
    def sql_ip_distribution(ip_field: str = "remote_addr") -> str:
        """IP地理分布"""
        return f"""* |
SELECT
    count(*) as c,
    ip_to_province({ip_field}) as province
GROUP BY province
LIMIT 100"""


class QueryOptimizer:
    """查询优化建议"""

    @staticmethod
    def optimize_time_range(query: str, max_hours: int = 24) -> List[str]:
        """
        检查并建议优化时间范围

        Returns:
            优化建议列表
        """
        suggestions = []
        suggestions.append(f"建议时间范围不要超过 {max_hours} 小时，以提高查询速度")
        return suggestions

    @staticmethod
    def optimize_group_by(fields: List[str]) -> List[str]:
        """
        建议GROUP BY优化

        Returns:
            优化建议列表
        """
        suggestions = []
        if len(fields) > 5:
            suggestions.append("GROUP BY字段过多可能影响性能，建议减少分组字段数量")
        return suggestions

    @staticmethod
    def suggest_approx_functions(field: str, function_type: str = "distinct") -> str:
        """
        建议使用近似函数代替精确函数

        Args:
            field: 字段名
            function_type: 函数类型 (distinct, percentile)
        """
        if function_type == "distinct":
            return f"approx_distinct({field})  # 比 count(distinct {field}) 更快"
        elif function_type == "percentile":
            return f"approx_percentile({field}, 0.99)  # 比 exact_percentile 更快"
        return ""

    @staticmethod
    def avoid_string_operations(field: str) -> str:
        """建议避免对字符串列进行分组"""
        return f"""# 避免对字符串列进行分组，性能较差:
# SELECT {field}, count(*) GROUP BY {field}

# 建议使用数值分组:
SELECT __time__ - __time__ % 3600 as time_bucket, count(*) GROUP BY time_bucket"""
