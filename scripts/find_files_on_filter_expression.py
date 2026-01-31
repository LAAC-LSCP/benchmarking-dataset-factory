"""
This script creates a dataframe of files
matching a filter expression on (1) children metadata and (2) metannots

This dataframe can be used for later train/test/validation splitting of the data

For more information on filter expressions, visit the Pandas documentation
"""

from pathlib import Path
from typing import Annotated, Dict, List, Set, Tuple

import click
import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject

from .src.data.get_metannots_df import get_metannots_df
from .src.utils.constants import DATASETS, DATASETS_FOLDER
from .src.utils.logger import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--dataset",
    "-d",
    multiple=True,
    help="datasets. If not specified, will use all datasets",
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
like 'child_sex == 'F'' (see Pandas + \
ChildProject docs)",
)
@click.option(
    "--output-csv",
    required=True,
    type=click.Path(exists=False),
    help="Output .csv path",
)
def find_files_and_save(
    dataset: Tuple[str],
    metannots_filter_expr: str | None,
    children_filter_expr: str | None,
    output_csv: Path,
) -> None:
    """Save file paths matching filter expressions on metannots \
and children metadata (specified separately)"""
    file_infos = find_files(dataset, metannots_filter_expr, children_filter_expr)[0]

    save_file_paths(file_infos, output_csv)

    return


def find_files(
    dataset: Tuple[str],
    metannots_filter_expr: str | None,
    children_filter_expr: str | None,
) -> Tuple[
    Annotated[pd.DataFrame, "file csv"],
    Annotated[pd.DataFrame, "children"],
    Annotated[pd.DataFrame, "recordings"],
    Annotated[pd.DataFrame, "annotations"],
]:
    datasets: Set[str] = {d for d in dataset}

    if len(datasets) == 0:
        datasets = DATASETS

    metannots_df: pd.DataFrame = get_metannots_df(
        print_errors=False, dataset_names=(datasets if len(datasets) else None)
    )
    children_df = get_children_df(datasets)
    recordings_df = get_recordings_df(datasets)
    annotations_df = get_annotations_df(datasets)

    if metannots_filter_expr is not None:
        try:
            metannots_df = metannots_df.query(metannots_filter_expr)
        except Exception as e:
            logger.exception(f"problem using the filter expression on \
metannots dataframe: {e}")
            logger.info("using no filter at all...")

            metannots_filter_expr = ""

    if children_filter_expr is not None:
        try:
            children_df = children_df.query(children_filter_expr)
        except Exception as e:
            logger.exception(f"problem using the filter expression on \
children dataframe: {e}")
            logger.info("using no filter at all...")

            children_filter_expr = ""

    file_infos = get_file_infos(children_df, metannots_df)
    filtered_children = get_children_from_files(file_infos, children_df)
    filtered_recordings = get_recordings_from_files(file_infos, recordings_df)
    filtered_annotations = get_annotations_from_files(file_infos, annotations_df)

    return file_infos, filtered_children, filtered_recordings, filtered_annotations


def save_file_paths(file_paths: pd.DataFrame, output_path: Path) -> None:
    file_paths.to_csv(output_path, index=False)


def get_children_df(datasets: Set[str]) -> pd.DataFrame:
    children_df_list: List[pd.DataFrame] = []

    for dataset in [d for d in DATASETS_FOLDER.iterdir() if d.is_dir()]:
        project = ChildProject(dataset)
        project.read()

        children_df = project.children

        if "discard" in children_df.columns:
            children_df = children_df[children_df["discard"] != "1"]
        children_df["dataset"] = dataset.name

        children_df_list.append(children_df)

    children_df = pd.concat(children_df_list)

    return children_df[children_df["dataset"].isin(datasets)]


def get_recordings_df(datasets: Set[str]) -> pd.DataFrame:
    recordings_df_list: List[pd.DataFrame] = []

    for dataset in [d for d in DATASETS_FOLDER.iterdir() if d.is_dir()]:
        project = ChildProject(dataset)
        project.read()

        recordings_df = project.recordings

        if "discard" in recordings_df.columns:
            recordings_df = recordings_df[recordings_df["discard"] != "1"]
        recordings_df["dataset"] = dataset.name

        recordings_df_list.append(recordings_df)

    recordings_df = pd.concat(recordings_df_list)

    return recordings_df[recordings_df["dataset"].isin(datasets)]


def get_annotations_df(datasets: Set[str]) -> pd.DataFrame:
    # NOTE: I'm deliberately avoiding using annotation manager (it's slow)
    annotations_df_list: List[pd.DataFrame] = []

    for dataset in [d for d in DATASETS_FOLDER.iterdir() if d.is_dir()]:
        annotations_df = pd.read_csv(dataset / "metadata" / "annotations.csv")

        annotations_df["dataset"] = dataset.name

        annotations_df_list.append(annotations_df)

    annotations_df = pd.concat(annotations_df_list)

    return annotations_df[annotations_df["dataset"].isin(datasets)]


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
                "recording path": (
                    project.path
                    / "recordings"
                    / "converted"
                    / "standard"
                    / row["recording_filename"]
                ).with_suffix(
                    ".wav"
                ),  # checked that this is always there :)
                "recording path raw": project.get_recording_path(
                    row["recording_filename"]
                ),
                "dataset": dataset,
                "set": row["set"],
                "annotation start (ms)": start,
                "annotation end (ms)": end,
                "annotation duration (ms)": duration,
                "recording duration (ms)": row["duration"],
                "format": row["format"],
                "child_id": row["child_id"],
                "annotation_filename": row["annotation_filename"],
                "recording_filename": row["recording_filename"],
            }
        )

    return pd.DataFrame(file_infos)


def get_children_from_files(
    file_infos: pd.DataFrame, original_children_df: pd.DataFrame
) -> pd.DataFrame:
    children = original_children_df.copy()
    children = children.merge(
        file_infos[["child_id", "dataset"]].drop_duplicates(),
        on=["child_id", "dataset"],
        how="inner",
    )

    children["child_id"] = (
        children["dataset"].astype(str) + "_" + children["child_id"].astype(str)
    )

    children = children.loc[:, ~children.isna().all()]
    children = children.drop("dataset", axis=1)

    return children


def get_recordings_from_files(
    file_infos: pd.DataFrame, original_recordings_df: pd.DataFrame
) -> pd.DataFrame:
    recordings = original_recordings_df.copy()
    recordings = recordings.merge(
        file_infos[["recording_filename", "dataset"]].drop_duplicates(),
        on=["recording_filename", "dataset"],
        how="inner",
    )

    recordings["child_id"] = (
        recordings["dataset"].astype(str) + "_" + recordings["child_id"].astype(str)
    )

    recordings = recordings.loc[:, ~recordings.isna().all()]

    filename_cols = [col for col in recordings.columns if col.endswith("_filename")]
    for col in filename_cols:
        recordings[col] = (
            recordings["dataset"].astype(str) + "/" + recordings[col].astype(str)
        )

    recordings = recordings.drop("dataset", axis=1)

    return recordings


def get_annotations_from_files(
    file_infos: pd.DataFrame, original_annotations_df: pd.DataFrame
) -> pd.DataFrame:
    annotations = original_annotations_df.copy()
    annotations = annotations.merge(
        file_infos[["annotation_filename", "dataset"]].drop_duplicates(),
        on=["annotation_filename", "dataset"],
        how="inner",
    )

    annotations["set"] = annotations["dataset"] + "/" + annotations["set"].astype(str)
    annotations["recording_filename"] = (
        annotations["dataset"] + "/" + annotations["recording_filename"].astype(str)
    )

    annotations = annotations.loc[:, ~annotations.isna().all()]

    annotations = annotations.drop("dataset", axis=1)

    return annotations


def get_annotation_duration(annotation_filename: str) -> Tuple[int, int, int]:
    parts = annotation_filename.split("_")

    start = int(parts[-2])
    end = int(parts[-1].rstrip(".csv"))

    return start, end, end - start


def get_path_of_annotation_file(dataset: str, set_name: str, filename: str) -> Path:
    return DATASETS_FOLDER / dataset / "annotations" / set_name / "converted" / filename


if __name__ == "__main__":
    find_files_and_save()
