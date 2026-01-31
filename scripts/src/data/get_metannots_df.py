from typing import Dict, List, Optional, Set

import pandas as pd
from pydantic import ValidationError

from scripts.src.data.get_datasets import get_dataset_info
from scripts.src.data.metannots import get_metannots, get_metannots_dict
from scripts.src.utils.constants import DATASETS_FOLDER
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


def get_metannots_df(
    print_errors: bool = False, dataset_names: Optional[Set[str]] = None
) -> pd.DataFrame:
    datasets = get_dataset_info(
        DATASETS_FOLDER, print_info=print_errors, dataset_names=dataset_names
    )

    metannots_list: List[Dict] = []
    for dataset in datasets["datasets"]:
        for gold_std_set in dataset["gold_std_sets"]:
            metannots_dict: Optional[Dict] = None
            try:
                metannots = get_metannots(
                    DATASETS_FOLDER, dataset["name"], gold_std_set
                )

                if metannots is None:
                    continue

                metannots_dict = metannots.model_dump()
            except ValidationError as e:
                if print_errors:
                    logger.warning(f"Validation warnings: {e}")

                metannots_dict = get_metannots_dict(
                    DATASETS_FOLDER, dataset["name"], gold_std_set
                )

                if metannots_dict is None:
                    continue

            metannots_dict["set"] = gold_std_set
            metannots_dict["dataset"] = dataset["name"]

            metannots_list.append(metannots_dict)

    return pd.DataFrame(metannots_list)
