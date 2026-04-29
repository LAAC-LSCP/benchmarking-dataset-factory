"""
This script validates metannots based on the annotation schema outlined in
ChildProject's documentation (v0.4.3.)

Prints out validation errors. Usage:

`python3 scripts/validate_metannots.py`

Or with output redirection:

`python3 scripts/validate_metannots.py > validation_errors.txt`
"""

import click
from pydantic import ValidationError

from .src.custom_types import Datasets
from .src.data.get_datasets import get_dataset_info
from .src.data.metannots import get_metannots
from .src.utils.constants import DATASETS_FOLDER
from .src.utils.logger import get_logger

CATEGORICAL_CUTOFF: int = 20


logger = get_logger(__name__)


@click.command()
@click.option(
    "--dataset-name",
    type=str,
    required=False,
    default=None,
    help="Dataset name to process",
)
def validate_metannots(dataset_name: str | None) -> None:
    """Validate metannots. Prints out validation errors across datasets and sets"""
    datasets: Datasets

    if dataset_name is not None:
        datasets = get_dataset_info(DATASETS_FOLDER, dataset_names={dataset_name})
    else:
        datasets = get_dataset_info(DATASETS_FOLDER)

    logger.info("Printing out validation errors...")
    for dataset in datasets["datasets"]:
        for gold_std_set in dataset["gold_std_sets"]:
            try:
                get_metannots(DATASETS_FOLDER, dataset["name"], gold_std_set)
            except ValidationError as e:
                logger.exception(f"Validation error in \
dataset '{dataset["name"]}', set '{gold_std_set}'")

    logger.info("Done!")

    return


if __name__ == "__main__":
    validate_metannots()
