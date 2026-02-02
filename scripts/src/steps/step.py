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
    conda_activation_str: str


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

    def __init__(self, name: StepName, env: Optional[EnvConfig] = None) -> None:
        self._name = name
        self._env = env or EnvConfig(conda_activation_str="")

    def run(self, datasets_dir: Path, dest_dataset: Path, overwrite: bool) -> None:
        try:
            logger.info(f"Running step '{self._name}'...")
            self._run(datasets_dir, dest_dataset, overwrite)
            logger.info(f"Finished running step '{self._name}'...")
        except Exception as e:
            raise StepFailedException(self._name, repr(e)) from e

    @abstractmethod
    def _run(self, datasets_dir: Path, dest_dataset: Path, overwrite: bool) -> None:
        return NotImplemented

    @property
    def name(self) -> StepName:
        return self._name
