"""
Pydantic boilerplate for the `datasets.json` file in the metadata folder
"""

from pathlib import Path
from typing import List, TypedDict

import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject


class Dataset(TypedDict):
    name: str
    gold_std_sets: List[str]


class Datasets(TypedDict):
    datasets: List[Dataset]


# TODO: this function runs really slow because it uses the annotation manager
def get_datasets(datasets_folder: Path, print_info: bool = False) -> Datasets:
    result: Datasets = {"datasets": []}

    datasets = [d for d in datasets_folder.iterdir() if d.is_dir()]

    for ds in datasets:
        project = ChildProject(ds)
        am = AnnotationManager(project)

        sets_metadata: pd.DataFrame = am.get_sets_metadata()

        if "method" in sets_metadata:
            sets_metadata = sets_metadata[sets_metadata["method"] == "manual"]
        elif print_info:
            print(f"INFO: no 'method' column in sets metadata for \
dataset {ds.name}. Assuming all sets are manual")

        manual_sets: List[str] = [s for s in sets_metadata.index]

        dataset: Dataset = {
            "name": ds.name,
            "gold_std_sets": manual_sets,
        }

        result["datasets"].append(dataset)

    return result
