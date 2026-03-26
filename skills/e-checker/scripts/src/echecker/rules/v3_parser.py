"""V3规则解析器

支持V3格式的YAML规则文件，采用pipeline语法替代V2的插件配置语法。
"""

import yaml
import re
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
from dataclasses import dataclass, field

from echecker.expression.template import ConfigPreprocessor, is_template
from .folder_expander import FolderExpander

@dataclass
class ExternalDataSourceConfig:
    """外部数据源配置"""
    name: str
    file: Path
    sheet: str
    columns: Dict[str, str]
    key_column: Optional[str] = None

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ExternalDataSourceConfig":
        """从字典解析外部数据源配置"""
        return cls(
            name=name,
            file=Path(data["file"]),
            sheet=data["sheet"],
            columns=data["columns"],
            key_column=data.get("key_column")
        )


@dataclass
class PipelineStep:
    """管道操作步骤

    每个步骤包含一个操作符和其配置
    """
    operator: str  # 操作符名称 (split, lookup, exists等)
    config: Dict[str, Any] = field(default_factory=dict)  # 操作符配置（预处理后）
    raw_config: Dict[str, Any] = field(default_factory=dict)  # 原始配置（包含模板）
    has_templates: bool = False  # 是否包含模板表达式

    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], str], preprocessor: Optional[ConfigPreprocessor] = None) -> "PipelineStep":
        """从字典解析管道步骤

        格式:
        - 字典: {operator_name: config} 例如 {split: "|"}
        - 字符串: "operator_name" 例如 "count"

        Args:
            data: 步骤数据
            preprocessor: 配置预处理器，用于处理 ${...} 模板表达式
        """
        if not data:
            raise ValueError("Pipeline步骤不能为空")

        # 处理字符串格式（如 - count）
        if isinstance(data, str):
            return cls(operator=data, config={})

        # 获取操作符名称（第一个键）
        operator = list(data.keys())[0]
        config = data[operator]

        # 标准化配置格式
        if config is None:
            config = {}
        elif not isinstance(config, dict):
            # 简写格式：值直接作为操作符的配置
            config = {"value": config}

        # 保存原始配置
        raw_config = dict(config)

        # 处理模板表达式
        has_templates = False
        if preprocessor:
            config = preprocessor.process(config)
            # 检查是否包含模板
            has_templates = cls._check_templates(config)

        return cls(
            operator=operator,
            config=config,
            raw_config=raw_config,
            has_templates=has_templates
        )

    @staticmethod
    def _check_templates(value: Any) -> bool:
        """递归检查值是否包含模板表达式"""
        if isinstance(value, dict):
            return any(PipelineStep._check_templates(v) for v in value.values())
        elif isinstance(value, list):
            return any(PipelineStep._check_templates(item) for item in value)
        else:
            from echecker.expression.template import TemplateExpr
            return isinstance(value, TemplateExpr)


@dataclass
class PipelineValidation:
    """Pipeline类型验证配置"""
    steps: List[PipelineStep]
    message: Optional[str] = None

    @classmethod
    def from_config(cls, data: Union[List, Dict, str], preprocessor: Optional[ConfigPreprocessor] = None) -> "PipelineValidation":
        """解析pipeline配置

        支持三种格式:
        1. 数组格式: [{split: "|"}, {lookup: "..."}, {exists: true}]
        2. 对象格式: {pipe: [...], message: "..."}
        3. 字符串格式: "split '|' | lookup '...' | exists"

        Args:
            data: Pipeline配置数据
            preprocessor: 配置预处理器，用于处理 ${...} 模板表达式
        """
        if isinstance(data, list):
            # 数组格式
            steps = [PipelineStep.from_dict(step, preprocessor) for step in data]
            return cls(steps=steps)

        elif isinstance(data, dict):
            # 对象格式
            if 'pipe' in data:
                pipe = data['pipe']
                message = data.get('message')

                if isinstance(pipe, str):
                    # 字符串管道语法
                    steps = cls._parse_pipe_string(pipe, preprocessor)
                else:
                    # 数组格式
                    steps = [PipelineStep.from_dict(step, preprocessor) for step in pipe]

                return cls(steps=steps, message=message)
            elif 'pipeline' in data:
                # {pipeline: [...]} 格式
                pipeline = data['pipeline']
                message = data.get('message')

                if isinstance(pipeline, str):
                    steps = cls._parse_pipe_string(pipeline, preprocessor)
                else:
                    steps = [PipelineStep.from_dict(step, preprocessor) for step in pipeline]

                return cls(steps=steps, message=message)
            else:
                raise ValueError(f"Pipeline配置必须包含 'pipe' 或 'pipeline' 字段: {data}")

        elif isinstance(data, str):
            # 纯字符串格式
            steps = cls._parse_pipe_string(data, preprocessor)
            return cls(steps=steps)

        else:
            raise ValueError(f"不支持的Pipeline配置格式: {type(data)}")

    @staticmethod
    def _parse_pipe_string(pipe_str: str, preprocessor: Optional[ConfigPreprocessor] = None) -> List[PipelineStep]:
        """解析管道字符串

        格式: "split '|' | lookup 'ref[id].col' | exists"

        Args:
            pipe_str: 管道字符串
            preprocessor: 配置预处理器，用于处理 ${...} 模板表达式
        """
        steps = []
        # 简单的管道字符串解析（按 | 分割）
        parts = [p.strip() for p in pipe_str.split('|')]

        for part in parts:
            if not part:
                continue

            # 解析操作符和参数
            # 格式: "operator 'arg'" 或 "operator {key: value}" 或 "operator"
            match = re.match(r"^(\w+)\s*(.*)$", part)
            if not match:
                raise ValueError(f"无法解析管道步骤: {part}")

            operator = match.group(1)
            arg_str = match.group(2).strip()

            # 解析参数
            config = {}
            raw_config = {}
            has_templates = False

            if arg_str:
                # 去除引号
                if (arg_str.startswith('"') and arg_str.endswith('"')) or \
                   (arg_str.startswith("'") and arg_str.endswith("'")):
                    arg_str = arg_str[1:-1]

                # 尝试解析为其他类型
                if arg_str.lower() == 'true':
                    config['value'] = True
                elif arg_str.lower() == 'false':
                    config['value'] = False
                else:
                    try:
                        config['value'] = int(arg_str)
                    except ValueError:
                        try:
                            config['value'] = float(arg_str)
                        except ValueError:
                            config['value'] = arg_str

                raw_config = dict(config)

                # 处理模板表达式
                if preprocessor:
                    config = preprocessor.process(config)
                    has_templates = PipelineStep._check_templates(config)

            steps.append(PipelineStep(
                operator=operator,
                config=config,
                raw_config=raw_config,
                has_templates=has_templates
            ))

        return steps


@dataclass
class V3ValidationConfig:
    """V3校验配置

    支持两种类型:
    1. pipeline: 使用管道语法
    2. type: 兼容V2插件类型
    """
    validation_type: str  # "pipeline" 或插件类型名称
    config: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    pipeline: Optional[PipelineValidation] = None
    raw_config: Dict[str, Any] = field(default_factory=dict)  # 原始配置
    has_templates: bool = False  # 是否包含模板表达式

    @classmethod
    def from_dict(cls, data: Dict[str, Any], preprocessor: Optional[ConfigPreprocessor] = None) -> "V3ValidationConfig":
        """从字典解析V3校验配置

        Args:
            data: 校验配置数据
            preprocessor: 配置预处理器，用于处理 ${...} 模板表达式
        """
        # 复制数据以避免修改原始数据
        data_copy = dict(data)

        if 'pipeline' in data_copy or 'pipe' in data_copy:
            # Pipeline类型
            pipeline = PipelineValidation.from_config(data_copy, preprocessor)

            # 提取其他配置并处理模板
            extra_config = {k: v for k, v in data_copy.items() if k not in ('pipeline', 'pipe', 'message')}
            raw_config = dict(extra_config)

            if preprocessor:
                extra_config = preprocessor.process(extra_config)
                has_templates = PipelineStep._check_templates(extra_config)
            else:
                has_templates = False

            return cls(
                validation_type="pipeline",
                pipeline=pipeline,
                message=pipeline.message or data_copy.get('message'),
                config=extra_config,
                raw_config=raw_config,
                has_templates=has_templates
            )
        else:
            # 默认假设第一个键是操作符，使用pipeline格式
            pipeline = PipelineValidation.from_config([data_copy], preprocessor)
            return cls(
                validation_type="pipeline",
                pipeline=pipeline,
                message=data_copy.get('message'),
                has_templates=any(step.has_templates for step in pipeline.steps)
            )


@dataclass
class V3Rule:
    """V3校验规则"""
    target: str  # 目标单元格/范围
    validations: List[V3ValidationConfig]
    id: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.id is None:
            import hashlib
            self.id = hashlib.md5(self.target.encode()).hexdigest()[:8]


@dataclass
class V3RuleSet:
    """V3规则集"""
    version: str = "3.0"
    refs: Dict[str, ExternalDataSourceConfig] = field(default_factory=dict)
    rules: List[V3Rule] = field(default_factory=list)


class V3RuleParser:
    """V3规则解析器

    支持V3格式的YAML规则文件，采用pipeline语法。
    同时向后兼容V2规则格式。

    模板表达式支持:
    - 支持 ${...} 语法嵌入动态表达式
    - 在解析阶段自动编译模板表达式
    - 在执行阶段通过 EvalContext 求值
    """

    def __init__(self, enable_templates: bool = True):
        """初始化解析器

        Args:
            enable_templates: 是否启用模板表达式预处理，默认为 True
        """
        self._ruleset: Optional[V3RuleSet] = None
        self._preprocessor: Optional[ConfigPreprocessor] = ConfigPreprocessor() if enable_templates else None

    def parse_file(self, path: Union[str, Path]) -> V3RuleSet:
        """解析规则文件"""
        path = Path(path) if isinstance(path, str) else path

        if not path.exists():
            raise FileNotFoundError(f"规则文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self.parse_data(data, base_path=path.parent)

    def parse_data(self, data: Dict[str, Any], base_path: Path = Path("."), enable_templates: Optional[bool] = None) -> V3RuleSet:
        """解析规则数据"""
        version = data.get('version', '3.0')

        # 解析refs（与V2相同）
        refs = {}
        for ref_name, ref_data in data.get('refs', {}).items():
            ref_data_copy = dict(ref_data)
            if 'file' in ref_data_copy:
                ref_path = Path(ref_data_copy['file'])
                if not ref_path.is_absolute():
                    ref_path = base_path / ref_path
                ref_data_copy['file'] = ref_path

            refs[ref_name] = ExternalDataSourceConfig.from_dict(ref_name, ref_data_copy)

        # 解析rules
        rules = []
        for rule_data in data.get('rules', []):
            rule = self._parse_rule(rule_data)
            rules.append(rule)

        # 展开通配符
        expander = FolderExpander(str(base_path))
        expanded_rules = expander.expand(rules)

        self._ruleset = V3RuleSet(
            version=version,
            refs=refs,
            rules=expanded_rules
        )

        # 验证所有规则中的refs引用
        self._validate_refs(self._ruleset)

        return self._ruleset

    def _parse_rule(self, data: Dict[str, Any]) -> V3Rule:
        """解析单个规则"""
        validations = []

        for val_data in data.get('validations', []):
            val_config = V3ValidationConfig.from_dict(val_data, self._preprocessor)
            validations.append(val_config)

        # 处理 target 字段的模板表达式
        target = data['target']
        if self._preprocessor and isinstance(target, str) and is_template(target):
            target = self._preprocessor.process(target)

        return V3Rule(
            target=target,
            validations=validations,
            id=data.get('id'),
            description=data.get('description'),
            enabled=data.get('enabled', True)
        )

    def _validate_refs(self, ruleset: V3RuleSet) -> None:
        """验证规则中引用的数据源和列是否在refs中声明"""
        errors = []

        for rule in ruleset.rules:
            for validation in rule.validations:
                # 检查pipeline中的lookup操作符
                if validation.pipeline:
                    for step in validation.pipeline.steps:
                        if step.operator in ('lookup', 'exists_in', 'where', 'all_exist_in'):
                            # 解析 lookup 语法: "ref_source[match_column].return_column"
                            lookup_str = step.config.get('value', '')
                            if isinstance(lookup_str, str) and '[' in lookup_str:
                                ref_source = lookup_str.split('[')[0]
                                if ref_source and ref_source not in ruleset.refs:
                                    errors.append(
                                        f"规则 '{rule.id}': pipeline中引用了未声明的数据源 '{ref_source}'"
                                    )

                # 检查V2兼容配置
                config = validation.config
                ref_source = config.get('ref_source')
                if ref_source and ref_source not in ruleset.refs:
                    errors.append(
                        f"规则 '{rule.id}': 引用了未声明的数据源 '{ref_source}'"
                    )

        if errors:
            raise ValueError("规则引用验证失败:\n" + "\n".join(f"  - {e}" for e in errors))


def is_v3_rules(data: Dict[str, Any]) -> bool:
    """检查是否为V3规则格式

    V3规则的特征：
    - version为"3.0"
    - validations包含pipeline字段
    - 使用数组形式的管道步骤
    """
    version = data.get('version', '')
    if isinstance(version, str) and version.startswith('3.'):
        return True

    # 检查是否有pipeline语法
    for rule in data.get('rules', []):
        for val in rule.get('validations', []):
            if isinstance(val, dict):
                if 'pipeline' in val or 'pipe' in val:
                    return True
                # 检查是否为数组格式的pipeline
                if any(isinstance(v, list) for v in val.values()):
                    return True
            elif isinstance(val, list):
                # 数组格式也是V3特征
                return True

    return False
