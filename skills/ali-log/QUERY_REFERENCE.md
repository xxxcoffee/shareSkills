# 阿里云日志服务(SLS) 查询参考手册

## 目录

1. [查询语法](#查询语法)
2. [SQL分析函数](#sql分析函数)
3. [常用查询示例](#常用查询示例)
4. [性能优化建议](#性能优化建议)

---

## 查询语法

### 基础语法结构

```
查询语句 | SQL分析语句
```

### 全文查询

| 语法 | 说明 | 示例 |
|------|------|------|
| `keyword` | 关键词查询 | `ERROR` |
| `word1 and word2` | AND查询 | `GET and 200` |
| `word1 or word2` | OR查询 | `GET or POST` |
| `not word` | NOT查询 | `not DEBUG` |
| `field:value` | 字段查询 | `status:200` |
| `field>value` | 大于 | `request_time>100` |
| `field in [a b]` | 范围查询 | `status in [200 299]` |

### 通配符查询

| 语法 | 说明 | 示例 |
|------|------|------|
| `prefix*` | 前缀匹配 | `cn-shanghai*` |
| `?ingle` | 单字符匹配 | `?hina` |
| `#"phrase"` | 短语精确匹配 | `#"user/login"` |

### JSON字段查询

```
# 简单JSON字段
user.id:12345

# 嵌套JSON字段
error.details.message:"connection timeout"

# 多层嵌套
service.metadata.labels.app:"nginx"
```

---

## SQL分析函数

### 聚合函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `count(*)` | 计数 | `count(*) as pv` |
| `sum(field)` | 求和 | `sum(bytes_sent)` |
| `avg(field)` | 平均值 | `avg(request_time)` |
| `max(field)` | 最大值 | `max(response_time)` |
| `min(field)` | 最小值 | `min(response_time)` |
| `count(distinct field)` | 去重计数 | `count(distinct user_id)` |
| `approx_distinct(field)` | 近似去重(更快) | `approx_distinct(ip)` |

### 字符串函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `concat(s1, s2)` | 字符串拼接 | `concat(method, ' ', uri)` |
| `split(str, delim)` | 字符串分割 | `split(path, '/')` |
| `split_part(str, delim, n)` | 获取第N部分 | `split_part(uri, '?', 1)` |
| `substr(str, start, len)` | 子字符串 | `substr(uri, 1, 10)` |
| `length(str)` | 字符串长度 | `length(user_agent)` |
| `lower(str)` / `upper(str)` | 大小写转换 | `lower(method)` |
| `trim(str)` | 去除空格 | `trim(message)` |
| `replace(str, old, new)` | 替换 | `replace(region, 'cn-', '')` |
| `strpos(str, sub)` | 查找位置 | `strpos(uri, '/api')` |

### JSON函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `json_parse(str)` | 解析JSON | `json_parse(message)` |
| `json_extract(json, path)` | 提取JSON值 | `json_extract(data, '$.user.name')` |
| `json_extract_scalar(json, path)` | 提取标量值 | `json_extract_scalar(log, '$.level')` |
| `json_extract_long(json, path)` | 提取整数 | `json_extract_long(log, '$.code')` |
| `json_extract_double(json, path)` | 提取浮点数 | `json_extract_double(log, '$.duration')` |
| `json_extract_bool(json, path)` | 提取布尔值 | `json_extract_bool(log, '$.success')` |
| `json_array_length(json)` | JSON数组长度 | `json_array_length(tags)` |
| `json_array_contains(arr, val)` | 数组包含 | `json_array_contains(roles, 'admin')` |

### 日期时间函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `from_unixtime(ts)` | 时间戳转时间 | `from_unixtime(__time__)` |
| `to_unixtime(time)` | 时间转时间戳 | `to_unixtime(now())` |
| `current_timestamp` | 当前时间 | `current_timestamp` |
| `current_date` | 当前日期 | `current_date` |
| `now()` | 当前时间戳 | `now()` |
| `date_format(time, format)` | 格式化时间 | `date_format(__time__, '%Y-%m-%d')` |
| `date_parse(str, format)` | 解析时间 | `date_parse('2024-01-01', '%Y-%m-%d')` |
| `date_trunc(unit, time)` | 截断时间 | `date_trunc('hour', __time__)` |
| `date_add(unit, n, time)` | 时间加减 | `date_add('day', -1, now())` |
| `date_diff(unit, t1, t2)` | 时间差 | `date_diff('hour', start, end)` |
| `year/month/day(time)` | 提取年月日 | `year(__time__)` |
| `hour/minute/second(time)` | 提取时分秒 | `hour(__time__)` |
| `day_of_week/time)` | 星期几 | `day_of_week(__time__)` |

**时间格式化说明：**

| 格式符 | 说明 | 示例 |
|--------|------|------|
| `%Y` | 4位年份 | 2024 |
| `%y` | 2位年份 | 24 |
| `%m` | 月份 | 01-12 |
| `%d` | 日期 | 01-31 |
| `%H` | 小时(24h) | 00-23 |
| `%h` | 小时(12h) | 01-12 |
| `%i` | 分钟 | 00-59 |
| `%s` | 秒 | 00-59 |

### IP函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `ip_to_province(ip)` | IP转省份 | `ip_to_province(remote_addr)` |
| `ip_to_city(ip)` | IP转城市 | `ip_to_city(client_ip)` |
| `ip_to_country(ip)` | IP转国家 | `ip_to_country(remote_addr)` |
| `ip_to_provider(ip)` | IP转运营商 | `ip_to_provider(remote_addr)` |

### 条件表达式

| 表达式 | 说明 | 示例 |
|--------|------|------|
| `CASE WHEN ... THEN ... END` | 条件判断 | `CASE WHEN status>=500 THEN 'error' ELSE 'ok' END` |
| `IF(cond, true_val, false_val)` | IF表达式 | `IF(status=200, 1, 0)` |
| `COALESCE(a, b, c)` | 返回第一个非null | `COALESCE(user_id, 'anonymous')` |
| `NULLIF(a, b)` | 相等返回null | `NULLIF(status, 200)` |
| `TRY(expr)` | 异常捕获 | `TRY(json_parse(data))` |

### 比较运算符

| 运算符 | 说明 | 示例 |
|--------|------|------|
| `=`, `!=`, `<>` | 等于/不等于 | `status = 200` |
| `>`, `<`, `>=`, `<=` | 大小比较 | `request_time > 100` |
| `BETWEEN ... AND ...` | 范围 | `status BETWEEN 200 AND 299` |
| `LIKE` | 模式匹配 | `uri LIKE '%/api/%'` |
| `IS NULL` / `IS NOT NULL` | null判断 | `user_id IS NOT NULL` |
| `IN` | 集合判断 | `status IN (200, 201, 204)` |

### 窗口函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `row_number()` | 行号 | `row_number() over (order by time)` |
| `rank()` | 排名 | `rank() over (order by pv desc)` |
| `lag(field, n)` | 前N行 | `lag(pv, 1) over (order by time)` |
| `lead(field, n)` | 后N行 | `lead(pv, 1) over (order by time)` |

### 时序分析函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `time_series(time, window, format, padding)` | 时序补全 | `time_series(__time__, '5m', '%H:%i', '0')` |
| `compare(field, seconds)` | 同比环比 | `compare(pv, 86400)` |

---

## 常用查询示例

### 1. 基础日志查询

```sql
-- 查询ERROR级别日志
level:ERROR

-- 查询特定状态码范围
status in [500 599]

-- 查询特定API路径
request_uri:/api/v1/users*

-- 组合条件
method:POST and status:200 and request_time>1000
```

### 2. PV/UV统计

```sql
-- 每分钟PV
* |
SELECT
    date_format(date_trunc('minute', __time__), '%H:%i') as time,
    count(*) as pv
GROUP BY time
ORDER BY time

-- 每小时UV (独立IP)
* |
SELECT
    date_format(date_trunc('hour', __time__), '%Y-%m-%d %H:00') as hour,
    approx_distinct(remote_addr) as uv
GROUP BY hour
ORDER BY hour
```

### 3. 错误分析

```sql
-- 错误率统计
* |
SELECT
    sum(IF(status>=500, 1, 0)) * 100.0 / count(*) as error_rate,
    count(*) as total
FROM log

-- 错误分类统计
status>=500 |
SELECT
    status,
    count(*) as error_count,
    round(count(*) * 100.0 / sum(count(*)) over(), 2) as percentage
GROUP BY status
ORDER BY error_count DESC

-- 每分钟错误数趋势
status>=500 |
SELECT
    date_format(date_trunc('minute', __time__), '%H:%i') as time,
    count(*) as error_count
GROUP BY time
ORDER BY time
```

### 4. 性能分析

```sql
-- 请求耗时分布
* |
SELECT
    CASE
        WHEN request_time < 100 THEN '<100ms'
        WHEN request_time < 500 THEN '100-500ms'
        WHEN request_time < 1000 THEN '500ms-1s'
        ELSE '>1s'
    END as duration_range,
    count(*) as count
GROUP BY duration_range

-- 平均响应时间趋势(按分钟)
* |
SELECT
    date_format(date_trunc('minute', __time__), '%H:%i') as time,
    round(avg(request_time), 2) as avg_time,
    round(max(request_time), 2) as max_time
GROUP BY time
ORDER BY time

-- 分位数统计
* |
SELECT
    approx_percentile(request_time, 0.5) as p50,
    approx_percentile(request_time, 0.9) as p90,
    approx_percentile(request_time, 0.99) as p99
FROM log
```

### 5. TopN统计

```sql
-- Top 10 访问接口
* |
SELECT
    split_part(request_uri, '?', 1) as path,
    count(*) as pv,
    round(avg(request_time), 2) as avg_time
GROUP BY path
ORDER BY pv DESC
LIMIT 10

-- Top 10 来源IP
* |
SELECT
    remote_addr,
    count(*) as pv,
    ip_to_city(remote_addr) as city
GROUP BY remote_addr
ORDER BY pv DESC
LIMIT 10

-- Top 10 慢请求
* |
SELECT
    request_uri,
    request_time,
    __time__
ORDER BY request_time DESC
LIMIT 10
```

### 6. 地理分布分析

```sql
-- 按省份统计
* |
SELECT
    ip_to_province(remote_addr) as province,
    count(*) as pv
GROUP BY province
ORDER BY pv DESC
LIMIT 20

-- 按国家和运营商
* |
SELECT
    ip_to_country(remote_addr) as country,
    ip_to_provider(remote_addr) as provider,
    count(*) as pv
GROUP BY country, provider
ORDER BY pv DESC
```

### 7. 同比环比分析

```sql
-- 今日PV与昨日对比
* |
SELECT
    diff[1] as today_pv,
    diff[2] as yesterday_pv,
    round((diff[3] - 1) * 100, 2) as growth_rate
FROM (
    SELECT compare(count(*), 86400) as diff
    FROM log
)

-- 本周与上周对比
* |
SELECT
    diff[1] as this_week,
    diff[2] as last_week,
    round((diff[3] - 1) * 100, 2) as growth_rate
FROM (
    SELECT compare(count(*), 604800) as diff
    FROM log
)
```

### 8. JSON日志分析

```sql
-- 提取JSON字段
* |
SELECT
    json_extract_scalar(message, '$.level') as level,
    json_extract_scalar(message, '$.service') as service,
    count(*) as count
GROUP BY level, service

-- 嵌套JSON查询
* |
SELECT
    json_extract_scalar(log, '$.user.id') as user_id,
    json_extract_scalar(log, '$.action.type') as action,
    count(*) as count
GROUP BY user_id, action

-- 数组字段查询
* |
SELECT
    json_array_contains(tags, 'important') as is_important,
    count(*) as count
GROUP BY is_important
```

### 9. 用户行为分析

```sql
-- 用户访问频次分布
* |
SELECT
    user_id,
    count(*) as visit_count,
    approx_distinct(request_uri) as unique_pages
GROUP BY user_id
HAVING visit_count > 10
ORDER BY visit_count DESC
LIMIT 100

-- 用户访问路径分析
* |
SELECT
    user_id,
    group_concat(request_uri order by __time__) as path,
    count(*) as steps
GROUP BY user_id
HAVING steps > 5
LIMIT 100
```

### 10. 实时监控查询

```sql
-- 最近5分钟错误数
__time__ > to_unixtime(now()) - 300 and status>=500 |
SELECT count(*) as error_count

-- 最近1分钟QPS
__time__ > to_unixtime(now()) - 60 |
SELECT count(*) / 60.0 as qps

-- 当前在线用户(按最近5分钟活跃)
__time__ > to_unixtime(now()) - 300 |
SELECT approx_distinct(user_id) as online_users
```

---

## 性能优化建议

### 1. 查询范围优化

```
✓ 推荐: 查询特定时间范围
__time__ > 1704067200 and __time__ < 1704153600

✗ 避免: 查询全量数据
* | SELECT ...
```

### 2. 索引字段查询

```
✓ 推荐: 使用已创建索引的字段
status:200 and method:GET

✗ 避免: 对未索引字段频繁查询
message:"specific error text"
```

### 3. GROUP BY优化

```sql
✓ 推荐: 使用数值分组，减少字符串操作
SELECT __time__ - __time__ % 3600 as hour, count(*)
GROUP BY hour

✗ 避免: 对字符串列进行分组
SELECT date_format(__time__, '%Y-%m-%d %H') as hour, count(*)
GROUP BY hour
```

### 4. 近似函数使用

```sql
✓ 推荐: 使用近似函数(大数据量时)
SELECT approx_distinct(user_id) as uv

✗ 避免: 精确去重(大数据量时慢)
SELECT count(distinct user_id) as uv
```

### 5. 避免生成字符串

```sql
✓ 推荐: 数值计算后格式化
SELECT __time__ - __time__ % 3600 as time_bucket
GROUP BY time_bucket

✗ 避免: 生成字符串后分组
SELECT date_format(__time__, '%Y-%m-%d %H:00') as time_str
GROUP BY time_str
```

### 6. 多列GROUP BY优化

```sql
✓ 推荐: 字典大的字段放前面
SELECT user_id, status, count(*)
GROUP BY user_id, status

✗ 避免: 字典小的字段放前面
SELECT status, user_id, count(*)
GROUP BY status, user_id
```

### 7. 子查询优化

```sql
✓ 推荐: 减少子查询层数
SELECT * FROM (
    SELECT user_id, count(*) as cnt
    FROM log
    GROUP BY user_id
) WHERE cnt > 10

✗ 避免: 多层嵌套子查询
```

---

## 注意事项

1. **时间戳单位**：`__time__` 字段是Unix时间戳，单位为秒
2. **字符串引号**：SQL中字符串用单引号 `'string'`，字段名用双引号 `"field"` 或不使用引号
3. **查询条件限制**：查询语句中建议不超过30个条件
4. **分页限制**：SQL分析不支持OFFSET，需要分页时使用LIMIT配合时间范围
5. **数据类型**：确保字段索引类型正确(text/double/long)，否则影响查询结果

---

## 参考资料

- [阿里云SLS官方文档](https://help.aliyun.com/zh/sls/)
- [查询语法文档](https://help.aliyun.com/zh/sls/query-syntax/)
- [SQL分析语法](https://help.aliyun.com/zh/sls/sql-syntax-and-functions/)
