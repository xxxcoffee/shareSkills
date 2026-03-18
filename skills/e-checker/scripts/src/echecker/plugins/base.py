"""插件基类定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from echecker.types import ErrorType, Severity, ValidationError
from echecker.plugins.context import PluginContext


@dataclass
class PluginResult:
    """插件校验结果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    message: Optional[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ValidationPlugin(ABC):
    """校验器插件基类

    所有校验器插件必须继承此类，并提供以下类属性：
    - name: 插件标识名（唯一）
    - version: 版本号
    - description: 描述
    - category: 分类
    - config_spec: JSON Schema格式的配置规格

    示例:
        class MyPlugin(ValidationPlugin):
            name = "my_validator"
            version = "1.0.0"
            description = "我的校验器"
            category = "custom"
            config_spec = {
                "type": "object",
                "properties": {
                    "min": {"type": "number"},
                    "max": {"type": "number"}
                }
            }

            def validate(self, value: Any, context: PluginContext, config: Dict) -> PluginResult:
                # 实现校验逻辑
                return PluginResult(is_valid=True)
    """

    # 类属性：元数据
    name: str = ""  # 插件标识名（必须唯一）
    version: str = "1.0.0"  # 版本
    description: str = ""  # 描述
    category: str = "general"  # 分类

    # 类属性：配置规格（用于YAML校验和IDE提示）
    config_spec: Dict[str, Any] = {}  # JSON Schema格式

    def __init__(self):
        """初始化插件实例"""
        pass

    @abstractmethod
    def validate(self, value: Any, context: PluginContext, config: Dict) -> PluginResult:
        """执行校验

        Args:
            value: 要校验的单元格值
            context: 插件执行上下文，提供行数据、外部数据等访问能力
            config: 该校验器的配置（来自YAML规则文件）

        Returns:
            PluginResult: 校验结果
        """
        pass

    @classmethod
    def get_config_spec(cls) -> Dict[str, Any]:
        """获取配置规格，用于YAML校验和IDE自动完成

        Returns:
            Dict: JSON Schema格式的配置规格
        """
        return cls.config_spec

    def create_error(
        self,
        context: PluginContext,
        error_type: ErrorType,
        message: str,
        expected: Any = None,
        actual: Any = None,
        severity: Severity = Severity.ERROR
    ) -> ValidationError:
        """创建校验错误

        Args:
            context: 插件上下文
            error_type: 错误类型
            message: 错误消息
            expected: 期望值
            actual: 实际值
            severity: 严重级别

        Returns:
            ValidationError: 校验错误对象
        """
        return ValidationError(
            rule_id=self.name,
            cell_ref=f"{context.current_sheet}.{context.current_cell}",
            error_type=error_type,
            message=message,
            severity=severity,
            expected=expected,
            actual=actual,
            sheet_name=context.current_sheet
        )

    def parse_list_value(self, value: Any, split_by: str = "|") -> List[str]:
        """解析列表值（支持分隔符分隔的字符串）

        Args:
            value: 原始值
            split_by: 分隔符，默认为"|"

        Returns:
            List[str]: 解析后的字符串列表
        """
        if value is None:
            return []
        if isinstance(value, (int, float)):
            return [str(int(value))]
        s = str(value).strip()
        if not s:
            return []
        return [x.strip() for x in s.split(split_by) if x.strip()]


# 插件注册表
_plugin_registry: Dict[str, Type[ValidationPlugin]] = {}


def register_plugin(plugin_class: Type[ValidationPlugin]) -> Type[ValidationPlugin]:
    """注册插件（类装饰器）

    用法:
        @register_plugin
        class MyPlugin(ValidationPlugin):
            name = "my_plugin"
            ...

    Args:
        plugin_class: 插件类

    Returns:
        Type[ValidationPlugin]: 传入的插件类（装饰器语法需要）
    """
    if not plugin_class.name:
        raise ValueError(f"插件 {plugin_class.__name__} 必须定义name属性")

    _plugin_registry[plugin_class.name] = plugin_class
    return plugin_class


def get_plugin_class(name: str) -> Optional[Type[ValidationPlugin]]:
    """获取插件类

    Args:
        name: 插件名称

    Returns:
        Optional[Type[ValidationPlugin]]: 插件类，不存在则返回None
    """
    return _plugin_registry.get(name)


def list_registered_plugins() -> List[str]:
    """列出所有已注册的插件名称

    Returns:
        List[str]: 插件名称列表
    """
    return list(_plugin_registry.keys())
