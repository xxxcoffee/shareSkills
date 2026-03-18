"""操作符管理器

负责操作符的自动发现、注册和管理。
类似于现有的PluginManager，但用于V3操作符系统。
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from echecker.operators.base import Operator, Pipeline, OperatorContext, OperatorResult


class OperatorInfo:
    """操作符信息"""

    def __init__(self, operator_class: Type[Operator]):
        self.name = operator_class.name
        self.version = operator_class.version
        self.description = operator_class.description
        self.category = operator_class.category
        self.config_spec = operator_class.get_config_spec()
        self.operator_class = operator_class

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "category": self.category,
            "config_spec": self.config_spec
        }


class OperatorManager:
    """操作符管理器

    负责操作符的发现、注册和管理。支持：
    - 自动发现内置操作符
    - 手动注册操作符
    - 操作符实例管理（单例模式）
    - 管道创建

    示例:
        manager = OperatorManager()
        manager.load_builtin_operators()  # 加载内置操作符

        # 获取操作符类
        operator_class = manager.get_operator("split")

        # 创建管道
        pipeline = manager.create_pipeline([
            {"operator": "split", "config": {"by": "|"}},
            {"operator": "lookup", "config": {"ref_source": "elements", "column": "id"}}
        ])
    """

    def __init__(self):
        self._operators: Dict[str, Type[Operator]] = {}
        self._instances: Dict[str, Operator] = {}

    def register(self, operator_class: Type[Operator]) -> None:
        """注册操作符

        Args:
            operator_class: 操作符类

        Raises:
            ValueError: 操作符名称已存在
        """
        if not operator_class.name:
            raise ValueError(f"操作符 {operator_class.__name__} 必须定义name属性")

        if operator_class.name in self._operators:
            raise ValueError(f"操作符 '{operator_class.name}' 已注册")

        self._operators[operator_class.name] = operator_class

    def unregister(self, name: str) -> bool:
        """注销操作符

        Args:
            name: 操作符名称

        Returns:
            bool: 是否成功注销
        """
        if name in self._operators:
            del self._operators[name]
            self._instances.pop(name, None)
            return True
        return False

    def get_operator(self, name: str) -> Optional[Type[Operator]]:
        """获取操作符类

        Args:
            name: 操作符名称

        Returns:
            Optional[Type[Operator]]: 操作符类，不存在则返回None
        """
        return self._operators.get(name)

    def get_operator_instance(self, name: str) -> Optional[Operator]:
        """获取操作符实例（单例）

        Args:
            name: 操作符名称

        Returns:
            Optional[Operator]: 操作符实例，不存在则返回None
        """
        # 检查是否已有实例
        if name in self._instances:
            return self._instances[name]

        # 创建新实例
        operator_class = self._operators.get(name)
        if operator_class is None:
            return None

        instance = operator_class()
        self._instances[name] = instance
        return instance

    def has_operator(self, name: str) -> bool:
        """检查操作符是否存在

        Args:
            name: 操作符名称

        Returns:
            bool: 是否存在
        """
        return name in self._operators

    def list_operators(self) -> List[OperatorInfo]:
        """列出所有可用操作符

        Returns:
            List[OperatorInfo]: 操作符信息列表
        """
        return [OperatorInfo(cls) for cls in self._operators.values()]

    def list_operators_by_category(self, category: str) -> List[OperatorInfo]:
        """按分类列出操作符

        Args:
            category: 分类名称

        Returns:
            List[OperatorInfo]: 操作符信息列表
        """
        return [
            OperatorInfo(cls) for cls in self._operators.values()
            if cls.category == category
        ]

    def load_builtin_operators(self) -> int:
        """加载所有内置操作符

        通过导入builtin包触发所有操作符的注册。

        Returns:
            int: 加载的操作符数量
        """
        # 导入builtin包，触发所有操作符注册
        try:
            from echecker.operators import builtin
        except ImportError:
            pass

        return len(self._operators)

    def create_pipeline(self, config_list: List[Dict[str, Any]]) -> Pipeline:
        """从配置创建Pipeline实例

        Args:
            config_list: 操作符配置列表
                每个配置应包含:
                - operator: 操作符名称
                - config: 操作符配置字典
                - 其他可选参数如name、condition等

        Returns:
            Pipeline: 创建的管道实例

        Raises:
            KeyError: 如果指定的操作符不存在
            ValueError: 如果配置格式不正确

        示例:
            pipeline = manager.create_pipeline([
                {"operator": "split", "config": {"by": "|"}},
                {"operator": "lookup", "config": {"ref_source": "elements", "column": "id"}},
                {"operator": "exists", "config": {}}
            ])
        """
        steps = []

        for idx, config in enumerate(config_list):
            op_name = config.get("operator")
            if not op_name:
                raise ValueError(f"第{idx+1}步缺少operator字段")

            operator_class = self.get_operator(op_name)
            if operator_class is None:
                raise KeyError(f"操作符 '{op_name}' 不存在")

            step = {
                "operator": op_name,
                "config": config.get("config", {}),
                "name": config.get("name"),
                "condition": config.get("condition"),
                "on_error": config.get("on_error", "fail")
            }
            steps.append(step)

        return Pipeline(steps, self)

    def clear_instances(self) -> None:
        """清除所有操作符实例（用于测试）"""
        self._instances.clear()
