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
    _fetch_files: bool

    def __init__(
        self,
        env: EnvConfig,
        additive: bool,
        *,
        file_infos: pd.DataFrame,
        fetch_files: bool,
    ) -> None:
        self._file_infos = file_infos
        self._fetch_files = fetch_files

        super().__init__(env=env, additive=additive, name=StepName.ADD_ANNOTATIONS)

    def _run(self, datasets_dir: Path, dest_dataset: Path) -> None:
        file_pairs: Set[Tuple[Path, Path]] = set()
        dataset_file_map: Dict[str, Set[Tuple[Path, Path]]] = {
            d: set() for d in self._file_infos["dataset"].unique()
        }
        for _, row in self._file_infos.iterrows():  # type: ignore
            src: Path = row["annotation path"]

            dst = AddAnnotations._get_dst_annotation(src, dest_dataset, row["dataset"])

            file_pairs.add((src, dst))
            dataset_file_map[row["dataset"]].add((src, dst))

        for _, row in (
            self._file_infos[["dataset", "set"]].drop_duplicates().iterrows()
        ):  # type: ignore
            src: Path = (
                datasets_dir
                / row["dataset"]
                / "annotations"
                / row["set"]
                / "metannots.yml"
            )

            if not src.exists():
                continue

            dst = AddAnnotations._get_dst_metannots(
                dest_dataset, row["dataset"], row["set"]
            )

            file_pairs.add((src, dst))
            dataset_file_map[row["dataset"]].add((src, dst))

        # skip things that are already added
        file_pairs = {(src, dst) for (src, dst) in file_pairs if not dst.exists()}
        dataset_file_map = {
            dataset: {(src, dst) for (src, dst) in files if not dst.exists()}
            for (dataset, files) in dataset_file_map.items()
        }

        if len(file_pairs) != 0:
            if self._fetch_files:
                fetch_files(self.env, dataset_file_map, datasets_dir)
            copy_files(self.env, file_pairs, dest_dataset)

        git_unannex_and_save(
            self.env, dest_dataset, "annotations/**", "Unannexed annotations and saved"
        )

        return

    @staticmethod
    def _get_dst_annotation(source: Path, output_dir: Path, dataset: str) -> Path:
        parts = source.parts
        idx = parts.index("annotations")
        return output_dir / "annotations" / dataset / Path(*parts[idx + 1 :])

    @staticmethod
    def _get_annotation_path(
        dataset_dir: Path, set_name: str, annotation_name: str
    ) -> Path:
        return dataset_dir / "annotations" / set_name / "converted" / annotation_name

    @staticmethod
    def _get_dst_metannots(output_dir: Path, dataset: str, set_name: str) -> Path:
        return output_dir / "annotations" / dataset / set_name / "metannots.yml"
