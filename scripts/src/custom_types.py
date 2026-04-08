from enum import StrEnum
from typing import Any, List, TypedDict


class DatasetType(StrEnum):
    VTC = "vtc"
    ADDRESSEE = "addressee"
    TRANSCRIPTION = "transcription"
    VOCAL_MATURITY = "vcm"


class ColumnInfo(TypedDict):
    column: str
    categorical: bool
    annotation_duration_ms: int
    duration_from_samples_ms: int


class CPSet(TypedDict):
    name: str
    columns: List[ColumnInfo]


class Data(TypedDict):
    name: str
    sets: List[CPSet]


class Dataset(TypedDict):
    name: str
    gold_std_sets: List[str]


class Datasets(TypedDict):
    datasets: List[Dataset]
