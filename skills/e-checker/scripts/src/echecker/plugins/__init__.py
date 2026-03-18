"""eChecker V2 插件系统

提供插件化架构支持，包括：
- ValidationPlugin: 插件基类
- PluginContext: 插件执行上下文
- PluginManager: 插件管理器
- ExternalDataManager: 外部数据管理器
"""

from echecker.plugins.base import ValidationPlugin, PluginResult
from echecker.plugins.context import PluginContext
from echecker.plugins.manager import PluginManager, PluginInfo
from echecker.plugins.external_data import ExternalDataManager, ExternalDataSource

__all__ = [
    "ValidationPlugin",
    "PluginResult",
    "PluginContext",
    "PluginManager",
    "PluginInfo",
    "ExternalDataManager",
    "ExternalDataSource",
]
