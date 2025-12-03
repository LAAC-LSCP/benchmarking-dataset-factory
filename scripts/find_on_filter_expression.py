"""
This script aggregates the metannots files into a csv
file, making it easy to apply filter expressions

To see the list of columns, look under `metannots.py`, or in the
ChildProject documentation
"""

from pathlib import Path
from typing import Dict, List, Optional

import click
import pandas as pd
from custom_types.datasets_json import get_datasets
from custom_types.metannots import get_metannots, get_metannots_dict
from pydantic import ValidationError

CURRENT_FILE: Path = Path(__file__)
SCRIPT_FOLDER: Path = CURRENT_FILE.parent
METADATA_FOLDER: Path = (SCRIPT_FOLDER / ".." / "metadata").resolve()
DATASETS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "datasets").resolve()


@click.command()
@click.option(
    "--filter-expr",
    required=False,
    default=None,
    help="Filter expression like 'col_1 > 5' (see Pandas documentation)",
)
def filter_metannots(filter_expr: str | None) -> None:
    datasets = get_datasets(DATASETS_FOLDER)

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
                print(f"Validation warnings: {e}")

                metannots_dict = get_metannots_dict(
                    DATASETS_FOLDER, dataset["name"], gold_std_set
                )

                if metannots_dict is None:
                    continue

            metannots_dict["set"] = gold_std_set
            metannots_dict["dataset"] = dataset["name"]

            metannots_list.append(metannots_dict)

    df = pd.DataFrame(metannots_list)

    if filter_expr is not None:
        try:
            df = df.query(filter_expr)
        except Exception as e:
            print(
                f"ERROR: problem using the filter expression on \
metannots dataframe: {e}"
            )
            print("INFO: Using no filter at all...")

    print(
        f"INFO: Printing datasets and sets matching \
filter expression '{filter_expr}'..."
    )
    for _, row in df.iterrows():
        print(f"Dataset: '{row["dataset"]}'       Set: '{row["set"]}'")

    return


def get_metannots_df() -> None:
    pass


if __name__ == "__main__":
    filter_metannots()
