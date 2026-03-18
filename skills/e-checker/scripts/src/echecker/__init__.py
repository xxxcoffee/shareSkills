"""Excel配置检查器 - 基于YAML规则的多维度校验工具"""

__version__ = "3.0.0"

from echecker.core.engine_v3 import V3ValidationEngine, validate_excel

__all__ = ["V3ValidationEngine", "validate_excel"]
