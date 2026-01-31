"""
Pydantic boilerplate for the `datasets.json` file in the metadata folder
"""

from pathlib import Path
from typing import List, Optional, Set

import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject

from scripts.src.custom_types import Dataset, Datasets
from scripts.src.utils.constants import DATASETS
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


# TODO: this function runs really slow because it uses the annotation manager
def get_dataset_info(
    datasets_folder: Path,
    print_info: bool = False,
    dataset_names: Optional[Set[str]] = None,
) -> Datasets:
    result: Datasets = {"datasets": []}

    if not dataset_names:
        dataset_names = DATASETS

    datasets = {
        d for d in datasets_folder.iterdir() if d.is_dir() and d.name in dataset_names
    }

    for ds in datasets:
        project = ChildProject(ds)
        am = AnnotationManager(project)

        sets_metadata: pd.DataFrame = am.get_sets_metadata()

        if "method" in sets_metadata:
            sets_metadata = sets_metadata[sets_metadata["method"] == "manual"]
        elif print_info:
            logger.info(f"No 'method' column in sets metadata for \
dataset {ds.name}. Assuming all sets are manual")

        manual_sets: List[str] = [s for s in sets_metadata.index]

        dataset: Dataset = {
            "name": ds.name,
            "gold_std_sets": manual_sets,
        }

        result["datasets"].append(dataset)

    return result
