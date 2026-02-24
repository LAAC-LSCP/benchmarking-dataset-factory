"""
This script creates a train, test, validation split
based on the output of find_files_on_filter_expression.py

It takes into account file durations and can, if specified, split
fairly across recordings for the same child

We stratify as follows: do the train/test/validation split for a child
Then combine all the splits

TODO: preferably accumulate not by the length of the annotation file, but
by length total of relevant segments that have been annotated

...for this to work we need both the `manually_annotated_data.json` from the benchmarking
dataset as well as the smaller dataset-only .json files that give the lengths of annotated
data for each column. It is a bit of work to copy all of that over and wire it up,
so for now it's good enough that asymptotically, in the number of annotation files,
you will land on the same split you would get with the better method
"""

from pathlib import Path
from typing import List, Tuple

import click
import pandas as pd


from scripts.create_dataset import filter_on_manual_data, fix_columns_for_combined_dfs, get_file_paths
from scripts.src.custom_types import DatasetType
from scripts.src.human_annotation_metadata.schema_manual_metadata import dataset_model_factory
from scripts.src.metadata import get_generated_metadata, get_manual_metadata
from scripts.src.utils.logger import get_logger

SCRIPTS_FOLDER: Path = Path(__file__).parent


assert SCRIPTS_FOLDER.exists()


logger = get_logger(__name__)


@click.command()
@click.option(
    "--train",
    required=True,
    type=float,
    help="Train percentage in [0, 1]",
)
@click.option(
    "--test",
    required=True,
    type=float,
    help="Test percentage in [0, 1]",
)
@click.option(
    "--validate",
    required=True,
    type=float,
    help="Validation percentage in [0, 1]",
)
@click.option(
    "--output-csv",
    required=True,
    type=click.Path(exists=False),
    help="Output .csv path",
)
@click.option(
    "--same-child",
    is_flag=True,
    help="Assure same child doesn't cross train/test/validation boundary",
)
@click.option(
    "--stratify-set",
    is_flag=True,
    help="Stratify by set",
)
@click.option(
    "--seed",
    required=False,
    type=int,
    default=0,
    help="Random seed for split",
)
@click.option(
    "--dataset-type",
    type=click.Choice([t.value for t in DatasetType]),
    required=True,
    help="Type of dataset to create",
)
@click.option(
    "--datasets-folder",
    required=True,
    type=click.Path(exists=True),
    default=None,
    help="Folder with available datasets",
)
def split_data(
    train: float,
    test: float,
    validate: float,
    output_csv: Path,
    same_child: bool,
    stratify_set: bool,
    seed: int,
    dataset_type: str,
    datasets_folder: str,
) -> None:
    """
    Splits the output of `find_files_on_filter_expression.py` based on
    a specified train, test, validation split
    """
    file_infos, children_df, recordings_df, annotations_df = get_file_paths(
        datasets=tuple(),
        children_filter_expr=None,
        datasets_dir=Path(datasets_folder),
    )

    generated_data = get_generated_metadata()
    manual_data = dataset_model_factory(generated_data, skip_validation=True)(**get_manual_metadata())
    file_infos, children_df, recordings_df, annotations_df = filter_on_manual_data(
        file_infos,
        children_df,
        recordings_df,
        annotations_df,
        manual_data,
        DatasetType(dataset_type),
    )

    if len(annotations_df) == 0:
        logger.info("Matched annotations empty. Exiting")

        return

    validate_inputs(train, test, validate)

    annotation_infos = get_file_infos(children_df, recordings_df, annotations_df)

    groups = ["dataset", "set"]
    if not stratify_set:
        groups.remove("set")
    grouped = annotation_infos.groupby(groups)

    file_infos_with_splits: List[pd.DataFrame] = []
    for _, group in grouped:
        tr, te, va = train_test_split(group, train, test, validate, seed)
        file_infos_with_splits.append(tr)
        file_infos_with_splits.append(te)
        file_infos_with_splits.append(va)

    file_infos_with_split = pd.concat(file_infos_with_splits)
    file_infos_with_split = file_infos_with_split.drop("cum_duration", axis=1)

    tot_duration = annotation_infos["annotation duration (ms)"].sum()

    if same_child:
        file_infos_with_split = reassign_split_by_child(
            file_infos_with_split, train, test, validate, seed
        )

    train_set = set(
        tuple(x)
        for x in file_infos_with_split[file_infos_with_split["split"] == "train"][
            ["child_id", "dataset"]
        ].to_records(index=False)
    )
    test_set = set(
        tuple(x)
        for x in file_infos_with_split[file_infos_with_split["split"] == "test"][
            ["child_id", "dataset"]
        ].to_records(index=False)
    )
    validate_set = set(
        tuple(x)
        for x in file_infos_with_split[file_infos_with_split["split"] == "validate"][
            ["child_id", "dataset"]
        ].to_records(index=False)
    )

    assert not train_set & test_set
    assert not train_set & validate_set
    assert not test_set & validate_set

    file_infos_with_split = file_infos_with_split.drop("age (months)", axis=1)
    file_infos_with_split = file_infos_with_split.drop_duplicates()
    file_infos_with_split["full recording path"] = file_infos_with_split["full recording path"].apply(lambda x: str(Path(x).with_suffix(".wav")))

    print_info(file_infos_with_split, tot_duration, train, test, validate)
    save_file(file_infos_with_split, output_csv)

    return


def get_file_infos(children: pd.DataFrame, recordings: pd.DataFrame, annotations: pd.DataFrame) -> pd.DataFrame:
    result = annotations.merge(
        recordings[["recording_filename", "child_id"]],
        on="recording_filename",
        how="left",
    )

    result = result.merge(
        children[["child_id", "age (months)"]], on="child_id", how="left"
    )

    result["annotation duration (ms)"] = result["range_offset"] - result["range_onset"]
    result["full annotation path"] = result.apply(
        lambda row: str(get_full_annotation_path(row)), axis=1
    )
    result["full recording path"] = result.apply(
        lambda row: str(get_full_recording_path(row)), axis=1
    )

    return result[
        [
            "dataset",
            "set",
            "child_id",
            "age (months)",
            "time_seek",
            "range_onset",
            "range_offset",
            "annotation duration (ms)",
            "full annotation path",
            "full recording path",
        ]
    ]


def get_full_annotation_path(row: pd.Series) -> Path:
    return (
        Path("/scratch1/data/laac_data/datasets")
        / row["dataset"]
        / "annotations"
        / row["set"]
        / "converted"
        / row["annotation_filename"]
    )


def get_full_recording_path(row: pd.Series) -> Path:
    return (
        Path("/scratch1/data/laac_data/datasets")
        / row["dataset"]
        / "recordings"
        / "converted"
        / "standard"
        / row["recording_filename"]
    )


def get_dur_split(file_infos: pd.DataFrame, split: str) -> float:
    return file_infos[file_infos["split"] == split]["annotation duration (ms)"].sum()


def print_info(
    file_infos_with_split: pd.DataFrame,
    tot_duration: float,
    train: float,
    test: float,
    validate: float,
) -> None:
    logger.info("Found split!")
    logger.info(f"Desired train, test, validation split (ms): \
{int(get_dur(tot_duration, train))}, \
{int(get_dur(tot_duration, test))}, \
{int(get_dur(tot_duration, validate))}")
    logger.info(f"Found train, test, validation split (ms): \
{int(get_dur_split(file_infos_with_split, "train"))}, \
{int(get_dur_split(file_infos_with_split, "test"))}, \
{int(get_dur_split(file_infos_with_split, "validate"))}")


def save_file(df: pd.DataFrame, output_csv: Path) -> None:
    df.to_csv(output_csv, index=False)


# Would use sklearn but they don't do weights
def train_test_split(
    df: pd.DataFrame,
    train: float,
    test: float,
    validate: float,
    seed: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    shuffled_df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    shuffled_df["cum_duration"] = shuffled_df["annotation duration (ms)"].cumsum()
    tot_dur = shuffled_df["cum_duration"].iloc[-1]

    train_df = shuffled_df[
        shuffled_df["cum_duration"] <= get_dur(tot_dur, train)
    ].copy()
    train_df["split"] = "train"

    test_df = shuffled_df[
        (shuffled_df["cum_duration"] > get_dur(tot_dur, train))
        & (shuffled_df["cum_duration"] <= get_dur(tot_dur, train + test))
    ].copy()
    test_df["split"] = "test"

    validate_df = shuffled_df[
        (shuffled_df["cum_duration"] > get_dur(tot_dur, train + test))
        & (shuffled_df["cum_duration"] <= get_dur(tot_dur, train + test + validate))
    ].copy()
    validate_df["split"] = "validate"

    return train_df, test_df, validate_df


def reassign_split_by_child(
    file_infos_with_splits: pd.DataFrame,
    train: float,
    test: float,
    validate: float,
    seed: int,
):
    group_cols = ["child_id", "dataset"]
    groups = list(file_infos_with_splits.groupby(group_cols))
    rng = pd.Series(range(len(groups))).sample(frac=1, random_state=seed).tolist()
    groups = [groups[i] for i in rng]

    total_duration = file_infos_with_splits["annotation duration (ms)"].sum()
    targets = {
        "train": train * total_duration,
        "test": test * total_duration,
        "validate": validate * total_duration,
    }
    current = {"train": 0, "test": 0, "validate": 0}
    assignments = []

    for _, group in groups:
        gaps = {k: targets[k] - current[k] for k in targets}
        split = max(gaps, key=gaps.get)  # type: ignore
        group = group.copy()
        group["split"] = split
        current[split] += group["annotation duration (ms)"].sum()
        assignments.append(group)

    return pd.concat(assignments)


def validate_inputs(train: float, test: float, validate: float) -> None:
    if train < 0 or train > 1:
        raise ValueError("`train` should be in range [0, 1]")

    if test < 0 or test > 1:
        raise ValueError("`test` should be in range [0, 1]")

    if validate < 0 or validate > 1:
        raise ValueError("`validate` should be in range [0, 1]")

    if train + test + validate != 1.0:
        raise ValueError("train, test, validation split does not add to 1")

    return


def get_dur(total_duration: float, fraction: float) -> float:
    return total_duration * fraction


if __name__ == "__main__":
    split_data()
