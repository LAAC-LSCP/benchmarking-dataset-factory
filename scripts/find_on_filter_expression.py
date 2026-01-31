"""
This script aggregates the metannots files into a csv
file, making it easy to apply filter expressions

To see the list of columns, look under `metannots.py`, or in the
ChildProject documentation
"""

import click
import pandas as pd

from .src.data.get_metannots_df import get_metannots_df
from .src.utils.logger import get_logger

logger = get_logger(__name__)


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
                logger.exception(f"problem using the filter expression on \
metannots dataframe: {e}")
                logger.info("Using no filter at all...")

            filter_expr = ""

    if not no_info_output:
        logger.info(f"Printing datasets and sets matching \
filter expression '{filter_expr}'...")
    for _, row in df.iterrows():
        logger.info(f"Dataset: '{row["dataset"]}'       Set: '{row["set"]}'")

    return df


if __name__ == "__main__":
    filter_metannots()
