"""
Generic script that lets you graph certain properties of datasets
"""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, List, Set, Tuple

import click
import matplotlib.pyplot as plt
import pandas as pd
from ChildProject.annotations import AnnotationManager
from ChildProject.projects import ChildProject
from helpers.constants import DATASETS_FOLDER


class XValue(StrEnum):
    CHILD_ID = "child_id"
    CHILD_AGE = "child_age"
    CHILD_SEX = "child_sex"
    SPEAKER_TYPE = "speaker_type"
    SPEAKER_ID = "speaker_id"


class YValue(StrEnum):
    SEGMENT = "segment"
    RECORDING = "recording"


class MetricValue(StrEnum):
    DURATION_MEAN = "duration_mean"
    DURATION_TOTAL = "duration_total"
    DURATION_STD = "duration_std"
    COUNT = "count"


CHILD_PROPS: List[XValue] = [XValue.CHILD_ID, XValue.CHILD_AGE, XValue.CHILD_SEX]
SEGMENT_PROPS: List[XValue] = [XValue.SPEAKER_TYPE, XValue.SPEAKER_ID]


@click.command()
@click.option(
    "--dataset",
    "-d",
    multiple=True,
    help="datasets to graph. If not specified, will use all datasets",
)
@click.option(
    "--x-axis",
    "-x",
    required=True,
    type=click.Choice(
        ["child_id", "child_age", "child_sex", "speaker_type", "speaker_id"]
    ),
    help="x-axis",
)
@click.option(
    "--y-axis",
    "-y",
    required=True,
    type=click.Choice(["segment", "recording"]),
    help="y-axis",
)
@click.option(
    "--metric",
    required=True,
    type=click.Choice(["duration_mean", "count", "duration_std", "duration_total"]),
    help="function to run over aggregated data",
)
@click.option("--sort-by-y", is_flag=True, help="Sort data by y (instead of x) axis")
@click.option(
    "--output-folder",
    required=False,
    type=click.Path(exists=False),
    help="path of output folder",
)
def graph(
    dataset: Tuple[str],
    x_axis: XValue,
    y_axis: YValue,
    metric: MetricValue,
    sort_by_y: bool,
    output_folder: Path | None,
) -> List[Tuple[pd.Series, Annotated[str, "dataset"]]]:
    """Lets you graph distributional info of metadata over a dataset

    If looking at segments, will choose information only from human-annotated sets
    If looking at recordings in general, will choose all recording information
    regardless of which sets"""

    validate(x_axis, y_axis)

    datasets: Set[str] = {d for d in dataset}
    datas: List[Tuple[pd.Series, Annotated[str, "dataset"]]] = []

    use_ms = y_axis == YValue.SEGMENT and metric in [
        MetricValue.DURATION_MEAN,
        MetricValue.DURATION_STD,
    ]

    for d in datasets:
        dataset_dir = DATASETS_FOLDER / d
        data = get_data(dataset_dir, x_axis, y_axis, metric, use_ms)

        if sort_by_y:
            data = data.sort_values(ascending=False)
        else:
            data = data.sort_index()

        if data.index.dtype == "float64":
            data.index = data.index.round(1)  # type: ignore

        data.index = data.index.fillna("N/A")

        datas.append((data, d))

    datas = sorted(datas, key=lambda x: x[1])

    graph_data(datas, x_axis, y_axis, metric, use_ms)

    if output_folder is not None:
        save_data(datas, x_axis, y_axis, metric, output_folder)

    return datas


def graph_data(
    datas: List[Tuple[pd.Series, str]],
    x_axis: XValue,
    y_axis: YValue,
    metric: MetricValue,
    use_ms: bool,
) -> None:
    _, axes = plt.subplots(1, len(datas), figsize=(5 * len(datas), 6))
    if len(datas) == 1:
        axes = [axes]

    unit_str: str = "(ms)" if use_ms else "(h)"

    x_value_str: str = x_axis.replace("_", " ")
    metric_value_str: str = metric.replace("_", " ")

    for i, data in enumerate(datas):
        data[0].plot(kind="bar", ax=axes[i], width=1.0)
        axes[i].set_title(f"Dataset {data[1]} - {y_axis} by {x_value_str}")
        axes[i].set_xlabel(x_value_str)
        axes[i].set_ylabel(f"{y_axis} {metric_value_str} {unit_str}")
        axes[i].tick_params(axis="x", rotation=22.5)

    plt.tight_layout()
    plt.show()

    return


def validate(x_axis: XValue, y_axis: YValue) -> None:
    if x_axis in SEGMENT_PROPS and y_axis == YValue.RECORDING:
        raise ValueError(
            "Can't meaningfully aggregate segment-level information over recordings. \
Please choose a different x or y axis."
        )

    return


def get_data(
    dataset: Path, x_axis: XValue, y_axis: YValue, metric: MetricValue, use_ms: bool
) -> pd.Series:
    project = ChildProject(dataset)
    project.read()

    children: pd.DataFrame = project.children
    if "discard" in children.columns:
        children = children[children["discard"] != "1"]

    recordings: pd.DataFrame = project.recordings
    if "discard" in recordings.columns:
        recordings = recordings[recordings["discard"] != "1"]

    ages: pd.Series = project.compute_ages(recordings, children)
    ages.name = XValue.CHILD_AGE.value

    children = pd.concat([children, ages], axis=1)

    child_recordings = children.merge(recordings, on="child_id", how="inner")

    if x_axis in CHILD_PROPS:
        if y_axis == YValue.SEGMENT:
            return get_data_child_segments(
                child_recordings, x_axis, metric, project, use_ms
            )

        if y_axis == YValue.RECORDING:
            return get_data_child_recordings(child_recordings, x_axis, metric, use_ms)

    if x_axis in SEGMENT_PROPS:
        if y_axis == YValue.SEGMENT:
            return get_data_child_segments(
                child_recordings, x_axis, metric, project, use_ms
            )

        if y_axis == YValue.RECORDING:
            pass

    raise ValueError("Invalid choice of x or y axis")


def get_data_child_segments(
    child_recordings: pd.DataFrame,
    x_axis: XValue,
    metric: MetricValue,
    project: ChildProject,
    use_ms: bool,
) -> pd.Series:
    am = AnnotationManager(project)
    gold_std_sets = get_gold_std_sets(am)
    annotations = am.annotations
    annotations = annotations[annotations["set"].isin(gold_std_sets)]

    segments = am.get_segments(annotations)
    segments["duration"] = segments["segment_offset"] - segments["segment_onset"]

    if not use_ms:
        segments["duration"] = segments["duration"].apply(ms_to_hours)

    segments = segments.reindex(
        columns=(["recording_filename", "duration"] + [p.value for p in SEGMENT_PROPS])
    )

    child_recordings = child_recordings.reindex(
        columns=([p.value for p in CHILD_PROPS] + ["recording_filename"])
    )
    data = child_recordings.merge(segments, on="recording_filename", how="inner")

    return get_grouped_data(data, x_axis, metric)


def get_gold_std_sets(am: AnnotationManager) -> List[str]:
    sets_metadata: pd.DataFrame = am.get_sets_metadata()

    sets_metadata = sets_metadata[sets_metadata["method"] == "manual"]

    return [s for s in sets_metadata.index]


def get_data_child_recordings(
    child_recordings: pd.DataFrame, x_axis: XValue, metric: MetricValue, use_ms: bool
) -> pd.Series:
    data = child_recordings.reindex(
        columns=([p.value for p in CHILD_PROPS] + ["duration"])
    )

    if not use_ms:
        data["duration"] = data["duration"].apply(ms_to_hours)

    if x_axis == XValue.CHILD_AGE:
        data[x_axis] = pd.cut(data[x_axis], bins=10, precision=1)

    return get_grouped_data(data, x_axis, metric)


def get_grouped_data(
    data: pd.DataFrame, x_axis: XValue, metric: MetricValue
) -> pd.Series:
    grouped_data = data.groupby(x_axis, dropna=False)["duration"]

    if metric == MetricValue.COUNT:
        return grouped_data.count()
    elif metric == MetricValue.DURATION_MEAN:
        return grouped_data.mean()
    elif metric == MetricValue.DURATION_STD:
        return grouped_data.std()
    elif metric == MetricValue.DURATION_TOTAL:
        return grouped_data.sum()


def save_data(
    datas: List[Tuple[pd.Series, str]],
    x_axis: XValue,
    y_axis: YValue,
    metric: MetricValue,
    output_folder: Path,
) -> None:
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    for data in datas:
        filename = f"{data[1]}_{y_axis}_{metric}_by_{x_axis}.csv"
        output_path = output_folder / filename

        df = data[0].to_frame(name=f"{y_axis}_{metric}")
        df.index.name = x_axis

        df.to_csv(output_path)
        print(f"Saved data to: {output_path}")

    return


def ms_to_hours(ms: float) -> float:
    return ms / (60 * 60 * 1000)


if __name__ == "__main__":
    graph()
