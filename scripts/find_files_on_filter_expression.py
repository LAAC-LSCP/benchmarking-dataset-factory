"""
This script prints out a list of human annotation file paths
matching a filter expression on (1) children metadata and (2) metannots

For more information on filter expressions, visit the Pandas documentation


"""

from pathlib import Path
from typing import List

import click
import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject
from helpers.constants import DATASETS_FOLDER

from find_on_filter_expression import get_metannots_df


@click.command()
@click.option(
    "--metannots-filter-expr",
    required=False,
    default=None,
    help="Filter expression on metannots \
like 'has_addressee == 'Y'' (see Pandas + \
ChildProject docs)",
)
@click.option(
    "--children-filter-expr",
    required=False,
    default=None,
    help="Filter expression on children metadata \
like 'child_sex == 'f'' (see Pandas + \
ChildProject docs)",
)
@click.option(
    "--no-info-output",
    is_flag=True,
    help="Don't print info, such as error info. Only print file paths",
)
def find_files(
    metannots_filter_expr: str | None,
    children_filter_expr: str | None,
    no_info_output: bool,
) -> List[Path]:
    """Prints file paths matching filter expressions on metannots \
and children metadata (specified separately)"""
    metannots_df: pd.DataFrame = get_metannots_df(print_errors=False)
    children_df = get_children_df()

    if metannots_filter_expr is not None:
        try:
            metannots_df = metannots_df.query(metannots_filter_expr)
        except Exception as e:
            if not no_info_output:
                print(
                    f"ERROR: problem using the filter expression on \
metannots dataframe: {e}"
                )
                print("INFO: Using no filter at all...")

            metannots_filter_expr = ""

    if children_filter_expr is not None:
        try:
            children_df = children_df.query(children_filter_expr)
        except Exception as e:
            if not no_info_output:
                print(
                    f"ERROR: problem using the filter expression on \
children dataframe: {e}"
                )
                print("INFO: Using no filter at all...")

            children_filter_expr = ""

    file_paths = get_file_paths(children_df, metannots_df)

    for file_path in file_paths:
        print(str(file_path))

    return file_paths


def get_children_df() -> pd.DataFrame:
    children_df_list: List[pd.DataFrame] = []

    for dataset in [d for d in DATASETS_FOLDER.iterdir() if d.is_dir()]:
        project = ChildProject(dataset)
        project.read()

        children_df = project.children

        if "discard" in children_df.columns:
            children_df = children_df[children_df["discard"] != "1"]
        children_df["dataset"] = dataset.name

        children_df_list.append(children_df)

    return pd.concat(children_df_list)


def get_file_paths(children_df: pd.DataFrame, metannots_df: pd.DataFrame) -> List[Path]:
    file_paths: List[Path] = []

    for _, metannot in metannots_df.iterrows():
        gold_std_set: str = metannot["set"]
        dataset: str = metannot["dataset"]

        file_paths += get_file_paths_for_set_dataset(gold_std_set, dataset, children_df)

    return file_paths


def get_file_paths_for_set_dataset(
    set_name: str, dataset: str, children_df: pd.DataFrame
) -> List[Path]:
    file_paths: List[Path] = []

    project = ChildProject(DATASETS_FOLDER / dataset)
    am: AnnotationManager = AnnotationManager(project)

    recordings: pd.DataFrame = project.recordings
    recordings = recordings[["recording_filename", "child_id", "discard"]]

    if "discard" in recordings.columns:
        recordings = recordings.rename(columns={"discard": "discard_recording"})

    annotations: pd.DataFrame = am.annotations
    annotations = annotations[annotations["set"] == set_name]

    annotations_w_child_id = annotations.merge(
        recordings, on="recording_filename", how="left"
    )
    annotations_w_child_id = annotations_w_child_id[
        annotations_w_child_id["discard_recording"] != "1"
    ]

    valid_child_ids = children_df[children_df["dataset"] == dataset]["child_id"]
    annotations_w_child_id = annotations_w_child_id[
        annotations_w_child_id["child_id"].isin(valid_child_ids)
    ]

    for _, row in annotations_w_child_id.iterrows():
        file_paths.append(
            get_path_of_annotation_file(dataset, set_name, row["annotation_filename"])
        )

    return file_paths


def get_path_of_annotation_file(dataset: str, set_name: str, filename: str) -> Path:
    return DATASETS_FOLDER / dataset / "annotations" / set_name / "converted" / filename


if __name__ == "__main__":
    find_files()
