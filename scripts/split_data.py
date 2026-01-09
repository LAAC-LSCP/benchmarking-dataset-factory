"""
This script creates a train, test, validation split
based on the output of find_files_on_filter_expression.py

It takes into account file durations and can, if specified, split
fairly across recordings for the same child

We stratify as follows: do the train/test/validation split for a child
Then combine all the splits
"""

from pathlib import Path
from typing import List, Tuple

import click
import pandas as pd


@click.command()
@click.option(
    "--input",
    required=True,
    type=click.Path(exists=True),
    help="Input file (output from `find_files_on_filter_expression.py`)",
)
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
def split_data(
    input: Path,
    train: float,
    test: float,
    validate: float,
    output_csv: Path,
    same_child: bool,
    stratify_set: bool,
    seed: int,
) -> None:
    """
    Splits the output of `find_files_on_filter_expression.py` based on
    a specified train, test, validation split
    """
    validate_inputs(train, test, validate)

    file_infos: pd.DataFrame = pd.read_csv(input)

    groups = ["dataset", "set"]
    if not stratify_set:
        groups.remove("set")
    grouped = file_infos.groupby(groups)

    file_infos_with_splits: List[pd.DataFrame] = []
    for _, group in grouped:
        tr, te, va = train_test_split(group, train, test, validate, seed)
        file_infos_with_splits.append(tr)
        file_infos_with_splits.append(te)
        file_infos_with_splits.append(va)

    file_infos_with_split = pd.concat(file_infos_with_splits)
    file_infos_with_split = file_infos_with_split.drop("cum_duration", axis=1)

    tot_duration = file_infos["annotation duration (ms)"].sum()

    if same_child:
        file_infos_with_split = reassign_split_by_child(file_infos_with_split, train, test, validate, seed)

    train_set = set(
        tuple(x) for x in file_infos_with_split[file_infos_with_split["split"] == "train"][["child_id", "dataset"]].to_records(index=False)
    )
    test_set = set(
        tuple(x) for x in file_infos_with_split[file_infos_with_split["split"] == "test"][["child_id", "dataset"]].to_records(index=False)
    )
    validate_set = set(
        tuple(x) for x in file_infos_with_split[file_infos_with_split["split"] == "validate"][["child_id", "dataset"]].to_records(index=False)
    )

    assert not train_set & test_set
    assert not train_set & validate_set
    assert not test_set & validate_set

    print_info(file_infos_with_split, tot_duration, train, test, validate)
    save_file(file_infos_with_split, output_csv)

    return


def get_dur_split(file_infos: pd.DataFrame, split: str) -> float:
    return file_infos[file_infos["split"] == split]["annotation duration (ms)"].sum()


def print_info(
    file_infos_with_split: pd.DataFrame,
    tot_duration: float,
    train: float,
    test: float,
    validate: float,
) -> None:
    print("Found split!")
    print(f"Desired train, test, validation split (ms): \
{int(get_dur(tot_duration, train))}, \
{int(get_dur(tot_duration, test))}, \
{int(get_dur(tot_duration, validate))}")
    print(f"Found train, test, validation split (ms): \
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


def reassign_split_by_child(file_infos_with_splits: pd.DataFrame, train: float, test: float, validate: float, seed: int):
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
        split = max(gaps, key=gaps.get)
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
