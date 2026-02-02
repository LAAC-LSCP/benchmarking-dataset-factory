import pandas as pd
import pytest


@pytest.fixture
def recordings() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "experiment": "exp1",
                "child_id": "C1",
                "date_iso": "2024-06-01",
                "start_time": "09:00:00",
                "recording_device": "LENA",
                "recording_filename": "recording_1.wav",
                "duration": 62_000,
            },
            {
                "experiment": "exp1",
                "child_id": "C2",
                "date_iso": "2024-06-02",
                "start_time": "10:30:00",
                "recording_device": "LENA",
                "recording_filename": "recording_2.wav",
                "duration": 52_000,
            },
        ]
    )


@pytest.fixture
def annotations() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "set": "human",
                "recording_filename": "recording_1.wav",
                "raw_filename": "recording_1.wav",
                "time_seek": 0,
                "range_onset": 42_000,
                "range_offset": 60_000,
                "annotation_filename": "recording_1_0_60000",
            },
            {
                "set": "human",
                "recording_filename": "recording_1.wav",
                "raw_filename": "recording_1.wav",
                "time_seek": 0,
                "range_onset": 0,
                "range_offset": 38_000,
                "annotation_filename": "recording_1_0_60000",
            },
            {
                "set": "human",
                "recording_filename": "recording_2.wav",
                "raw_filename": "recording_2.mp3",
                "time_seek": 5_000,
                "range_onset": 15_000,
                "range_offset": 45_000,
                "annotation_filename": "recording_2_15000_45000",
            },
        ]
    )
