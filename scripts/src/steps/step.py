from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Optional

from scripts.src.utils.exceptions import StepFailedException
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EnvConfig:
    conda_activation_str: str = ""

    def build_command(self, *commands: str) -> str:
        """Join shell commands with &&, omitting the activation prefix if empty."""
        all_cmds = [self.conda_activation_str, *commands]
        return " && ".join(c for c in all_cmds if c)


class StepName(StrEnum):
    ADD_BOILERPLATE = "add_boilerplate"
    ADD_METADATA = "add_metadata"
    ADD_ANNOTATIONS = "add_annotations"
    ADD_RECORDINGS = "add_recordings"
    SPLIT_RECORDINGS = "split_recordings"


class Step(ABC):
    """
    ABC for running steps in a dataset creation pipeline
    """

    _name: StepName
    _env: EnvConfig
    _additive: bool

    def __init__(
        self, name: StepName, additive: bool = False, env: Optional[EnvConfig] = None
    ) -> None:
        self._name = name
        self._additive = additive
        self._env = env or EnvConfig(conda_activation_str="")

    def run(self, datasets_dir: Path, dest_dataset: Path) -> None:
        try:
            logger.info(f"Running step '{self._name}'...")
            self._run(datasets_dir, dest_dataset)
            logger.info(f"Finished running step '{self._name}'...")
        except Exception as e:
            raise StepFailedException(self._name, e) from e

    @abstractmethod
    def _run(self, datasets_dir: Path, dest_dataset: Path) -> None:
        return NotImplemented

    @property
    def name(self) -> StepName:
        return self._name

    @property
    def env(self) -> EnvConfig:
        return self._env

    @property
    def additive(self) -> bool:
        return self._additive
