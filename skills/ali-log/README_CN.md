# ali-log

[English](./README.md) | 简体中文

阿里云日志服务（SLS）Claude Code 查询工具。

## 功能概述

阿里云日志服务（SLS）Python SDK 的封装，提供简单易用的日志查询功能。

**功能特性：**
- 拉取原始日志 (`pull_logs`)
- 查询分析日志 (`query_logs`)
- 通过时间获取游标 (`get_cursor`)
- 通过游标获取时间 (`get_cursor_time`)
- **查询构建器** - 便捷的查询语句构造
- **SQL 分析构建器** - 链式 SQL 语句构建
- **查询模板** - 常用查询场景模板
- **完整 SQL 函数参考** - 查看 [QUERY_REFERENCE.md](./QUERY_REFERENCE.md)

## 安装

### 前置要求

- Python 3.8+
- 阿里云账号并开通日志服务（SLS）

### 安装依赖

```bash
# 安装必要的包
pip install aliyun-log-python-sdk

# 或使用 requirements.txt
pip install -r requirements.txt
```

### 安装 Skill

```bash
# 复制到 Claude Code skills 目录
cp -r ali-log ~/.claude/skills/
```

## 配置说明

### 密钥配置（必填）

需要配置阿里云访问凭证，有两种方式：

#### 方式 1：环境变量（推荐）

```bash
# 添加到 ~/.bashrc、~/.zshrc 或 ~/.bash_profile
export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
export ALIBABA_CLOUD_LOG_ENDPOINT="cn-hangzhou.log.aliyuncs.com"
```

然后重新加载：
```bash
source ~/.bashrc  # 或 ~/.zshrc
```

#### 方式 2：直接传参

```python
from ali_log import AliLogClient

client = AliLogClient(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret",
    endpoint="cn-hangzhou.log.aliyuncs.com"
)
```

### 项目配置（可选）

可以设置默认项目和日志库，避免每次查询都指定：

#### 方式 1：环境变量

```bash
export ALIBABA_CLOUD_LOG_PROJECT="your-project-name"
export ALIBABA_CLOUD_LOG_LOGSTORE="your-logstore-name"
```

#### 方式 2：直接传参

```python
client = AliLogClient(
    endpoint="cn-hangzhou.log.aliyuncs.com",
    project="your-project-name",      # 默认项目
    logstore="your-logstore-name"     # 默认日志库
)
```

### 可用端点列表

| 地域 | 端点 |
|------|------|
| 华东1（杭州） | `cn-hangzhou.log.aliyuncs.com` |
| 华东2（上海） | `cn-shanghai.log.aliyuncs.com` |
| 华北2（北京） | `cn-beijing.log.aliyuncs.com` |
| 华南1（深圳） | `cn-shenzhen.log.aliyuncs.com` |
| 新加坡 | `ap-southeast-1.log.aliyuncs.com` |

### 获取阿里云凭证

1. 登录 [阿里云控制台](https://www.aliyun.com/)
2. 点击头像 → **AccessKey 管理**
3. 创建或使用现有的 AccessKey
4. 复制 `AccessKey ID` 和 `AccessKey Secret`

**⚠️ 安全提示：** 永远不要将 AccessKey 凭证提交到版本控制。使用环境变量或安全的密钥管理方案。

## 快速开始

### 基础用法

```python
from ali_log import AliLogClient

# 初始化客户端（从环境变量读取配置）
client = AliLogClient()

# 查询日志
logs = client.query_logs(
    project="my-project",
    logstore="app-logs",
    from_time="2024-01-01 00:00:00",
    to_time="2024-01-01 23:59:59",
    query="* | SELECT * FROM log LIMIT 100"
)

for log in logs:
    print(log.get_contents())
```

### 使用查询构建器

```python
from ali_log import AliLogClient
from query_builder import QueryBuilder, SQLBuilder, QueryTemplates

client = AliLogClient()

# 方式 1：QueryBuilder
qb = QueryBuilder()
query = (qb
    .field("level", "ERROR")
    .and_()
    .range_field("status", 500, 599)
    .build())

logs = client.query_logs(
    from_time="2024-01-01 00:00:00",
    to_time="2024-01-01 23:59:59",
    query=f"{query} | SELECT * FROM log LIMIT 100"
)

# 方式 2：SQLBuilder
sql = (SQLBuilder("level:ERROR")
    .select_count("error_count")
    .group_by_time("hour")
    .where_last_hours(24)
    .build())

result = client.query_logs(
    from_time="2024-01-01 00:00:00",
    to_time="2024-01-01 23:59:59",
    query=sql
)

# 方式 3：查询模板
sql = QueryTemplates.sql_pv_trend(unit="hour")
result = client.query_logs(
    from_time="2024-01-01 00:00:00",
    to_time="2024-01-01 23:59:59",
    query=sql
)
```

## API 参考

### AliLogClient 方法

| 方法 | 用途 | 适用场景 |
|------|------|----------|
| `pull_logs` | 拉取原始日志 | 实时消费、数据同步 |
| `query_logs` | 查询分析日志 | 日志检索、统计分析 |
| `get_cursor` | 获取时间游标 | 定位日志位置 |
| `list_shards` | 列出所有分区 | 了解 Logstore 结构 |
| `query_all_logs` | 查询所有日志 | 自动分页获取 |

### QueryBuilder 方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `field(name, value)` | 字段等于 | `field("status", 200)` |
| `range_field(name, from, to)` | 范围查询 | `range_field("status", 500, 599)` |
| `wildcard(name, pattern)` | 通配符匹配 | `wildcard("uri", "/api/*")` |
| `and_()` | AND 运算符 | - |
| `or_()` | OR 运算符 | - |

### SQLBuilder 方法

| 方法 | 说明 |
|------|------|
| `select_count(alias)` | SELECT count(*) |
| `select_sum(field, alias)` | SELECT sum(field) |
| `group_by_time(unit, format_str)` | GROUP BY time |
| `where_last_hours(hours)` | WHERE 时间过滤 |
| `order_by(field, direction)` | ORDER BY |
| `limit(n)` | LIMIT n |

## 常见问题

### 错误：endpoint is required

**解决：** 设置 `ALIBABA_CLOUD_LOG_ENDPOINT` 环境变量或传入 `endpoint` 参数。

### 错误：access_key_id is required

**解决：** 配置 `ALIBABA_CLOUD_ACCESS_KEY_ID` 环境变量。

### 错误：project is required / logstore is required

**解决：** 设置环境变量或在每次查询时传入：
```python
logs = client.query_logs(
    project="your-project",
    logstore="your-logstore",
    query="*"
)
```

### 查询返回空结果

**解决：** 扩大时间范围或检查日志是否正常产生：
```python
from datetime import datetime, timedelta

to_time = datetime.now()
from_time = to_time - timedelta(hours=1)  # 最近1小时

logs = client.query_logs(
    from_time=from_time.strftime('%Y-%m-%d %H:%M:%S'),
    to_time=to_time.strftime('%Y-%m-%d %H:%M:%S'),
    query="*"
)
```

## 使用示例

查看 [SKILL.md](./SKILL.md) 获取完整的使用示例，包括：
- 错误日志查询
- 实时日志消费
- 统计分析
- JSON 日志分析
- 性能分析
- 地理分布分析

## 参考文档

- [QUERY_REFERENCE.md](./QUERY_REFERENCE.md) - 完整 SQL 函数参考
- [阿里云 SLS 官方文档](https://help.aliyun.com/product/28958.html)

## 开源协议

MIT 协议 - 查看 [LICENSE](../../LICENSE) 了解详情。