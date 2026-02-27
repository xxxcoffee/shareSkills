"""
阿里云日志服务(SLS) Python SDK封装
支持拉取原始日志、查询分析日志等功能
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from aliyun.log import LogClient, GetLogsRequest
from aliyun.log.logexception import LogException


class AliLogClient:
    """阿里云日志服务客户端封装"""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ):
        """
        初始化日志客户端

        Args:
            endpoint: 日志服务端点，默认从环境变量 ALIBABA_CLOUD_LOG_ENDPOINT 读取
            access_key_id: AccessKey ID，默认从环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID 读取
            access_key_secret: AccessKey Secret，默认从环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET 读取
            project: 默认Project名称，默认从环境变量 ALIBABA_CLOUD_LOG_PROJECT 读取
            logstore: 默认Logstore名称，默认从环境变量 ALIBABA_CLOUD_LOG_LOGSTORE 读取
        """
        self.endpoint = endpoint or os.environ.get('ALIBABA_CLOUD_LOG_ENDPOINT')
        self.access_key_id = access_key_id or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID')
        self.access_key_secret = access_key_secret or os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        self.default_project = project or os.environ.get('ALIBABA_CLOUD_LOG_PROJECT')
        self.default_logstore = logstore or os.environ.get('ALIBABA_CLOUD_LOG_LOGSTORE')

        if not self.endpoint:
            raise ValueError("endpoint is required, set ALIBABA_CLOUD_LOG_ENDPOINT env var or pass endpoint parameter")
        if not self.access_key_id:
            raise ValueError("access_key_id is required, set ALIBABA_CLOUD_ACCESS_KEY_ID env var or pass access_key_id parameter")
        if not self.access_key_secret:
            raise ValueError("access_key_secret is required, set ALIBABA_CLOUD_ACCESS_KEY_SECRET env var or pass access_key_secret parameter")

        self.client = LogClient(self.endpoint, self.access_key_id, self.access_key_secret)

    def _get_project(self, project: Optional[str] = None) -> str:
        """获取Project名称"""
        proj = project or self.default_project
        if not proj:
            raise ValueError("project is required, set ALIBABA_CLOUD_LOG_PROJECT env var or pass project parameter")
        return proj

    def _get_logstore(self, logstore: Optional[str] = None) -> str:
        """获取Logstore名称"""
        store = logstore or self.default_logstore
        if not store:
            raise ValueError("logstore is required, set ALIBABA_CLOUD_LOG_LOGSTORE env var or pass logstore parameter")
        return store

    def _time_to_timestamp(self, time_val: Union[str, int, float, datetime]) -> int:
        """
        将时间转换为Unix时间戳（秒）

        Args:
            time_val: 时间字符串、时间戳或datetime对象

        Returns:
            Unix时间戳（秒）
        """
        if isinstance(time_val, datetime):
            return int(time_val.timestamp())
        elif isinstance(time_val, (int, float)):
            return int(time_val)
        elif isinstance(time_val, str):
            # 尝试解析常见格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d',
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_val, fmt)
                    return int(dt.timestamp())
                except ValueError:
                    continue
            # 如果是纯数字，视为时间戳
            try:
                return int(float(time_val))
            except ValueError:
                raise ValueError(f"Cannot parse time: {time_val}")
        else:
            raise ValueError(f"Unsupported time type: {type(time_val)}")

    def list_shards(
        self,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        列出Logstore的所有分区

        Args:
            project: Project名称
            logstore: Logstore名称

        Returns:
            分区列表，每个分区包含shard_id、status等信息
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        response = self.client.list_shards(project, logstore)
        return response.get_shards_info()

    def get_cursor(
        self,
        shard_id: int,
        timestamp: Union[int, float, str, datetime],
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> str:
        """
        通过时间获取游标

        Args:
            shard_id: 分区ID
            timestamp: 时间（字符串、时间戳或datetime对象）
            project: Project名称
            logstore: Logstore名称

        Returns:
            游标字符串
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        if isinstance(timestamp, str) and timestamp in ['begin', 'end']:
            # 获取最早或最新的游标
            cursor_type = timestamp
            response = self.client.get_cursor(project, logstore, shard_id, cursor_type)
        else:
            ts = self._time_to_timestamp(timestamp)
            response = self.client.get_cursor(project, logstore, shard_id, ts)

        return response.get_cursor()

    def get_cursor_time(
        self,
        shard_id: int,
        cursor: str,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> int:
        """
        通过游标获取服务器端时间

        Args:
            shard_id: 分区ID
            cursor: 游标字符串
            project: Project名称
            logstore: Logstore名称

        Returns:
            Unix时间戳（秒）
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        response = self.client.get_cursor_time(project, logstore, shard_id, cursor)
        return response.get_cursor_time()

    def pull_logs(
        self,
        shard_id: int,
        cursor: str,
        count: int = 1000,
        end_cursor: Optional[str] = None,
        compress: bool = True,
        query: Optional[str] = None,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        拉取原始日志

        Args:
            shard_id: 分区ID
            cursor: 起始游标
            count: 返回的日志条数，默认1000
            end_cursor: 结束游标
            compress: 是否使用压缩，默认True
            query: 过滤语句（SPL语法）
            project: Project名称
            logstore: Logstore名称

        Returns:
            (日志列表, 下一页游标)
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        response = self.client.pull_logs(
            project_name=project,
            logstore_name=logstore,
            shard_id=shard_id,
            cursor=cursor,
            count=count,
            end_cursor=end_cursor,
            compress=compress,
            query=query
        )

        logs = []
        for log_group in response.get_flatten_logs():
            for log in log_group.get('logs', []):
                logs.append(log)

        next_cursor = response.get_next_cursor()
        return logs, next_cursor

    def query_logs(
        self,
        from_time: Union[int, float, str, datetime],
        to_time: Union[int, float, str, datetime],
        query: str = "*",
        offset: int = 0,
        limit: int = 100,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询分析日志（使用GetLogsV2接口）

        Args:
            from_time: 起始时间
            to_time: 结束时间
            query: 查询语句，支持SQL分析
            offset: 起始位置，用于分页
            limit: 返回条数，默认100，最大100
            project: Project名称
            logstore: Logstore名称

        Returns:
            日志列表
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        from_ts = self._time_to_timestamp(from_time)
        to_ts = self._time_to_timestamp(to_time)

        # 构建请求对象（新旧SDK都支持这种方式）
        request = GetLogsRequest(
            project=project,
            logstore=logstore,
            fromTime=from_ts,
            toTime=to_ts,
            query=query,
            offset=offset,
            line=limit
        )

        # 优先尝试新的get_logs_v2接口，如果不存在则使用get_logs
        if hasattr(self.client, 'get_logs_v2'):
            response = self.client.get_logs_v2(request)
        else:
            response = self.client.get_logs(request)

        return response.get_logs()

    def query_all_logs(
        self,
        from_time: Union[int, float, str, datetime],
        to_time: Union[int, float, str, datetime],
        query: str = "*",
        batch_size: int = 100,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        查询所有日志（自动分页）

        Args:
            from_time: 起始时间
            to_time: 结束时间
            query: 查询语句
            batch_size: 每批获取条数，默认100
            project: Project名称
            logstore: Logstore名称

        Returns:
            所有日志列表
        """
        all_logs = []
        offset = 0

        while True:
            logs = self.query_logs(
                from_time=from_time,
                to_time=to_time,
                query=query,
                offset=offset,
                limit=batch_size,
                project=project,
                logstore=logstore
            )

            if not logs:
                break

            all_logs.extend(logs)

            if len(logs) < batch_size:
                break

            offset += batch_size

        return all_logs

    def get_logstore_info(
        self,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取Logstore信息

        Args:
            project: Project名称
            logstore: Logstore名称

        Returns:
            Logstore信息
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        response = self.client.get_logstore(project, logstore)
        return {
            'name': response.get_name(),
            'ttl': response.get_ttl(),
            'shard_count': response.get_shard_count(),
            'enable_tracking': response.get_enable_tracking(),
            'auto_split': response.get_auto_split(),
            'max_split_shard': response.get_max_split_shard(),
            'append_meta': response.get_append_meta(),
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有Project

        Returns:
            Project列表
        """
        response = self.client.list_project()
        return response.get_projects()


# 便捷函数，方便直接使用

def create_client(
    endpoint: Optional[str] = None,
    access_key_id: Optional[str] = None,
    access_key_secret: Optional[str] = None,
    project: Optional[str] = None,
    logstore: Optional[str] = None
) -> AliLogClient:
    """
    创建阿里云日志客户端

    Args:
        endpoint: 日志服务端点
        access_key_id: AccessKey ID
        access_key_secret: AccessKey Secret
        project: 默认Project名称
        logstore: 默认Logstore名称

    Returns:
        AliLogClient实例
    """
    return AliLogClient(
        endpoint=endpoint,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        project=project,
        logstore=logstore
    )


def query_logs(
    from_time: Union[int, float, str, datetime],
    to_time: Union[int, float, str, datetime],
    query: str = "*",
    project: Optional[str] = None,
    logstore: Optional[str] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    便捷函数：查询日志

    Args:
        from_time: 起始时间
        to_time: 结束时间
        query: 查询语句
        project: Project名称
        logstore: Logstore名称
        **kwargs: 其他参数传递给AliLogClient

    Returns:
        日志列表
    """
    client = AliLogClient(**kwargs)
    return client.query_logs(
        from_time=from_time,
        to_time=to_time,
        query=query,
        project=project,
        logstore=logstore
    )
