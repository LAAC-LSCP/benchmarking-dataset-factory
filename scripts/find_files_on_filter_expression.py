"""
This script creates a dataframe of files
matching a filter expression on (1) children metadata and (2) metannots

This dataframe can be used for later train/test/validation splitting of the data

For more information on filter expressions, visit the Pandas documentation
"""

from pathlib import Path
from typing import Dict, List, Tuple

import click
import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject
from find_on_filter_expression import get_metannots_df
from helpers.constants import DATASETS_FOLDER


@click.command()
@click.option(
    "--dataset",
    "-d",
    multiple=True,
    help="datasets to graph. If not specified, will use all datasets",
)
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
    "--output-csv",
    required=True,
    type=click.Path(exists=False),
    help="Output .csv path",
)
def find_files(
    dataset: Tuple[str],
    metannots_filter_expr: str | None,
    children_filter_expr: str | None,
    output_csv: Path,
) -> pd.DataFrame:
    """Save file paths matching filter expressions on metannots \
and children metadata (specified separately)"""
    datasets: List[str] = [d for d in dataset]

    metannots_df: pd.DataFrame = get_metannots_df(
        print_errors=False, dataset_names=(datasets if len(datasets) else None)
    )
    children_df = get_children_df()

    if metannots_filter_expr is not None:
        try:
            metannots_df = metannots_df.query(metannots_filter_expr)
        except Exception as e:
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
            print(
                f"ERROR: problem using the filter expression on \
children dataframe: {e}"
            )
            print("INFO: Using no filter at all...")

            children_filter_expr = ""

    file_infos = get_file_infos(children_df, metannots_df)

    save_file_paths(file_infos, output_csv)

    return file_infos


def save_file_paths(file_paths: pd.DataFrame, output_path: Path) -> None:
    file_paths.to_csv(output_path, index=False)


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


def get_file_infos(
    children_df: pd.DataFrame, metannots_df: pd.DataFrame
) -> pd.DataFrame:
    file_infos: List[pd.DataFrame] = []

    for _, metannot in metannots_df.iterrows():
        gold_std_set: str = metannot["set"]
        dataset: str = metannot["dataset"]

        file_infos.append(
            get_file_paths_for_set_dataset(gold_std_set, dataset, children_df)
        )

    return pd.concat(file_infos, axis=0)


def get_file_paths_for_set_dataset(
    set_name: str, dataset: str, children_df: pd.DataFrame
) -> pd.DataFrame:
    file_infos: List[Dict] = []

    project = ChildProject(DATASETS_FOLDER / dataset)
    am: AnnotationManager = AnnotationManager(project)

    recordings: pd.DataFrame = project.recordings
    recordings = recordings.reindex(
        columns=["recording_filename", "child_id", "discard", "duration"]
    )

    if "discard" in recordings.columns:
        recordings = recordings[recordings["discard"] != "1"]

    annotations: pd.DataFrame = am.annotations
    annotations = annotations[annotations["set"] == set_name]

    annotations_w_child_id = annotations.merge(
        recordings, on="recording_filename", how="left"
    )

    valid_child_ids = children_df[children_df["dataset"] == dataset]["child_id"]
    annotations_w_child_id = annotations_w_child_id[
        annotations_w_child_id["child_id"].isin(valid_child_ids)
    ]

    for _, row in annotations_w_child_id.iterrows():
        start, end, duration = get_annotation_duration(row["annotation_filename"])

        file_infos.append(
            {
                "annotation path": get_path_of_annotation_file(
                    dataset, set_name, row["annotation_filename"]
                ),
                "recording path": project.get_recording_path(row["recording_filename"]),
                "dataset": dataset,
                "set": row["set"],
                "annotation start (ms)": start,
                "annotation end (ms)": end,
                "annotation duration (ms)": duration,
                "recording duration (ms)": row["duration"],
                "format": row["format"],
                "child_id": row["child_id"],
            }
        )

    return pd.DataFrame(file_infos)


def get_annotation_duration(annotation_filename: str) -> Tuple[int, int, int]:
    parts = annotation_filename.split("_")

    start = int(parts[-2])
    end = int(parts[-1].rstrip(".csv"))

    return start, end, end - start


def get_path_of_annotation_file(dataset: str, set_name: str, filename: str) -> Path:
    return DATASETS_FOLDER / dataset / "annotations" / set_name / "converted" / filename


if __name__ == "__main__":
    find_files()
