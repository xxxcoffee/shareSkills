"""报告基类"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from echecker.types import ValidationReport


class BaseReporter(ABC):
    """报告生成器基类"""

    @abstractmethod
    def generate(self, report: ValidationReport, output_path: Union[str, Path] = None) -> str:
        """生成报告

        Args:
            report: 校验报告
            output_path: 输出路径（可选）

        Returns:
            str: 报告内容或路径
        """
        pass
