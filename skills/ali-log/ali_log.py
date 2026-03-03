"""
阿里云日志服务(SLS) Python SDK封装
支持拉取原始日志、查询分析日志、日志下载任务等功能
"""

import os
import time
import json
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

        注意：如果需要查询的日志数量超过5000条，建议使用 create_download_job 创建日志下载任务，
        因为 query_logs 接口有数据量限制（单次最多返回100条，大量数据查询效率低且可能超时）。

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

            # 提醒：如果日志数量超过5000条，建议使用下载任务
            if len(all_logs) >= 5000:
                print(f"警告：已获取 {len(all_logs)} 条日志。如需获取更多日志，建议使用 create_download_job 创建日志下载任务。")

        return all_logs

    # ==================== 日志下载任务相关方法 ====================

    def create_download_job(
        self,
        name: str,
        from_time: Union[int, float, str, datetime],
        to_time: Union[int, float, str, datetime],
        query: str = "*",
        display_name: Optional[str] = None,
        description: str = "",
        content_type: str = "json",
        compression_type: str = "zstd",
        allow_incomplete: bool = True,
        power_sql: bool = False,
        oss_bucket: Optional[str] = None,
        oss_prefix: str = "sls-download/",
        role_arn: Optional[str] = None,
        project: Optional[str] = None,
        logstore: Optional[str] = None
    ) -> str:
        """
        创建日志下载任务

        适用于需要下载大量日志的场景（超过5000条），下载任务会将日志导出到OSS，然后通过OSS下载。
        支持的数据量：仅查询无限制，SQL分析最多支持100万行数据，数据量不超过2GB。

        Args:
            name: 下载任务名称（唯一标识）
            from_time: 起始时间
            to_time: 结束时间
            query: 查询语句，如 "*" 或 "* | SELECT * FROM log"
            display_name: 显示名称（可选，默认使用name）
            description: 任务描述
            content_type: 文件格式，可选 "json" 或 "csv"，默认 "json"
            compression_type: 压缩格式，可选 "zstd"(推荐)、"lz4"、"gzip"、"none"，默认 "zstd"
            allow_incomplete: 是否允许下载不精确结果，默认True
            power_sql: 是否启用powerSql，默认False
            oss_bucket: OSS存储桶名称（如果不填，需要后续从控制台下载）
            oss_prefix: OSS路径前缀，默认 "sls-download/"
            role_arn: 下载使用的RAM角色ARN，如 "acs:ram::123456789:role/aliyunlogdefaultrole"
            project: Project名称
            logstore: Logstore名称

        Returns:
            下载任务名称（job_name）

        Raises:
            ValueError: 参数校验失败
            LogException: API调用失败

        Example:
            >>> job_name = client.create_download_job(
            ...     name="my-download-job-001",
            ...     from_time="2024-01-01 00:00:00",
            ...     to_time="2024-01-01 23:59:59",
            ...     query="rid: 12345",
            ...     content_type="json",
            ...     compression_type="zstd",
            ...     oss_bucket="my-oss-bucket",
            ...     oss_prefix="logs/2024-01-01/"
            ... )
            >>> print(f"下载任务已创建: {job_name}")
        """
        project = self._get_project(project)
        logstore = self._get_logstore(logstore)

        # 参数校验
        if content_type not in ("json", "csv"):
            raise ValueError(f"content_type must be 'json' or 'csv', got {content_type}")
        if compression_type not in ("zstd", "lz4", "gzip", "none"):
            raise ValueError(f"compression_type must be 'zstd', 'lz4', 'gzip' or 'none', got {compression_type}")

        # 转换时间戳
        from_ts = self._time_to_timestamp(from_time)
        to_ts = self._time_to_timestamp(to_time)

        # 构建请求体
        body = {
            "name": name,
            "displayName": display_name or name,
            "description": description,
            "configuration": {
                "logstore": logstore,
                "fromTime": from_ts,
                "toTime": to_ts,
                "query": query,
                "powerSql": power_sql,
                "allowInComplete": allow_incomplete,
                "sink": {
                    "type": "AliyunOSS",
                    "contentType": content_type,
                    "compressionType": compression_type,
                }
            }
        }

        # 可选的OSS配置
        if oss_bucket:
            body["configuration"]["sink"]["bucket"] = oss_bucket
        if oss_prefix:
            body["configuration"]["sink"]["prefix"] = oss_prefix
        if role_arn:
            body["configuration"]["sink"]["roleArn"] = role_arn

        # 发送请求
        headers = {"Content-Type": "application/json"}
        response = self.client._send("POST", project, None, "/downloadjobs", body, headers)

        # 解析响应
        if response.status == 200:
            return name
        else:
            raise LogException(f"Failed to create download job: {response.data}")

    def get_download_job(
        self,
        job_name: str,
        project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取日志下载任务状态和结果

        Args:
            job_name: 下载任务名称（create_download_job返回的name）
            project: Project名称

        Returns:
            任务信息字典，包含以下关键字段：
            - status: 任务状态 (STARTING、RUNNING、SUCCEEDED、ERROR)
            - name: 任务名称
            - description: 任务描述
            - configuration: 下载配置
            - createTime: 创建时间
            - displayName: 显示名称
            - executionDetails: 执行详情，包含：
                - progress: 下载进度 (0-100)
                - filePath: 下载结果链接（SUCCEEDED时返回）
                - fileSize: 文件大小（字节）
                - logCount: 下载日志条数
                - executeTime: 执行时间（秒）
                - errorMessage: 错误信息（ERROR时返回）
                - checkSum: 文件ETAG校验值

        Raises:
            LogException: API调用失败或任务不存在

        Example:
            >>> job_info = client.get_download_job("my-download-job-001")
            >>> print(f"状态: {job_info['status']}")
            >>> if job_info['status'] == 'SUCCEEDED':
            ...     print(f"文件链接: {job_info['executionDetails']['filePath']}")
            ...     print(f"日志条数: {job_info['executionDetails']['logCount']}")
        """
        project = self._get_project(project)

        # 发送请求
        response = self.client._send("GET", project, None, f"/downloadjobs/{job_name}", {}, {})

        # 解析响应
        if response.status == 200:
            return json.loads(response.data)
        else:
            raise LogException(f"Failed to get download job: {response.data}")

    def list_download_jobs(
        self,
        offset: int = 0,
        size: int = 100,
        project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        列出日志下载任务

        Args:
            offset: 起始位置，用于分页
            size: 返回条数，默认100
            project: Project名称

        Returns:
            任务列表信息，包含以下字段：
            - total: 总任务数
            - count: 当前返回的任务数
            - results: 任务列表，每个任务包含name、status、createTime等
        """
        project = self._get_project(project)

        # 构建查询参数
        params = {"offset": offset, "size": size}

        # 发送请求
        response = self.client._send("GET", project, params, "/downloadjobs", {}, {})

        # 解析响应
        if response.status == 200:
            return json.loads(response.data)
        else:
            raise LogException(f"Failed to list download jobs: {response.data}")

    def wait_for_download_job(
        self,
        job_name: str,
        project: Optional[str] = None,
        timeout: int = 3600,
        poll_interval: int = 5,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        等待日志下载任务完成

        轮询检查任务状态，直到任务完成（SUCCEEDED）或失败（ERROR），或超时。

        Args:
            job_name: 下载任务名称
            project: Project名称
            timeout: 超时时间（秒），默认3600秒（1小时）
            poll_interval: 轮询间隔（秒），默认5秒
            verbose: 是否打印进度信息，默认True

        Returns:
            最终任务信息字典

        Raises:
            TimeoutError: 等待超时
            LogException: 任务执行失败或API调用失败

        Example:
            >>> try:
            ...     job_info = client.wait_for_download_job("my-download-job-001")
            ...     if job_info['status'] == 'SUCCEEDED':
            ...         print(f"下载成功！文件链接: {job_info['executionDetails']['filePath']}")
            ... except TimeoutError:
            ...     print("等待超时")
        """
        start_time = time.time()

        while True:
            job_info = self.get_download_job(job_name, project)
            status = job_info.get("status")

            if status == "SUCCEEDED":
                return job_info
            elif status == "ERROR":
                error_msg = job_info.get("executionDetails", {}).get("errorMessage", "Unknown error")
                raise LogException(f"Download job failed: {error_msg}")
            elif status in ("STARTING", "RUNNING"):
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Waiting for download job {job_name} timed out after {timeout} seconds")

                progress = job_info.get("executionDetails", {}).get("progress", 0)
                if verbose:
                    print(f"下载任务 {job_name} 状态: {status}, 进度: {progress}%, 已等待 {int(elapsed)}秒")
                time.sleep(poll_interval)
            else:
                raise LogException(f"Unknown job status: {status}")

    def _split_time_range(
        self,
        from_time: Union[int, float, str, datetime],
        to_time: Union[int, float, str, datetime],
        chunk_seconds: int = 600
    ) -> List[Tuple[int, int]]:
        """
        将时间范围拆分为多个小段

        Args:
            from_time: 起始时间
            to_time: 结束时间
            chunk_seconds: 每个时间段的长度（秒），默认600秒（10分钟）

        Returns:
            时间段列表，每个元素为(from_ts, to_ts)元组
        """
        from_ts = self._time_to_timestamp(from_time)
        to_ts = self._time_to_timestamp(to_time)

        chunks = []
        current = from_ts
        while current < to_ts:
            chunk_end = min(current + chunk_seconds, to_ts)
            chunks.append((current, chunk_end))
            current = chunk_end

        return chunks

    def batch_download_logs(
        self,
        from_time: Union[int, float, str, datetime],
        to_time: Union[int, float, str, datetime],
        query: str = "*",
        chunk_minutes: int = 10,
        max_workers: int = 3,
        content_type: str = "json",
        compression_type: str = "zstd",
        oss_bucket: Optional[str] = None,
        oss_prefix: str = "sls-download/",
        project: Optional[str] = None,
        logstore: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量下载日志（按时间拆分并行下载）

        将大时间范围拆分为多个小段（默认10分钟），创建多个下载任务并行执行，
        显著提升大日志量下载效率。例如：原本100万条日志（12分钟）拆分为
        12个10分钟段并行下载，总时间可缩短至约2-3分钟。

        Args:
            from_time: 起始时间
            to_time: 结束时间
            query: 查询语句
            chunk_minutes: 每个时间段的长度（分钟），默认10分钟
            max_workers: 最大并行任务数（阿里云限制最多3个并发）
            content_type: 文件格式，可选 "json" 或 "csv"
            compression_type: 压缩格式，可选 "zstd"(推荐)、"lz4"、"gzip"、"none"
            oss_bucket: OSS存储桶名称
            oss_prefix: OSS路径前缀
            project: Project名称
            logstore: Logstore名称
            **kwargs: 其他参数传递给create_download_job

        Returns:
            所有成功任务的信息列表

        Example:
            >>> results = client.batch_download_logs(
            ...     from_time="2024-01-01 00:00:00",
            ...     to_time="2024-01-01 02:00:00",
            ...     query="level: ERROR",
            ...     chunk_minutes=10,
            ...     oss_bucket="my-bucket"
            ... )
            >>> for r in results:
            ...     print(f"文件: {r['executionDetails']['filePath']}")
        """
        import concurrent.futures
        from datetime import datetime as dt

        chunk_seconds = chunk_minutes * 60
        time_chunks = self._split_time_range(from_time, to_time, chunk_seconds)

        if not time_chunks:
            print("时间范围无效，没有需要下载的数据")
            return []

        print(f"时间范围已拆分为 {len(time_chunks)} 个段（每段{chunk_minutes}分钟），并行下载中...")

        # 限制最大并发数为3（阿里云限制）
        max_workers = min(max_workers, 3)

        def download_chunk(chunk_idx: int, from_ts: int, to_ts: int) -> Optional[Dict[str, Any]]:
            """下载单个时间段的日志"""
            job_name = f"batch-{int(time.time())}-{chunk_idx}"
            chunk_prefix = f"{oss_prefix.rstrip('/')}/chunk-{chunk_idx}/"

            try:
                # 创建下载任务
                self.create_download_job(
                    name=job_name,
                    from_time=from_ts,
                    to_time=to_ts,
                    query=query,
                    display_name=f"Batch chunk {chunk_idx}",
                    content_type=content_type,
                    compression_type=compression_type,
                    oss_bucket=oss_bucket,
                    oss_prefix=chunk_prefix,
                    project=project,
                    logstore=logstore,
                    **kwargs
                )

                # 等待任务完成（不打印每个任务的进度）
                job_info = self.wait_for_download_job(
                    job_name=job_name,
                    project=project,
                    poll_interval=3,
                    verbose=False
                )

                # 格式化时间范围用于显示
                from_str = dt.fromtimestamp(from_ts).strftime('%H:%M:%S')
                to_str = dt.fromtimestamp(to_ts).strftime('%H:%M:%S')

                if job_info['status'] == 'SUCCEEDED':
                    details = job_info['executionDetails']
                    print(f"✓ 段 {chunk_idx+1}/{len(time_chunks)} ({from_str}-{to_str}): "
                          f"{details['logCount']}条, {details['fileSize']}字节")
                    return job_info
                else:
                    print(f"✗ 段 {chunk_idx+1}/{len(time_chunks)} ({from_str}-{to_str}): 失败")
                    return None

            except Exception as e:
                from_str = dt.fromtimestamp(from_ts).strftime('%H:%M:%S')
                to_str = dt.fromtimestamp(to_ts).strftime('%H:%M:%S')
                print(f"✗ 段 {chunk_idx+1}/{len(time_chunks)} ({from_str}-{to_str}): 错误 - {e}")
                return None

        # 使用线程池并行执行下载任务
        completed_jobs = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {
                executor.submit(download_chunk, i, from_ts, to_ts): i
                for i, (from_ts, to_ts) in enumerate(time_chunks)
            }

            for future in concurrent.futures.as_completed(future_to_chunk):
                result = future.result()
                if result:
                    completed_jobs.append(result)

        print(f"\n下载完成: {len(completed_jobs)}/{len(time_chunks)} 个任务成功")

        # 汇总统计
        if completed_jobs:
            total_logs = sum(j['executionDetails'].get('logCount', 0) for j in completed_jobs)
            total_size = sum(j['executionDetails'].get('fileSize', 0) for j in completed_jobs)
            print(f"总计: {total_logs}条日志, {total_size}字节")

        return completed_jobs

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
