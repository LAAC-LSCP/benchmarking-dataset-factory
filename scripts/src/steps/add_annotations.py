from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

from scripts.src.steps.file_management import (
    copy_files,
    fetch_files,
    git_unannex_and_save,
)
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class AddAnnotations(Step):
    _file_infos: pd.DataFrame

    def __init__(self, env: EnvConfig, *, file_infos: pd.DataFrame) -> None:
        self._file_infos = file_infos

        super().__init__(env=env, name=StepName.ADD_ANNOTATIONS)

    def _run(self, _: Path, dest_dataset: Path, overwrite: bool) -> None:
        file_pairs: Set[Tuple[Path, Path]] = set()
        dataset_file_map: Dict[str, Set[Tuple[Path, Path]]] = {
            d: set() for d in self._file_infos["dataset"].unique()
        }
        for _, row in self._file_infos.iterrows():  # type: ignore
            src: Path = row["annotation path"]

            dst = AddAnnotations._get_dst_annotation(src, dest_dataset, row["dataset"])

            file_pairs.add((src, dst))
            dataset_file_map[row["dataset"]].add((src, dst))

        if not overwrite:
            # skip things that are already added
            file_pairs = {(src, dst) for (src, dst) in file_pairs if not dst.exists()}
            dataset_file_map = {
                dataset: {(src, dst) for (src, dst) in files if not dst.exists()}
                for (dataset, files) in dataset_file_map.items()
            }

        if len(file_pairs) != 0:
            fetch_files(self._env, dataset_file_map)
            copy_files(self._env, file_pairs, dest_dataset)

        git_unannex_and_save(
            self._env, dest_dataset, "annotations/**", "Unannexed annotations and saved"
        )

        return

    @staticmethod
    def _get_dst_annotation(source: Path, output_dir: Path, dataset: str) -> Path:
        parts = source.parts
        idx = parts.index("annotations")
        return output_dir / "annotations" / dataset / Path(*parts[idx + 1 :])
