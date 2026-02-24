"""
This script takes the outputs of `get_human_annotation_metadata.py`
and creates a table with the various sets, and totals
"""

import json
from pathlib import Path
from typing import List

import click
import pandas as pd

from .src.custom_types import Data, DatasetType
from .src.data.get_metannots_df import get_metannots_df
from .src.utils.constants import DATASETS, DATASETS_FOLDER

CURRENT_FILE: Path = Path(__file__)
HUMAN_ANNOTATION_METADATA_OUTPUT: Path = (
    CURRENT_FILE.parent / ".." / "outputs" / "human_annotation_data"
).resolve()


@click.command()
@click.option(
    "--output-path",
    type=Path,
    help="Output path of dataframe",
)
@click.option(
    "--type",
    type=click.Choice(
        ["vtc", "addressee", "transcription", "vcm"], case_sensitive=False
    ),
    required=True,
    help="Type of dataset to create",
)
def create_table_corpora_info(output_path: str, type: str):
    """
    Creates a table with info about the various human annotation corpora
    """
    dataset_type = DatasetType(type)
    relevant_column: str
    if dataset_type == DatasetType.ADDRESSEE:
        relevant_column = "has_addressee"
    elif dataset_type == DatasetType.TRANSCRIPTION:
        relevant_column = "has_transcription"
    elif dataset_type == DatasetType.VOCAL_MATURITY:
        relevant_column = "has_vcm_type"
    elif dataset_type == DatasetType.VTC:
        relevant_column = "has_speaker_type"
    else:
        raise ValueError("dataset type not valid")

    duration_data = get_datasets_duration_metadata(HUMAN_ANNOTATION_METADATA_OUTPUT)
    metannots_df: pd.DataFrame = get_metannots_df(
        DATASETS_FOLDER,
        print_errors=False,
        dataset_names=DATASETS,
    )

    df = get_datasets_duration_table(duration_data)

    merged = pd.merge(
        df,
        metannots_df[["dataset", "segmentation", relevant_column]],
        left_on=["dataset", "set"],
        right_on=["dataset", "segmentation"],
        how="left",
    )

    merged = merged[merged[relevant_column] == "Y"]

    merged = merged.drop([relevant_column, "segmentation"], axis=1)

    merged.to_csv(Path(str(output_path) + f"_{relevant_column}"), index=False)

    return


def get_datasets_duration_metadata(data_folder: Path) -> List[Data]:
    return [
        get_dataset_duration_metadata(f) for f in data_folder.iterdir() if f.is_file()
    ]


def get_dataset_duration_metadata(f: Path) -> Data:
    data: Data
    with open(f, "r") as raw_data:
        data = json.load(raw_data)

    return data


def get_datasets_duration_table(data: List[Data]) -> pd.DataFrame:
    datas = [
        row for dataset in data for row in get_dataset_duration_table_data(dataset)
    ]

    return pd.DataFrame(datas)


def get_dataset_duration_table_data(dataset: Data) -> List[dict]:
    return [
        {
            "dataset": dataset["name"],
            "set": s["name"],
            "sampled_duration_minutes": ms_to_min(
                s["columns"][0]["duration_from_samples_ms"]
            ),
            "duration_annotated_minutes": ms_to_min(
                s["columns"][0]["annotated_duration_ms"]
            ),
        }
        for s in dataset["sets"]
    ]


def ms_to_min(ms: int) -> float:
    if ms is None:
        return None

    return round(ms / 1000 / 60, 2)


if __name__ == "__main__":
    create_table_corpora_info()
