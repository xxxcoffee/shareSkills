"""配置管理器"""

import yaml
from pathlib import Path
from typing import List, Optional, Union

from echecker.config.schema import CentralConfig, ProjectConfig, RuleFile
from echecker.types import RuleDict


class ConfigManager:
    """配置管理器 - 负责加载和管理中央配置及规则文件"""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self._config: Optional[CentralConfig] = None

    def load_central_config(self, path: Union[str, Path]) -> CentralConfig:
        """加载中央配置文件 (echecker.yaml)"""
        config_path = Path(path) if isinstance(path, str) else path
        if not config_path.is_absolute():
            config_path = self.base_path / config_path

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        projects = []
        for proj_data in data.get('projects', []):
            project = ProjectConfig(
                name=proj_data['name'],
                excel=proj_data['excel'],
                rules=proj_data.get('rules', {})
            )
            projects.append(project)

        self._config = CentralConfig(projects=projects)
        return self._config

    def resolve_rules(self, excel_path: Union[str, Path]) -> List[RuleFile]:
        """解析与指定Excel相关的所有规则文件"""
        excel_path = Path(excel_path) if isinstance(excel_path, str) else excel_path
        rules = []

        if self._config:
            for project in self._config.projects:
                if project.excel.resolve() == excel_path.resolve():
                    if global_rule := project.get_global_rule():
                        rules.append(RuleFile(path=global_rule, is_global=True))
                    if local_rule := project.get_local_rule():
                        rules.append(RuleFile(path=local_rule, is_global=False))
                    break

        return rules

    def merge_rules(self, global_rules: List[RuleDict], local_rules: List[RuleDict]) -> List[RuleDict]:
        """合并全局规则和本地规则"""
        merged = []

        for rule in global_rules:
            rule_copy = dict(rule)
            rule_copy['_source'] = 'global'
            merged.append(rule_copy)

        for rule in local_rules:
            rule_copy = dict(rule)
            rule_copy['_source'] = 'local'
            if not any(r.get('id') == rule.get('id') for r in merged):
                merged.append(rule_copy)

        return merged

    def get_config(self) -> Optional[CentralConfig]:
        """获取已加载的配置"""
        return self._config
