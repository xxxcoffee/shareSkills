"""插件管理器

负责插件的自动发现、注册和管理。
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from echecker.plugins.base import ValidationPlugin, PluginResult
from echecker.plugins.context import PluginContext


class PluginInfo:
    """插件信息"""

    def __init__(self, plugin_class: Type[ValidationPlugin]):
        self.name = plugin_class.name
        self.version = plugin_class.version
        self.description = plugin_class.description
        self.category = plugin_class.category
        self.config_spec = plugin_class.get_config_spec()
        self.plugin_class = plugin_class

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "config_spec": self.config_spec
        }


class PluginManager:
    """插件管理器

    负责插件的发现、注册和管理。支持：
    - 自动发现内置插件
    - 手动注册插件
    - 插件实例管理（单例模式）

    示例:
        manager = PluginManager()
        manager.discover_plugins()  # 自动发现

        # 获取插件实例
        plugin = manager.get_plugin("format")

        # 执行校验
        result = plugin.validate(value, context, config)
    """

    def __init__(self):
        self._plugins: Dict[str, Type[ValidationPlugin]] = {}
        self._instances: Dict[str, ValidationPlugin] = {}

    def register(self, plugin_class: Type[ValidationPlugin]) -> None:
        """注册插件

        Args:
            plugin_class: 插件类

        Raises:
            ValueError: 插件名称已存在
        """
        if not plugin_class.name:
            raise ValueError(f"插件 {plugin_class.__name__} 必须定义name属性")

        if plugin_class.name in self._plugins:
            raise ValueError(f"插件 '{plugin_class.name}' 已注册")

        self._plugins[plugin_class.name] = plugin_class

    def unregister(self, name: str) -> bool:
        """注销插件

        Args:
            name: 插件名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._plugins:
            del self._plugins[name]
            self._instances.pop(name, None)
            return True
        return False

    def get_plugin(self, name: str) -> Optional[ValidationPlugin]:
        """获取插件实例（单例）

        Args:
            name: 插件名称

        Returns:
            Optional[ValidationPlugin]: 插件实例，不存在则返回None
        """
        # 检查是否已有实例
        if name in self._instances:
            return self._instances[name]

        # 创建新实例
        plugin_class = self._plugins.get(name)
        if plugin_class is None:
            return None

        instance = plugin_class()
        self._instances[name] = instance
        return instance

    def get_plugin_class(self, name: str) -> Optional[Type[ValidationPlugin]]:
        """获取插件类

        Args:
            name: 插件名称

        Returns:
            Optional[Type[ValidationPlugin]]: 插件类，不存在则返回None
        """
        return self._plugins.get(name)

    def has_plugin(self, name: str) -> bool:
        """检查插件是否存在

        Args:
            name: 插件名称

        Returns:
            bool: 是否存在
        """
        return name in self._plugins

    def list_plugins(self) -> List[PluginInfo]:
        """列出所有可用插件

        Returns:
            List[PluginInfo]: 插件信息列表
        """
        return [PluginInfo(cls) for cls in self._plugins.values()]

    def list_plugins_by_category(self, category: str) -> List[PluginInfo]:
        """按分类列出插件

        Args:
            category: 分类名称

        Returns:
            List[PluginInfo]: 插件信息列表
        """
        return [
            PluginInfo(cls) for cls in self._plugins.values()
            if cls.category == category
        ]

    def discover_plugins(self, paths: Optional[List[Path]] = None) -> int:
        """自动发现插件

        搜索路径（按优先级）：
        1. 用户指定的paths
        2. echecker/plugins/ (内置)

        Args:
            paths: 额外的插件搜索路径

        Returns:
            int: 发现的插件数量
        """
        count = 0

        # 1. 搜索内置插件
        count += self._discover_builtin_plugins()

        # 2. 搜索用户指定路径
        if paths:
            for path in paths:
                count += self._discover_plugins_in_path(path)

        return count

    def _discover_builtin_plugins(self) -> int:
        """发现内置插件

        Returns:
            int: 发现的插件数量
        """
        count = 0

        # 导入echecker.plugins包
        try:
            import echecker.plugins as plugins_pkg
            pkg_path = Path(plugins_pkg.__file__).parent

            # 遍历子目录
            for item in pkg_path.iterdir():
                if item.is_dir() and not item.name.startswith('_'):
                    plugin_module = item / "plugin.py"
                    if plugin_module.exists():
                        if self._load_plugin_module(f"echecker.plugins.{item.name}.plugin"):
                            count += 1

        except Exception as e:
            # 记录错误但不中断
            print(f"发现内置插件时出错: {e}")

        return count

    def _discover_plugins_in_path(self, path: Path) -> int:
        """在指定路径发现插件

        Args:
            path: 搜索路径

        Returns:
            int: 发现的插件数量
        """
        count = 0

        if not path.exists():
            return 0

        # 遍历目录中的Python文件
        for py_file in path.glob("*_plugin.py"):
            try:
                # 动态导入
                spec = importlib.util.spec_from_file_location(
                    py_file.stem, py_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # 查找插件类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, ValidationPlugin) and
                            attr is not ValidationPlugin and
                            attr.name):
                            self.register(attr)
                            count += 1

            except Exception as e:
                print(f"加载插件 {py_file} 时出错: {e}")

        return count

    def _load_plugin_module(self, module_name: str) -> bool:
        """加载插件模块

        Args:
            module_name: 模块名称

        Returns:
            bool: 是否成功加载
        """
        try:
            module = importlib.import_module(module_name)

            # 查找ValidationPlugin的子类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, ValidationPlugin) and
                    attr is not ValidationPlugin and
                    attr.name):
                    self.register(attr)
                    return True

        except Exception as e:
            print(f"加载模块 {module_name} 时出错: {e}")

        return False

    def execute(
        self,
        plugin_name: str,
        value: Any,
        context: PluginContext,
        config: Dict[str, Any]
    ) -> PluginResult:
        """执行插件校验

        快捷方法，获取插件并执行校验。

        Args:
            plugin_name: 插件名称
            value: 要校验的值
            context: 插件上下文
            config: 插件配置

        Returns:
            PluginResult: 校验结果

        Raises:
            KeyError: 插件不存在
        """
        plugin = self.get_plugin(plugin_name)
        if plugin is None:
            raise KeyError(f"插件 '{plugin_name}' 不存在")

        return plugin.validate(value, context, config)

    def clear_instances(self) -> None:
        """清除所有插件实例（用于测试）"""
        self._instances.clear()
