"""
This script aggregates the metannots files into a csv
file, making it easy to apply filter expressions

To see the list of columns, look under `metannots.py`, or in the
ChildProject documentation
"""

from typing import Dict, List, Optional

import click
import pandas as pd
from custom_types.datasets_json import get_datasets
from custom_types.metannots import get_metannots, get_metannots_dict
from helpers.constants import DATASETS_FOLDER
from pydantic import ValidationError


@click.command()
@click.option(
    "--filter-expr",
    required=False,
    default=None,
    help="Filter expression like 'has_addressee == 'Y'' \
(see Pandas + ChildProject docs)",
)
@click.option(
    "--no-info-output",
    is_flag=True,
    help="Don't print info, such as error info. Only print datasets and sets",
)
def filter_metannots(filter_expr: str | None, no_info_output: bool) -> pd.DataFrame:
    """Find datasets and sets matching a filter expression on the metannots metadata"""
    df = get_metannots_df(print_errors=(not no_info_output))

    if filter_expr is not None:
        try:
            df = df.query(filter_expr)
        except Exception as e:
            if not no_info_output:
                print(
                    f"ERROR: problem using the filter expression on \
metannots dataframe: {e}"
                )
                print("INFO: Using no filter at all...")

            filter_expr = ""

    if not no_info_output:
        print(
            f"INFO: Printing datasets and sets matching \
filter expression '{filter_expr}'..."
        )
    for _, row in df.iterrows():
        print(f"Dataset: '{row["dataset"]}'       Set: '{row["set"]}'")

    return df


def get_metannots_df(print_errors: bool = False) -> pd.DataFrame:
    datasets = get_datasets(DATASETS_FOLDER, print_info=print_errors)

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
                    print(f"Validation warnings: {e}")

                metannots_dict = get_metannots_dict(
                    DATASETS_FOLDER, dataset["name"], gold_std_set
                )

                if metannots_dict is None:
                    continue

            metannots_dict["set"] = gold_std_set
            metannots_dict["dataset"] = dataset["name"]

            metannots_list.append(metannots_dict)

    return pd.DataFrame(metannots_list)


if __name__ == "__main__":
    filter_metannots()
