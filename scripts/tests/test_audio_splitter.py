from typing import Dict
import pandas as pd
import pytest
from scripts.src.steps.audio_splitter import AudioSplitter


@pytest.mark.parametrize(
    "padding_ms, expected",
    [
        (
            1_000,
            [
                {
                    "recording_filename": "recording_1.wav",
                    "start": 0,
                    "end": 39_000,
                },
                {
                    "recording_filename": "recording_1.wav",
                    "start": 41_000,
                    "end": 61_000,
                },
                {
                    "recording_filename": "recording_2.wav",
                    "start": 19_000,
                    "end": 51_000,
                },
            ],
        ),
        (
            5_000,
            [
                {
                    "recording_filename": "recording_1.wav",
                    "start": 0,
                    "end": 62_000,
                },
                {
                    "recording_filename": "recording_2.wav",
                    "start": 15_000,
                    "end": 52_000,
                },
            ],
        ),
        (
            0,
            [
                {
                    "recording_filename": "recording_1.wav",
                    "start": 0,
                    "end": 38_000,
                },
                {
                    "recording_filename": "recording_1.wav",
                    "start": 42_000,
                    "end": 60_000,
                },
                {
                    "recording_filename": "recording_2.wav",
                    "start": 20_000,
                    "end": 50_000,
                },
            ],
        ),
    ],
)
def test_audio_splitting_parametrized(
    recordings: pd.DataFrame, annotations: pd.DataFrame, padding_ms: int, expected: Dict
):
    audio_splitter = AudioSplitter(recordings, annotations, padding_ms=padding_ms)
    result = audio_splitter.get_recording_splits()
    pd.testing.assert_frame_equal(result, pd.DataFrame(expected))
