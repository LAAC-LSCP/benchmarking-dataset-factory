"""
Small script for getting children metadata for the interspeech submission

Gets the dataset, child_id, age, normative/non-normative, normative criterion
Discard children with `discard==1`
"""

from pathlib import Path
from typing import List, TypedDict

import click
import pandas as pd
from ChildProject.projects import ChildProject

from scripts.src.utils.constants import DATASETS_FOLDER
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetInfo(TypedDict):
    dataset: str
    min_age_months: float
    max_age_months: float
    languages: float
    monolingual: int
    multilingual: int
    normative: int
    non_normative: int
    male: int
    female: int


@click.command()
@click.option(
    "--output-path",
    type=click.Path(),
    help="Output path of dataframe",
)
def get_children_metadata_table(output_path: str):
    datasets_folder = DATASETS_FOLDER

    children_dfs: List[pd.DataFrame] = []
    dataset_summary_dfs: List[DatasetInfo] = []

    for dataset in datasets_folder.iterdir():
        logger.info(f"Processing dataset {dataset.name}")
        if not dataset.is_dir():
            continue

        project = ChildProject(dataset)
        project.read()

        dict_summary = project.dict_summary()["children"]

        dataset_summary_dfs.append(
            {
                "dataset": dataset.name,
                "min_age_months": dict_summary["min_age"],
                "max_age_months": dict_summary["max_age"],
                "languages": dict_summary["languages"],
                "monolingual": dict_summary["monolingual"],
                "multilingual": dict_summary["multilingual"],
                "normative": dict_summary["normative"],
                "non_normative": dict_summary["non-normative"],
                "male": dict_summary["M"],
                "female": dict_summary["F"],
            }
        )

        children: pd.DataFrame = project.children

        keep_cols: List[str] = [
            "child_id",
            "child_sex",
            "normative",
            "normative_criterion",
            "dob_criterion",
            "dob_accuracy",
            "discard",
        ]
        keep_cols = [col for col in keep_cols if col in children.columns]

        children = children[keep_cols]
        if "discard" in children.columns:
            children = children[children["discard"] != 1]

        ages: pd.Series = project.compute_ages().round(2)
        children["age (months)"] = ages

        if "discard" in children.columns:
            children = children.drop("discard", axis=1)

        children["dataset"] = dataset.name

        children_dfs.append(children)
        logger.info(f"Completed processing {dataset.name}")

    output_as_path = Path(output_path)

    logger.info(f"Saving to {output_as_path!s}...")
    pd.concat(children_dfs).to_csv(output_as_path, index=True)
    logger.info("Done.")

    summary_path = output_as_path.with_stem(output_as_path.stem + "_datasets_summary")
    logger.info(f"Saving to {summary_path!s}...")
    pd.DataFrame(dataset_summary_dfs).to_csv(summary_path, index=True)
    logger.info("Done.")

    return


if __name__ == "__main__":
    get_children_metadata_table()
