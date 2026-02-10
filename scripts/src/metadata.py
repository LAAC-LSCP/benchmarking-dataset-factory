import json
from pathlib import Path
from typing import Dict

from scripts.src.human_annotation_metadata.schema_generated_metadata import (
    GeneratedDatasets,
)
from scripts.src.utils.constants import OUTPUTS_FOLDER


def get_generated_metadata() -> GeneratedDatasets:
    human_annotation_data_dir: Path = (
        OUTPUTS_FOLDER / "human_annotation_data"
    ).resolve()

    if not human_annotation_data_dir.exists():
        raise FileNotFoundError(
            f"human annotation data not found at {human_annotation_data_dir!s}"
        )

    data: Dict = {"datasets": []}
    for f in human_annotation_data_dir.iterdir():
        if not f.is_file():
            continue

        with open(f, "r") as f:
            data["datasets"].append(json.load(f))

    return GeneratedDatasets(**data)


def get_manual_metadata() -> Dict:
    manual_annotation_metadata: Path = (
        OUTPUTS_FOLDER / "manually_annotated_metadata.json"
    ).resolve()

    if not manual_annotation_metadata.exists():
        raise FileNotFoundError(
            f"manual annotations file not found at {manual_annotation_metadata!s}"
        )

    data: Dict
    with open(manual_annotation_metadata, "r") as f:
        data = json.load(f)

    return data
