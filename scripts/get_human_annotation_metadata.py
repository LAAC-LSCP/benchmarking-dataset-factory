"""
This script gets info about the human annotation data

This script looks directly at human annotation data
to find the types of annotations available and get
an estimate of how much total data was annotated

It outputs a json file

Example output:

{
  "name": "vanuatu",
  "sets": [
    {
      "name": "eaf_2023/AD",
      "columns": [
        {
          "column": "speaker_type",
          "categorical": true,
          "values": [
            "CHI",
            "OCH",
            "FEM",
            "MAL"
          ],
          "annotated_duration_ms": 760555,
          "duration_from_samples_ms": 864000,
        },
        ...
      ]
    },
    {
      "name": "eaf_2023/HM",
      "columns": [
        {
          "column": "speaker_type",
          "categorical": true,
          "values": [
            "OCH",
            "MAL",
            "FEM",
            "CHI"
          ],
          "annotated_duration_ms": 908559,
          "duration_from_samples_ms": 864000,
        },
        ...
      ]
    },
    ...
  ]
}
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import click
import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject
from pydantic import ValidationError

from .src.data.get_datasets import get_dataset_info
from .src.data.gold_standard_data import (
    STANDARD_COLUMNS,
    get_annotated_ms,
    get_num_segments,
    is_categorical,
)
from .src.data.metannots import (
    MetaAnnotations,
    get_metannots,
    get_metannots_dict,
    get_sampled_duration,
    get_sampling_count,
)
from .src.utils.constants import DATASETS, DATASETS_FOLDER, OUTPUTS_FOLDER
from .src.utils.logger import get_logger

logger = get_logger(__name__)


CATEGORICAL_CUTOFF: int = 20


class ColumnInfo(TypedDict):
    column: str
    categorical: bool
    values: List[Any]
    annotated_duration_ms: int
    duration_from_samples_ms: int


class SetInfo(TypedDict):
    name: str
    columns: List[ColumnInfo]


class DatasetInfo(TypedDict):
    name: str
    sets: List["SetInfo"]


@click.command()
@click.option(
    "--dataset-name",
    required=False,
    help="Dataset name to process. If not specified, use all datasets",
)
def get_human_annotation_metadata(dataset_name: Optional[str] = None) -> None:
    """Aggregates human annotation metadata for a given dataset \
(mostly duration-related) and saves it"""
    if dataset_name:
        get_human_annotation_metadata_for_dataset(dataset_name)

        return

    for dataset in DATASETS:
        logger.info(f"Processing {dataset}")
        get_human_annotation_metadata_for_dataset(dataset)
        logger.info(f"Done with dataset {dataset}")

    logger.info("Done")

    return


def get_human_annotation_metadata_for_dataset(dataset_name: str) -> None:
    datasets = get_dataset_info(DATASETS_FOLDER, dataset_names={dataset_name})

    dataset = next((d for d in datasets["datasets"] if d["name"] == dataset_name), None)

    if dataset is None:
        raise ValueError(f"Dataset '{dataset_name}' not found")

    project = ChildProject(get_dataset_dir(dataset["name"]))
    am = AnnotationManager(project)

    annotations: pd.DataFrame = am.annotations

    dataset_info: DatasetInfo = {
        "name": dataset_name,
        "sets": [],
    }
    for gold_std_set in dataset["gold_std_sets"]:
        set_info: SetInfo = {
            "name": gold_std_set,
            "columns": [],
        }
        set_info["columns"] += get_column_info(  # type: ignore
            dataset_name,
            gold_std_set,
            annotations,
            am,
        )

        dataset_info["sets"].append(set_info)

    save_dataset_info(dataset_info, dataset_name)

    return


def save_dataset_info(dataset_info: DatasetInfo, dataset_name: str) -> None:
    output_location: Path = (
        OUTPUTS_FOLDER
        / "human_annotation_data"
        / f"human_annotation_data-{dataset_name}.json"
    )
    output_location.parent.mkdir(parents=True, exist_ok=True)

    with open(output_location, "w") as f:
        json.dump(dataset_info, f, indent=2)

    logger.info(f"Finished running script. Outputs at {str(output_location)}")


def get_column_info(
    dataset_name: str,
    set_name: str,
    annotations: pd.DataFrame,
    am: AnnotationManager,
) -> List[ColumnInfo]:
    result: List[ColumnInfo] = []

    gold_std_annotations = annotations[annotations["set"] == set_name]

    segments = am.get_segments(gold_std_annotations)

    interesting_cols = set(segments.columns) - STANDARD_COLUMNS

    for col in interesting_cols:
        categorical, values = is_categorical(segments, col, 20)

        metannots_dict: Optional[Dict] = None
        try:
            metannots: Optional[MetaAnnotations] = get_metannots(
                DATASETS_FOLDER, dataset_name, set_name
            )

            if metannots is None:
                continue

            metannots_dict = metannots.model_dump()
        except ValidationError as e:
            logger.warning(f"Validation warnings: {e}")

            metannots_dict = get_metannots_dict(DATASETS_FOLDER, dataset_name, set_name)

            if metannots_dict is None:
                continue

        result.append(
            {
                "column": col,
                "categorical": categorical,
                "annotated_duration_ms": get_annotated_ms(segments, col),
                "duration_from_samples_ms": (
                    get_sampled_duration(metannots_dict, gold_std_annotations)
                    if metannots_dict
                    else -1
                ),
                "number_of_samples": get_sampling_count(
                    metannots_dict, gold_std_annotations
                ),
                "num_of_non_empty_segments": get_num_segments(segments, col),
            }
        )

    return result


def get_dataset_dir(name: str) -> Path:
    return DATASETS_FOLDER / name


if __name__ == "__main__":
    get_human_annotation_metadata()
