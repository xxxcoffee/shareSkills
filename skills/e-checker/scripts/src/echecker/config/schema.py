"""配置数据类定义"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RuleFile:
    """规则文件引用"""
    path: Path
    is_global: bool = False

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)


@dataclass
class ProjectConfig:
    """项目配置"""
    name: str
    excel: Path
    rules: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.excel, str):
            self.excel = Path(self.excel)

    def get_global_rule(self) -> Optional[Path]:
        if "global" in self.rules:
            return Path(self.rules["global"])
        return None

    def get_local_rule(self) -> Optional[Path]:
        if "local" in self.rules:
            return Path(self.rules["local"])
        return None


@dataclass
class CentralConfig:
    """中央配置"""
    projects: List[ProjectConfig] = field(default_factory=list)

    def get_project(self, name: str) -> Optional[ProjectConfig]:
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def list_projects(self) -> List[str]:
        return [p.name for p in self.projects]
