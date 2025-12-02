"""
Helpers to parse the converted .csv files of gold standard human annotation data
"""

from typing import List, Set, Tuple

import numpy as np
import pandas as pd

STANDARD_COLUMNS: Set[str] = {
    "segment_onset",
    "segment_offset",
    "raw_filename",
    "set",
    "recording_filename",
    "time_seek",
    "range_onset",
    "range_offset",
    "format",
    "filter",
    "annotation_filename",
    "imported_at",
    "package_version",
    "error",
    "merged_from",
    "duration",  # Comes from merging segments with recordings
}


def is_categorical(
    segments: pd.DataFrame, column: str, n: int
) -> Tuple[bool, List | None]:
    """
    Determines if a column in segments is categorical or not
    based simply on a minimum number of unique values

    If categorical also returns the unique values
    """
    unique_vals: np.ndarray = segments[column].unique()

    if len(unique_vals) <= n:
        return True, list([str(val) for val in unique_vals])

    return False, None


def get_annotated_ms(segments: pd.DataFrame, column: str) -> int:
    """
    Get the number of ms that were actually annotated by people for a given column
    """
    non_na_segments = segments[segments[column].notna()]

    return int(
        sum(non_na_segments["segment_offset"] - non_na_segments["segment_onset"])
    )


def get_recording_length_ms(segments: pd.DataFrame, column: str) -> int:
    """
    Get the actual length of recordings on which this column was annotated
    """
    non_na_segments = segments[segments[column].notna()]

    return int(sum(non_na_segments["duration"]))
