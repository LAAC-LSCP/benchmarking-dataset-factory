import functools
import shutil
import subprocess
from functools import partial
from itertools import batched
from pathlib import Path
from typing import List, Set, Tuple

import pandas as pd

from scripts.src.steps.add_annotations import AddAnnotations
from scripts.src.steps.file_management import datalad_save
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.audio_splitter import AudioSplitter
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class SplitRecordings(Step):
    _remove_full_recordings: bool
    _annotations: pd.DataFrame
    _recordings: pd.DataFrame

    def __init__(
        self,
        env: EnvConfig,
        annotations: pd.DataFrame,
        recordings: pd.DataFrame,
        remove_full_recordings: bool = True,
    ) -> None:
        self._remove_full_recordings = remove_full_recordings
        self._annotations = annotations
        self._recordings = recordings

        super().__init__(env=env, name=StepName.SPLIT_RECORDINGS)

    def _run(self, _: Path, dest_dataset: Path) -> None:
        annotations = self._annotations
        recordings = self._recordings

        splitter = AudioSplitter(recordings, annotations, padding_ms=0)
        recordings = splitter.get_recording_splits()
        recordings["new_recording_filename"] = recordings.apply(
            lambda row: SplitRecordings._get_final_rec_path(
                Path(row["recording_filename"]), row["start"], row["end"], 0
            ),
            axis=1,
        )
        annotations = annotations.apply(
            functools.partial(
                splitter.set_annotation_from_split_recordings,
                split_recordings=recordings,
            ),
            axis=1,
        )

        unique_annots = annotations[
            [
                "recording_filename",
                "original_recording_filename",
                "range_onset",
                "range_offset",
                "time_seek",
                "original_annotation_filename",
            ]
        ].drop_duplicates()

        logger.info(f"Splitting a maximum of {len(unique_annots) * 2} times...")
        for batch in batched(unique_annots.iterrows(), 20):
            commands: List[Tuple[Path, int, int, int]] = []
            for _, row in batch:  # type: ignore
                _, original_rec_name, onset, offset, time_seek, _ = row
                raw, converted = SplitRecordings._get_recording_paths(
                    dest_dataset, original_rec_name
                )

                commands.append((converted, int(onset), int(offset), int(time_seek)))
                commands.append((raw, int(onset), int(offset), int(time_seek)))

            self._split_recordings(commands)

        datalad_save(self._env, dest_dataset, "Saved recordings")

        file_pairs = {
            (
                AddAnnotations._get_annotation_path(
                    dest_dataset, row["set"], row["original_annotation_filename"]
                ),
                AddAnnotations._get_annotation_path(
                    dest_dataset, row["set"], row["annotation_filename"]
                ),
            )
            for _, row in annotations.iterrows()
        }

        for file_pair in file_pairs:
            if not file_pair[0].exists():
                continue

            shutil.move(src=file_pair[0], dst=file_pair[1])

        datalad_save(self._env, dest_dataset, "Renamed annotations")

        self._update_annotations_csv(dest_dataset, annotations)
        self._update_recordings_csv(dest_dataset, recordings)

        pairs: Set[Tuple[Path, Path]] = set(
            map(
                partial(SplitRecordings._get_recording_paths, dest_dataset),
                annotations["original_recording_filename"],
            )
        )
        if self._remove_full_recordings:
            for batch in batched(pairs, 100):  # type: ignore
                self._remove_recordings(dest_dataset, batch)  # type: ignore

        return

    def _split_recordings(
        self,
        jobs: List[Tuple[Path, int, int, int]],
    ) -> None:
        sox_commands = []
        for rec, onset_ms, offset_ms, time_seek_ms in jobs:
            onset_s = onset_ms / 1000
            offset_s = offset_ms / 1000
            duration = offset_s - onset_s

            output_rec = SplitRecordings._get_final_rec_path(
                rec, onset_ms, offset_ms, time_seek_ms
            )

            if output_rec.exists():
                continue

            sox_commands.append(f"sox {rec!s} {output_rec!s} trim \
{(onset_s + time_seek_ms)!s} {duration!s}")

        if not sox_commands:
            return

        shell_commands = [
            self._env.conda_activation_str,
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

    def _update_annotations_csv(
        self, dest_dataset: Path, annotations: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info("Updating annotations...")
        annotations = annotations.copy()
        annotations = annotations.drop(
            ["original_recording_filename", "original_annotation_filename"], axis=1
        )

        annotations.to_csv(dest_dataset / "metadata" / "annotations.csv", index=False)
        datalad_save(self._env, dest_dataset, "Updated annotations.csv")

        return annotations

    def _update_recordings_csv(
        self,
        dest_dataset: Path,
        recordings_index: pd.DataFrame,
    ) -> pd.DataFrame:
        logger.info("Updating recordings...")
        recordings = self._recordings.copy()

        recordings = pd.merge(
            recordings, recordings_index, on="recording_filename", how="left"
        )
        recordings["recording_filename"] = recordings["new_recording_filename"]

        recordings = recordings.drop(["start", "end", "new_recording_filename"], axis=1)
        recordings = recordings.drop_duplicates()
        recordings["experiment"] = "benchmarking"

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
            self._env.conda_activation_str,
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
        rec: Path, onset_ms: float, offset_ms: float, time_seek_ms: float
    ) -> Path:
        return rec.parent / (
            rec.stem
            + f"-{(onset_ms + time_seek_ms)!s}to{(offset_ms + time_seek_ms)!s}{rec.suffix}"
        )

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
