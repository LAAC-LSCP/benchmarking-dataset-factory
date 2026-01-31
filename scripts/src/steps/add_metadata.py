from pathlib import Path

import pandas as pd

from scripts.src.steps.file_management import datalad_save
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class AddMetadata(Step):
    _children: pd.DataFrame
    _recordings: pd.DataFrame
    _annotations: pd.DataFrame

    def __init__(
        self,
        env: EnvConfig,
        *,
        children: pd.DataFrame,
        recordings: pd.DataFrame,
        annotations: pd.DataFrame,
    ) -> None:
        self._children = children.copy()
        self._recordings = recordings.copy()
        self._annotations = annotations.copy()

        super().__init__(env=env, name=StepName.ADD_METADATA)

    def _run(self, _: Path, dest_dataset: Path, overwrite: bool) -> None:
        metadata = dest_dataset / "metadata"
        metadata.mkdir(parents=True, exist_ok=True)

        self._children["experiment"] = "benchmarking"
        AddMetadata._save_to_csv(metadata / "children.csv", self._children)
        self._recordings["experiment"] = "benchmarking"
        AddMetadata._save_to_csv(metadata / "recordings.csv", self._recordings)
        AddMetadata._save_to_csv(metadata / "annotations.csv", self._annotations)

        datalad_save(self._env, dest_dataset, "Added metadata")

    @staticmethod
    def _save_to_csv(path: Path, df: pd.DataFrame) -> None:
        logger.info(f"Writing file '{path!s}'")
        df.to_csv(path, index=False)
