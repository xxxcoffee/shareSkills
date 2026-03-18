"""操作符注册中心

管理所有Pipeline操作符的注册和发现。
"""

from typing import Dict, List, Optional, Type, Any

from echecker.operators.base import Operator


# 使用base模块的注册表以保持兼容性
from echecker.operators.base import _operator_registry as _module_operators

# 操作符实例存储
_operator_instances: Dict[str, Operator] = {}


class OperatorInfo:
    """操作符信息"""

    def __init__(self, operator_class: Type[Operator]):
        self.name = operator_class.name
        self.version = operator_class.version
        self.description = operator_class.description
        self.operator_type = operator_class.operator_type
        self.config_spec = operator_class.get_config_spec()
        self.operator_class = operator_class

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "operator_type": self.operator_type.name if self.operator_type else None,
            "config_spec": self.config_spec
        }

    def __repr__(self):
        return f"OperatorInfo({self.name}@{self.version}, type={self.operator_type.name if self.operator_type else 'N/A'})"


class OperatorRegistry:
    """操作符注册中心

    负责操作符的注册、查询和管理。支持：
    - 装饰器注册（类级别）
    - 手动注册
    - 按类型查询
    - 单例实例管理

    示例:
        # 类级别装饰器注册（推荐）
        @OperatorRegistry.register
        class MyOperator(Operator):
            name = "my_operator"
            ...

        # 获取操作符
        op_class = OperatorRegistry.get("my_operator")
        op_instance = OperatorRegistry.get_instance("my_operator")

        # 按类型查询
        validators = OperatorRegistry.list_by_type(OperatorType.VALIDATE)
    """

    @classmethod
    def register(cls, operator_class: Type[Operator]) -> Type[Operator]:
        """注册操作符（类级别装饰器）

        用法:
            @OperatorRegistry.register
            class MyOperator(Operator):
                name = "my_operator"
                ...

        Args:
            operator_class: 操作符类

        Returns:
            Type[Operator]: 传入的操作符类

        Raises:
            ValueError: 操作符名称未定义或已存在
        """
        global _module_operators

        if not operator_class.name:
            raise ValueError(f"操作符 {operator_class.__name__} 必须定义name属性")

        if operator_class.name in _module_operators:
            raise ValueError(f"操作符 '{operator_class.name}' 已注册")

        _module_operators[operator_class.name] = operator_class
        return operator_class

    @classmethod
    def get(cls, name: str) -> Optional[Type[Operator]]:
        """获取操作符类

        Args:
            name: 操作符名称

        Returns:
            Optional[Type[Operator]]: 操作符类，不存在则返回None
        """
        return _module_operators.get(name)

    @classmethod
    def get_instance(cls, name: str) -> Optional[Operator]:
        """获取操作符实例（单例模式）

        Args:
            name: 操作符名称

        Returns:
            Optional[Operator]: 操作符实例，不存在则返回None
        """
        global _operator_instances

        if name not in _operator_instances:
            operator_class = _module_operators.get(name)
            if operator_class is None:
                return None
            _operator_instances[name] = operator_class()

        return _operator_instances[name]

    @classmethod
    def has(cls, name: str) -> bool:
        """检查操作符是否存在

        Args:
            name: 操作符名称

        Returns:
            bool: 是否存在
        """
        return name in _module_operators

    @classmethod
    def list_all(cls) -> List[OperatorInfo]:
        """列出所有已注册的操作符

        Returns:
            List[OperatorInfo]: 操作符信息列表
        """
        return [OperatorInfo(op_class) for op_class in _module_operators.values()]

    @classmethod
    def list_by_type(cls, operator_type) -> List[OperatorInfo]:
        """按类型列出操作符

        Args:
            operator_type: 操作符类型（OperatorType枚举）

        Returns:
            List[OperatorInfo]: 操作符信息列表
        """
        return [
            OperatorInfo(op_class) for op_class in _module_operators.values()
            if op_class.operator_type == operator_type
        ]

    @classmethod
    def list_names(cls) -> List[str]:
        """列出所有操作符名称

        Returns:
            List[str]: 操作符名称列表
        """
        return list(_module_operators.keys())

    @classmethod
    def clear(cls) -> None:
        """清除所有注册的操作符和实例（用于测试）"""
        global _operator_instances
        _module_operators.clear()
        _operator_instances.clear()

    @classmethod
    def clear_instances(cls) -> None:
        """清除所有操作符实例（用于测试）"""
        global _operator_instances
        _operator_instances.clear()

    # 实例方法（保留以兼容旧代码）
    def __init__(self):
        """初始化（已弃用，保留以兼容旧代码）"""
        pass


# 全局注册中心实例（向后兼容）
_default_registry: Optional[OperatorRegistry] = None


def get_registry() -> OperatorRegistry:
    """获取全局操作符注册中心

    Returns:
        OperatorRegistry: 全局注册中心实例（单例）
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = OperatorRegistry()
    return _default_registry


# 全局函数（向后兼容）
def register(operator_class: Type[Operator]) -> Type[Operator]:
    """全局注册操作符（装饰器）

    用法:
        from echecker.operators import register, Operator

        @register
        class MyOperator(Operator):
            name = "my_operator"
            ...

    Args:
        operator_class: 操作符类

    Returns:
        Type[Operator]: 传入的操作符类
    """
    return OperatorRegistry.register(operator_class)


def get_operator(name: str) -> Optional[Type[Operator]]:
    """全局获取操作符类

    Args:
        name: 操作符名称

    Returns:
        Optional[Type[Operator]]: 操作符类
    """
    return OperatorRegistry.get(name)


def get_operator_instance(name: str) -> Optional[Operator]:
    """全局获取操作符实例

    Args:
        name: 操作符名称

    Returns:
        Optional[Operator]: 操作符实例
    """
    return OperatorRegistry.get_instance(name)


def list_operators() -> List[OperatorInfo]:
    """全局列出所有操作符

    Returns:
        List[OperatorInfo]: 操作符信息列表
    """
    return OperatorRegistry.list_all()
