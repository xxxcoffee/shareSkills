# ali-log

English | [简体中文](./README_CN.md)

Alibaba Cloud Log Service (SLS) query tool for Claude Code.

## Overview

A Python SDK wrapper for Alibaba Cloud Log Service (SLS) that provides easy-to-use log query capabilities.

**Features:**
- Pull raw logs (`pull_logs`)
- Query and analyze logs (`query_logs`)
- Get cursor by time (`get_cursor`)
- Get time by cursor (`get_cursor_time`)
- **Query Builder** - Convenient query statement construction
- **SQL Analysis Builder** - Chainable SQL statement building
- **Query Templates** - Common query scenario templates
- **Complete SQL Function Reference** - See [QUERY_REFERENCE.md](./QUERY_REFERENCE.md)

## Installation

### Prerequisites

- Python 3.8+
- Alibaba Cloud account with Log Service (SLS) enabled

### Install Dependencies

```bash
# Install required packages
pip install aliyun-log-python-sdk

# Or use requirements.txt
pip install -r requirements.txt
```

### Install Skill

```bash
# Copy to Claude Code skills directory
cp -r ali-log ~/.claude/skills/
```

## Configuration

### Credential Configuration (Required)

You need to configure Alibaba Cloud access credentials. There are two ways:

#### Method 1: Environment Variables (Recommended)

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.bash_profile
export ALIBABA_CLOUD_ACCESS_KEY_ID="your-access-key-id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your-access-key-secret"
export ALIBABA_CLOUD_LOG_ENDPOINT="cn-hangzhou.log.aliyuncs.com"
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

#### Method 2: Direct Parameters

```python
from ali_log import AliLogClient

client = AliLogClient(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret",
    endpoint="cn-hangzhou.log.aliyuncs.com"
)
```

### Project Configuration (Optional)

You can set default project and logstore to avoid specifying them in every query:

#### Method 1: Environment Variables

```bash
export ALIBABA_CLOUD_LOG_PROJECT="your-project-name"
export ALIBABA_CLOUD_LOG_LOGSTORE="your-logstore-name"
```

#### Method 2: Direct Parameters

```python
client = AliLogClient(
    endpoint="cn-hangzhou.log.aliyuncs.com",
    project="your-project-name",      # Default project
    logstore="your-logstore-name"     # Default logstore
)
```

### Available Endpoints

| Region | Endpoint |
|--------|----------|
| China (Hangzhou) | `cn-hangzhou.log.aliyuncs.com` |
| China (Shanghai) | `cn-shanghai.log.aliyuncs.com` |
| China (Beijing) | `cn-beijing.log.aliyuncs.com` |
| China (Shenzhen) | `cn-shenzhen.log.aliyuncs.com` |
| Singapore | `ap-southeast-1.log.aliyuncs.com` |

### Getting Alibaba Cloud Credentials

1. Log in to [Alibaba Cloud Console](https://www.aliyun.com/)
2. Click your avatar → **AccessKey Management**
3. Create or use existing AccessKey
4. Copy `AccessKey ID` and `AccessKey Secret`

**⚠️ Security Note:** Never commit your AccessKey credentials to version control. Use environment variables or secure secret management.

## Quick Start

### Basic Usage

```python
from ali_log import AliLogClient

# Initialize client (reads from environment variables)
client = AliLogClient()

# Query logs
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

### Using Query Builder

```python
from ali_log import AliLogClient
from query_builder import QueryBuilder, SQLBuilder, QueryTemplates

client = AliLogClient()

# Method 1: QueryBuilder
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

# Method 2: SQLBuilder
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

# Method 3: Query Templates
sql = QueryTemplates.sql_pv_trend(unit="hour")
result = client.query_logs(
    from_time="2024-01-01 00:00:00",
    to_time="2024-01-01 23:59:59",
    query=sql
)
```

## API Reference

### AliLogClient Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| `pull_logs` | Pull raw logs | Real-time consumption, data sync |
| `query_logs` | Query and analyze logs | Log search, statistical analysis |
| `get_cursor` | Get time cursor | Locate log position |
| `list_shards` | List all shards | Understand Logstore structure |
| `query_all_logs` | Query all logs | Auto-pagination |

### QueryBuilder Methods

| Method | Description | Example |
|--------|-------------|---------|
| `field(name, value)` | Field equals | `field("status", 200)` |
| `range_field(name, from, to)` | Range query | `range_field("status", 500, 599)` |
| `wildcard(name, pattern)` | Wildcard match | `wildcard("uri", "/api/*")` |
| `and_()` | AND operator | - |
| `or_()` | OR operator | - |

### SQLBuilder Methods

| Method | Description |
|--------|-------------|
| `select_count(alias)` | SELECT count(*) |
| `select_sum(field, alias)` | SELECT sum(field) |
| `group_by_time(unit, format_str)` | GROUP BY time |
| `where_last_hours(hours)` | WHERE time filter |
| `order_by(field, direction)` | ORDER BY |
| `limit(n)` | LIMIT n |

## Troubleshooting

### Error: endpoint is required

**Solution:** Set the `ALIBABA_CLOUD_LOG_ENDPOINT` environment variable or pass `endpoint` parameter.

### Error: access_key_id is required

**Solution:** Configure `ALIBABA_CLOUD_ACCESS_KEY_ID` environment variable.

### Error: project is required / logstore is required

**Solution:** Either set environment variables or pass them in each query:
```python
logs = client.query_logs(
    project="your-project",
    logstore="your-logstore",
    query="*"
)
```

### Query returns empty results

**Solution:** Expand time range or check if logs are being produced:
```python
from datetime import datetime, timedelta

to_time = datetime.now()
from_time = to_time - timedelta(hours=1)  # Last 1 hour

logs = client.query_logs(
    from_time=from_time.strftime('%Y-%m-%d %H:%M:%S'),
    to_time=to_time.strftime('%Y-%m-%d %H:%M:%S'),
    query="*"
)
```

## Examples

See [SKILL.md](./SKILL.md) for comprehensive usage examples including:
- Error log queries
- Real-time log consumption
- Statistical analysis
- JSON log analysis
- Performance analysis
- Geographic distribution analysis

## Reference

- [QUERY_REFERENCE.md](./QUERY_REFERENCE.md) - Complete SQL function reference
- [Alibaba Cloud SLS Documentation](https://www.alibabacloud.com/help/en/sls/)

## License

MIT License - see [LICENSE](../../LICENSE) for details.