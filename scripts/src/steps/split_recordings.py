import subprocess
from functools import partial
from itertools import batched
from math import floor
from pathlib import Path
from typing import List, Set, Tuple

import pandas as pd

from scripts.src.steps.file_management import datalad_save
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class SplitRecordings(Step):
    _remove_full_recordings: bool

    def __init__(self, env: EnvConfig, remove_full_recordings: bool = True) -> None:
        self._remove_full_recordings = remove_full_recordings

        super().__init__(env=env, name=StepName.SPLIT_RECORDINGS)

    def _run(self, _: Path, dest_dataset: Path, overwrite: bool) -> None:
        annotations = SplitRecordings._get_annotations(dest_dataset)
        recordings = SplitRecordings._get_recordings(dest_dataset)

        logger.info(
            "Calculating range offsets again... (annotations.csv can be mistaken)"
        )
        # annotations.csv can't always be trusted with range_offsets. And we might
        # end up with many duplicates of entire files for this reason
        # NOTE: using converted recordings here as they are often shorter than raw
        real_offsets = [
            floor(
                SplitRecordings._get_audio_duration(
                    SplitRecordings._get_recording_paths(dest_dataset, rec_name)[1]
                )
                * 1000
            )
            - int(time_seek)
            for rec_name, time_seek in zip(
                annotations["recording_filename"], annotations["time_seek"]
            )
        ]

        annotations["real_range_offset"] = [
            min(annot_offset, real_offset)
            for annot_offset, real_offset in zip(
                annotations["range_offset"], real_offsets
            )
        ]

        unique_annots = annotations[
            ["recording_filename", "range_onset", "real_range_offset", "time_seek"]
        ].drop_duplicates()

        logger.info(f"Splitting a maximum of {len(unique_annots) * 2} times...")
        for batch in batched(unique_annots.iterrows(), 20):
            commands: List[Tuple[Path, int, int, int, bool]] = []
            for _, row in batch:  # type: ignore
                rec_name, onset, offset, time_seek = row
                raw, converted = SplitRecordings._get_recording_paths(
                    dest_dataset, rec_name
                )

                commands.append(
                    (converted, int(onset), int(offset), int(time_seek), overwrite)
                )
                commands.append(
                    (raw, int(onset), int(offset), int(time_seek), overwrite)
                )

            self._split_recordings(commands)

        pairs: Set[Tuple[Path, Path]] = set(
            map(
                partial(SplitRecordings._get_recording_paths, dest_dataset),
                annotations["recording_filename"],
            )
        )

        datalad_save(self._env, dest_dataset, "Saved recordings")

        self._update_annotations(dest_dataset, annotations)
        self._update_recordings(dest_dataset, recordings, annotations)

        if self._remove_full_recordings:
            for batch in batched(pairs, 100):  # type: ignore
                self._remove_recordings(dest_dataset, batch)  # type: ignore

        return

    def _split_recordings(
        self,
        jobs: List[Tuple[Path, int, int, int, bool]],
    ) -> None:
        sox_commands = []
        for rec, onset_ms, offset_ms, time_seek, overwrite in jobs:
            onset_s = onset_ms / 1000
            offset_s = offset_ms / 1000
            time_seek_s = time_seek / 1000
            duration = offset_s - onset_s

            output_rec = SplitRecordings._get_final_rec_path(
                rec, onset_s, offset_s, time_seek_s
            )

            if output_rec.exists() and not overwrite:
                continue

            sox_commands.append(f"sox {rec!s} {output_rec!s} trim \
{(onset_s + time_seek)!s} {duration!s}")

        if not sox_commands:
            return

        shell_commands = [
            f"source {self._env.conda_activate_file!s}",
            f"conda activate {self._env.conda_childproject_env}",
        ]
        shell_commands.extend(sox_commands)
        shell_command = " && ".join(shell_commands)

        try:
            subprocess.run(shell_command, shell=True, check=True)
            logger.info(f"Created {len(sox_commands)} files through splitting")
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise e

        return

    def _update_annotations(
        self, dest_dataset: Path, original_annotations: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info("Updating annotations...")
        annotations = original_annotations.copy()
        annotations["recording_filename"] = annotations.apply(  # type: ignore
            lambda row: SplitRecordings._get_final_rec_path(
                rec=Path(row["recording_filename"]),
                onset_s=int(row["range_onset"]) / 1000,
                offset_s=int(row["real_range_offset"]) / 1000,
                time_seek_s=int(row["time_seek"]) / 1000,
            ),
            axis=1,
        )
        annotations["range_offset"] = annotations["real_range_offset"]
        annotations["range_onset"] = 0
        annotations["time_seek"] = 0

        annotations = annotations.drop("real_range_offset", axis=1)

        annotations.to_csv(dest_dataset / "metadata" / "annotations.csv", index=False)
        datalad_save(self._env, dest_dataset, "Updated annotations.csv")

        return annotations

    def _update_recordings(
        self,
        dest_dataset: Path,
        recordings: pd.DataFrame,
        original_annotations: pd.DataFrame,
    ) -> pd.DataFrame:
        logger.info("Updating recordings...")

        recordings = pd.merge(
            recordings,
            original_annotations[
                ["recording_filename", "range_onset", "real_range_offset", "time_seek"]
            ],
            on="recording_filename",
            how="left",
        )

        recordings["recording_filename"] = recordings.apply(  # type: ignore
            lambda row: SplitRecordings._get_final_rec_path(
                rec=Path(row["recording_filename"]),
                onset_s=int(row["range_onset"]) / 1000,
                offset_s=int(row["real_range_offset"]) / 1000,
                time_seek_s=int(row["time_seek"]) / 1000,
            ),
            axis=1,
        )

        recordings = recordings.drop(
            ["real_range_offset", "range_onset", "time_seek"], axis=1
        )
        recordings = recordings.drop_duplicates()

        recordings.to_csv(dest_dataset / "metadata" / "recordings.csv", index=False)
        datalad_save(self._env, dest_dataset, "Updated recordings.csv")

        return recordings

    def _remove_recordings(
        self, dest_dataset: Path, recordings: Set[Tuple[Path, Path]]
    ) -> None:
        files = [str(f) for pair in recordings for f in pair]

        if not files:
            logger.info("No recordings to remove.")
            return

        # Join all file paths into a single string for the shell command
        files_str = " ".join(files)

        commands = [
            f"source {self._env.conda_activate_file!s}",
            f"conda activate {self._env.conda_childproject_env}",
            f"datalad drop {files_str} --reckless kill",
            f"datalad remove {files_str} --reckless kill -m \
'removed {len(files)} recordings'",
        ]
        shell_command = " && ".join(commands)

        try:
            subprocess.run(shell_command, shell=True, check=True, cwd=dest_dataset)
            logger.info(f"Removed {len(files)} files from dataset")
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise e

        return

    @staticmethod
    def _get_final_rec_path(
        rec: Path, onset_s: float, offset_s: float, time_seek_s: float
    ) -> Path:
        return rec.parent / (
            rec.stem
            + f"-{(onset_s + time_seek_s)!s}to{(offset_s + time_seek_s)!s}{rec.suffix}"
        )

    @staticmethod
    def _get_audio_duration(path: Path) -> float:
        result = subprocess.run(
            ["sox", "--i", "-D", str(path)], capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())

    @staticmethod
    def _get_annotations(dest_dataset: Path) -> pd.DataFrame:
        return pd.read_csv(dest_dataset / "metadata" / "annotations.csv")

    @staticmethod
    def _get_recordings(dest_dataset: Path) -> pd.DataFrame:
        return pd.read_csv(dest_dataset / "metadata" / "recordings.csv")

    @staticmethod
    def _get_recording_paths(dest_dataset: Path, rec_name: str) -> Tuple[Path, Path]:
        r_raw_path = dest_dataset / "recordings" / "raw" / rec_name
        r_converted_path = (
            dest_dataset / "recordings" / "converted" / "standard" / rec_name
        ).with_suffix(".wav")

        if not r_raw_path.exists():
            raise FileNotFoundError(f"File not found at {r_raw_path!s}")

        if not r_converted_path.exists():
            raise FileNotFoundError(f"File not found at {r_converted_path!s}")

        return r_raw_path, r_converted_path
