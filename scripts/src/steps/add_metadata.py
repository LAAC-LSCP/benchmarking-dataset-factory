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
        additive: bool,
        *,
        children: pd.DataFrame,
        recordings: pd.DataFrame,
        annotations: pd.DataFrame,
    ) -> None:
        self._children = children.copy()
        self._recordings = recordings.copy()
        self._annotations = annotations.copy()

        super().__init__(env=env, additive=additive, name=StepName.ADD_METADATA)

    def _run(self, _: Path, dest_dataset: Path) -> None:
        if self.additive:
            self._add_metadata(dest_dataset)

            return
        self._create_metadata(dest_dataset)

        return

    def _create_metadata(self, dest_dataset: Path) -> None:
        metadata = dest_dataset / "metadata"
        metadata.mkdir(parents=True, exist_ok=True)

        self._children["experiment"] = "benchmarking"
        self._recordings["experiment"] = "benchmarking"

        self._save(dest_dataset, self._children, self._recordings, self._annotations)

        return

    def _add_metadata(self, dest_dataset: Path) -> None:
        logger.info(f"Adding new metadata to {dest_dataset!s}")
        metadata = dest_dataset / "metadata"

        existing_children = pd.read_csv(metadata / "children.csv")
        existing_recordings = pd.read_csv(metadata / "recordings.csv")
        existing_annotations = pd.read_csv(metadata / "annotations.csv")

        children = pd.concat([existing_children, self._children]).drop_duplicates()
        recordings = pd.concat(
            [existing_recordings, self._recordings]
        ).drop_duplicates()
        annotations = pd.concat(
            [existing_annotations, self._annotations]
        ).drop_duplicates()

        children["experiment"] = "benchmarking"
        recordings["experiment"] = "benchmarking"

        self._save(dest_dataset, children, recordings, annotations)

        return

    def _save(
        self,
        dest_dataset: Path,
        children: pd.DataFrame,
        recordings: pd.DataFrame,
        annotations: pd.DataFrame,
    ) -> None:
        metadata = dest_dataset / "metadata"
        logger.info("Saving metadata...")
        AddMetadata._save_to_csv(metadata / "children.csv", children)
        AddMetadata._save_to_csv(metadata / "recordings.csv", recordings)
        AddMetadata._save_to_csv(metadata / "annotations.csv", annotations)
        datalad_save(self._env, dest_dataset, "Added metadata")
        logger.info("Done saving metadata!")

    @staticmethod
    def _save_to_csv(path: Path, df: pd.DataFrame) -> None:
        logger.info(f"Writing file '{path!s}'")
        df.to_csv(path, index=False)
