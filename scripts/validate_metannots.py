"""
This script validates metannots based on the annotation schema outlined in
ChildProject's documentation (v0.4.3.)

Prints out validation errors. Usage:

`python3 scripts/validate_metannots.py`

Or with output redirection:

`python3 scripts/validate_metannots.py > validation_errors.txt`
"""

from pathlib import Path

import click
from custom_types.datasets_json import get_datasets
from custom_types.metannots import get_metannots
from pydantic import ValidationError

CURRENT_FILE: Path = Path(__file__)
SCRIPT_FOLDER: Path = CURRENT_FILE.parent
METADATA_FOLDER: Path = (SCRIPT_FOLDER / ".." / "metadata").resolve()
DATASETS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "datasets").resolve()
OUTPUTS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "outputs").resolve()
CATEGORICAL_CUTOFF: int = 20


@click.command()
def validate_metannots() -> None:
    """Validate metannots. Prints out validation errors across datasets and sets"""
    datasets = get_datasets(DATASETS_FOLDER)

    print("Printing out validation errors...")
    for dataset in datasets["datasets"]:
        for gold_std_set in dataset["gold_std_sets"]:
            try:
                get_metannots(DATASETS_FOLDER, dataset["name"], gold_std_set)
            except ValidationError as e:
                print(
                    f"ERROR: validation error in \
dataset '{dataset["name"]}', set '{gold_std_set}': {e}"
                )

    print("Done!")

    return


if __name__ == "__main__":
    validate_metannots()
