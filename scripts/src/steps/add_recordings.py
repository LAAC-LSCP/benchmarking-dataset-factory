from pathlib import Path
from typing import Dict, Set, Tuple

import pandas as pd

from scripts.src.steps.file_management import copy_files, fetch_files
from scripts.src.steps.step import EnvConfig, Step, StepName


class AddRecordings(Step):
    _file_infos: pd.DataFrame

    def __init__(self, env: EnvConfig, *, file_infos: pd.DataFrame) -> None:
        self._file_infos = file_infos

        super().__init__(env=env, name=StepName.ADD_RECORDINGS)

    def _run(self, datasets_dir: Path, dest_dataset: Path, overwrite: bool) -> None:
        file_pairs: Set[Tuple[Path, Path]] = set()
        dataset_file_map: Dict[str, Set[Tuple[Path, Path]]] = {
            d: set() for d in self._file_infos["dataset"].unique()
        }
        for _, row in self._file_infos.iterrows():  # type: ignore
            src_converted: Path = row["recording path"]
            src_raw: Path = row["recording path raw"]

            dst_converted = AddRecordings._get_dst_recording_converted_standard(
                src_converted, dest_dataset, row["dataset"]
            )
            dst_raw = AddRecordings._get_dst_recording_raw(
                src_raw, dest_dataset, row["dataset"]
            )

            file_pairs.add((src_converted, dst_converted))
            file_pairs.add((src_raw, dst_raw))
            dataset_file_map[row["dataset"]].add((src_converted, dst_converted))
            dataset_file_map[row["dataset"]].add((src_raw, dst_raw))

        if not overwrite:
            # skip things that are already added
            file_pairs = {(src, dst) for (src, dst) in file_pairs if not dst.exists()}
            dataset_file_map = {
                dataset: {(src, dst) for (src, dst) in files if not dst.exists()}
                for (dataset, files) in dataset_file_map.items()
            }

        if len(file_pairs) != 0:
            fetch_files(self._env, dataset_file_map, datasets_dir)
            copy_files(self._env, file_pairs, dest_dataset)

        return

    @staticmethod
    def _get_dst_recording_converted_standard(
        source: Path, output_dir: Path, dataset: str
    ) -> Path:
        parts = source.parts
        idx = parts.index("standard")
        return (
            output_dir
            / "recordings"
            / "converted"
            / "standard"
            / dataset
            / Path(*parts[idx + 1 :])
        )

    @staticmethod
    def _get_dst_recording_raw(source: Path, output_dir: Path, dataset: str) -> Path:
        parts = source.parts
        idx = parts.index("raw")
        return output_dir / "recordings" / "raw" / dataset / Path(*parts[idx + 1 :])
