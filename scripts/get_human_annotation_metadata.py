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

from custom_types.datasets_json import get_datasets
from custom_types.metannots import (MetaAnnotations, get_metannots,
                                    get_sampled_duration)
from helpers.gold_standard_data import (STANDARD_COLUMNS, get_annotated_ms,
                                        is_categorical)

CURRENT_FILE: Path = Path(__file__)
SCRIPT_FOLDER: Path = CURRENT_FILE.parent
METADATA_FOLDER: Path = (SCRIPT_FOLDER / ".." / "metadata").resolve()
DATASETS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "datasets").resolve()
OUTPUTS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "outputs").resolve()
CATEGORICAL_CUTOFF: int = 20


class DatasetInfo(TypedDict):
    name: str
    sets: List[str]


class SetInfo(TypedDict):
    column: str
    categorical: bool
    values: List[Any]
    annotated_duration_ms: int
    recording_duration_ms: int


@click.command()
@click.option("--dataset-name", help="Dataset name to process")
def get_human_annotation_metadata(dataset_name: str) -> None:
    datasets = get_datasets(DATASETS_FOLDER)

    if dataset_name not in [d["name"] for d in datasets["datasets"]]:
        raise ValueError(f"Dataset '{dataset_name}' not found")

    dataset = next((d for d in datasets["datasets"] if d["name"] == dataset_name), None)

    project = ChildProject(get_dataset_dir(dataset["name"]))
    am = AnnotationManager(project)
    am.read()

    annotations: pd.DataFrame = am.annotations

    dataset_info: DatasetInfo = {
        "name": dataset_name,
        "sets": [],
    }
    for gold_std_set in dataset["gold_std_sets"]:
        set_info = {
            "name": gold_std_set,
            "columns": [],
        }
        set_info["columns"] += get_set_info(
            project, dataset_name, gold_std_set, annotations, am
        )

        dataset_info["sets"].append(set_info)

    save_dataset_info(dataset_info, dataset_name)


def save_dataset_info(dataset_info: Dict, dataset_name: str) -> None:
    output_location: Path = (
        OUTPUTS_FOLDER
        / "human_annotation_data"
        / f"human_annotation_data-{dataset_name}.json"
    )
    output_location.parent.mkdir(parents=True, exist_ok=True)

    with open(output_location, "w") as f:
        json.dump(dataset_info, f, indent=2)

    print(f"Finished running script. Outputs at {str(output_location)}")


def get_set_info(
    project: ChildProject,
    dataset_name: str,
    set_name: str,
    annotations: pd.DataFrame,
    am: AnnotationManager,
) -> List[SetInfo]:
    result: List[SetInfo] = []

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
            print(f"Validation warnings: {e}")

            metannots_dict: Optional[Dict] = get_metannots(
                DATASETS_FOLDER, dataset_name, set_name, safe_load=True
            )

            if metannots_dict is None:
                continue

        result.append(
            {
                "column": col,
                "categorical": categorical,
                "values": values,
                "annotated_duration_ms": get_annotated_ms(segments, col),
                "duration_from_samples_ms": (
                    get_sampled_duration(metannots_dict) if metannots_dict else None
                ),
            }
        )

    return result


def get_dataset_dir(name: str) -> Path:
    return DATASETS_FOLDER / name


if __name__ == "__main__":
    get_human_annotation_metadata()
