"""
Pydantic boilerplate for the `datasets.json` file in the metadata folder
"""

from pathlib import Path
from typing import List

from pydantic import BaseModel, ValidationInfo, field_validator


def get_datasets(datasets_folder: Path) -> BaseModel:
    class Dataset(BaseModel):
        name: str
        gold_std_sets: List[str]

        @field_validator("name")
        @classmethod
        def validate_name(cls, name: str) -> str:
            if not (datasets_folder / name).exists():
                raise ValueError(f"Dataset {name} not found in datasets folder")

            return name

        @field_validator("gold_std_sets")
        @classmethod
        def validate_gold_std_sets(
            cls, gold_std_sets: List[str], info: ValidationInfo
        ) -> List[str]:
            for gold_std_set in gold_std_sets:
                dataset_name: str = info.data["name"]

                if not (
                    datasets_folder / dataset_name / "annotations" / gold_std_set
                ).exists():
                    raise ValueError(
                        f"Human annotation set {gold_std_set} not found in dataset \
                        {dataset_name}"
                    )

            return gold_std_sets

    class Datasets(BaseModel):
        datasets: List[Dataset]

    return Datasets
