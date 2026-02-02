from typing import Annotated, Dict
import pandas as pd
from pyannote.core import Annotation, Segment, Timeline


class AudioSplitter:
    """Helper class to split audio files

    Created a separate class to properly test this functionality, since it's fairly involved
    to do it well

    We use pyannote-core to combine segments and find an efficient support for the audio,
    minimising the amount of audio to save"""

    _recordings: pd.DataFrame
    _annotations: pd.DataFrame
    _padding_ms: int

    def __init__(
        self, recordings: pd.DataFrame, annotations: pd.DataFrame, padding_ms: int = 0
    ):
        self._recordings = recordings
        self._annotations = annotations
        self._padding_ms = padding_ms

    def get_recording_file_for_annotation(self) -> pd.DataFrame:
        raise NotImplementedError

    def get_recording_splits(self) -> pd.DataFrame:
        timelines: Dict[Annotated[str, "recording filename"], Timeline] = {}
        for _, row in self._annotations.iterrows():
            rec_filename = row["recording_filename"]

            if rec_filename not in timelines:
                timelines[rec_filename] = Timeline()

            timelines[rec_filename].add(
                Segment(
                    start=(row["range_onset"] + row["time_seek"] - self._padding_ms),
                    end=(row["range_offset"] + row["time_seek"] + self._padding_ms),
                )
            )

        for rec_filename in timelines.keys():
            # simplify support
            timelines[rec_filename] = timelines[rec_filename].crop(
                Segment(start=0, end=self._get_duration(rec_filename))
            )
            timelines[rec_filename] = timelines[rec_filename].support()

        split_list = []
        for rec_filename in timelines.keys():
            timeline = timelines[rec_filename]
            split_list.extend(
                [
                    {
                        "recording_filename": rec_filename,
                        "start": s.start,
                        "end": s.end,
                    }
                    for s in timeline
                ]
            )

        return pd.DataFrame(split_list)

    def _get_duration(self, rec_filename: str) -> int:
        return int(
            self._recordings[self._recordings["recording_filename"] == rec_filename][
                "duration"
            ]
        )

    @staticmethod
    def crop_annotation(annotation: Annotation, start: int, end: int) -> Annotation:
        return annotation.crop(Timeline(segments={Segment(start=start, end=end)}))

    @staticmethod
    def calculate(onset: int, offset: int, time_seek: int) -> None:
        onset = onset + time_seek
        offset = offset + time_seek
