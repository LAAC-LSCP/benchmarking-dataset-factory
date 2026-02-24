import functools
import logging
import os
from pathlib import Path
from typing import Any, List, Tuple

import click
import pandas as pd
from dotenv import load_dotenv

from scripts.datasets_metadata import COL_TYPE_MAPPING
from scripts.src.human_annotation_metadata.schema_manual_metadata import (
    dataset_model_factory,
)
from scripts.src.metadata import get_generated_metadata, get_manual_metadata
from scripts.src.steps.split_recordings import SplitRecordings
from scripts.src.utils.constants import DATASETS_FOLDER

from .find_files_on_filter_expression import (
    find_files,
    get_annotations_from_files,
    get_children_from_files,
    get_recordings_from_files,
)
from .src.custom_types import DatasetType
from .src.dataset_pipeline import DatasetPipeline
from .src.steps.add_annotations import AddAnnotations
from .src.steps.add_boilerplate import AddBoilerplate
from .src.steps.add_metadata import AddMetadata
from .src.steps.add_recordings import AddRecordings
from .src.steps.step import EnvConfig, Step, StepName

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--output-path",
    type=Path,
    help="Output path for this new dataset",
)
@click.option(
    "--fetch-files",
    is_flag=True,
    default=False,
    help="Whether to fetch datalad files",
)
@click.option(
    "--additive",
    is_flag=True,
    default=False,
    help="Set to true if you're adding datasets",
)
@click.option(
    "--type",
    type=click.Choice([t.value for t in DatasetType]),
    required=True,
    help="Type of dataset to create",
)
@click.option(
    "--source",
    "-d",
    multiple=True,
    help="datasets to source from. If not specified, will use all datasets",
)
@click.option(
    "--step",
    "-s",
    type=click.Choice([s.value for s in StepName]),
    multiple=True,
    help="steps to run. If not specified, run all steps in the pipeline",
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
    "--datasets-folder",
    required=False,
    type=click.Path(exists=True),
    default=None,
    help="Folder with available datasets (note: compares against the \
subfolder in this repo to filter on potential dataset names)",
)
def create_dataset(
    output_path: str,
    fetch_files: bool,
    additive: bool,
    type: str,
    source: Tuple[str],
    step: Tuple[str],
    children_filter_expr: str | None,
    datasets_folder: str | None,
) -> None:
    output_dir, dataset_type, steps, datasets_dir = validate(
        output_path, type, step, datasets_folder
    )

    activation_str = get_from_env("CONDA_ACTIVATION_STR")

    try:
        logger.info(
            "Finding files, annotations, and metadata from metannots (may take a while)..."
        )
        # Gets every file possible (note not using a metannots filter for this)
        file_infos, children_df, recordings_df, annotations_df = get_file_paths(
            source,
            children_filter_expr,
            datasets_dir,
        )

        logger.info("Filtering on relevant data according to manual metadata...")
        # Filters down further based on manual annotations as source of truth (more accurate than metannots)
        generated_data = get_generated_metadata()
        manual_data = dataset_model_factory(generated_data, skip_validation=True)(**get_manual_metadata())
        logger.info(f"Manual data: {repr(manual_data)}")
        file_infos, children_df, recordings_df, annotations_df = filter_on_manual_data(
            file_infos,
            children_df,
            recordings_df,
            annotations_df,
            manual_data,
            dataset_type,
        )

        if len(annotations_df) == 0:
            logger.info("Matched annotations empty. Exiting")

            return

        children_df, recordings_df, annotations_df = fix_columns_for_combined_dfs(
            children_df, recordings_df, annotations_df
        )

        env = EnvConfig(
            conda_activation_str=activation_str,
        )

        pipeline_steps: List[Step] = [
            AddBoilerplate(env, additive),
            AddMetadata(
                env,
                additive,
                children=children_df,
                recordings=recordings_df,
                annotations=annotations_df,
            ),
            AddAnnotations(env, additive, file_infos=file_infos, fetch_files=fetch_files),
            AddRecordings(env, additive, file_infos=file_infos, fetch_files=fetch_files),
            SplitRecordings(
                env,
                additive,
                annotations=annotations_df,
                recordings=recordings_df,
                remove_full_recordings=True,
            ),
        ]

        if len(steps) != 0:
            pipeline_steps = [s for s in pipeline_steps if s.name.value in steps]

        pipeline = DatasetPipeline(
            output_path=output_dir,
            datasets_dir=datasets_dir,
            steps=pipeline_steps,
        )

        pipeline.run()
    except Exception as e:
        logger.error(f"Error during dataset creation: {e}")
        raise

    logger.info("Done!")

    return


def filter_on_manual_data(
    file_infos: pd.DataFrame,
    children_df: pd.DataFrame,
    recordings_df: pd.DataFrame,
    annotations_df: pd.DataFrame,
    manual_data: Any,
    dataset_type: DatasetType,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    file_infos = filter_file_infos_on_manual_data(file_infos, manual_data, dataset_type)
    children_df = get_children_from_files(file_infos, children_df)
    recordings_df = get_recordings_from_files(file_infos, recordings_df)
    annotations_df = get_annotations_from_files(file_infos, annotations_df)

    return file_infos, children_df, recordings_df, annotations_df


def filter_file_infos_on_manual_data(
    file_infos: pd.DataFrame, manual_data: Any, dataset_type: DatasetType
) -> pd.DataFrame:
    """Filters out files that have no data associated with the dataset type"""

    def row_filter(row, manual_data: Any, dataset_type: DatasetType) -> bool:
        dataset = next(
            (d for d in manual_data.datasets if d.name == row["dataset"]), None
        )
        assert dataset is not None
        s = next((s for s in dataset.sets if s.name == row["set"]), None)
        assert s is not None

        relevant_cols = s.__getattribute__(COL_TYPE_MAPPING[dataset_type].value)

        if not len(relevant_cols):
            return False

        annotation_df = pd.read_csv(row["annotation path"])
        available_cols = [col for col in annotation_df.columns if col in relevant_cols]

        if not len(available_cols):
            return False

        annotation_df = annotation_df[available_cols]

        # ignore files with all relevant annotations <NA>
        if not annotation_df.notna().any().any():
            return False

        return True

    return file_infos[
        file_infos.apply(
            functools.partial(
                row_filter, manual_data=manual_data, dataset_type=dataset_type
            ),
            axis=1,
        )
    ]


def fix_columns_for_combined_dfs(
    children: pd.DataFrame, recordings: pd.DataFrame, annotations: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    children["child_id"] = (
        children["dataset"].astype(str) + "_" + children["child_id"].astype(str)
    )
    children = children.drop("dataset", axis=1)

    annotations["set"] = annotations["dataset"] + "/" + annotations["set"].astype(str)
    annotations["recording_filename"] = (
        annotations["dataset"] + "/" + annotations["recording_filename"].astype(str)
    )
    annotations = annotations.drop("dataset", axis=1)

    filename_cols = [col for col in recordings.columns if col.endswith("_filename")]
    for col in filename_cols:
        recordings[col] = (
            recordings["dataset"].astype(str) + "/" + recordings[col].astype(str)
        )

    recordings["child_id"] = (
        recordings["dataset"].astype(str) + "_" + recordings["child_id"].astype(str)
    )
    recordings = recordings.drop("dataset", axis=1)

    return children, recordings, annotations


def validate(
    output_path: str,
    dataset_type: str,
    steps: Tuple[str],
    datasets_folder: str | None,
) -> Tuple[Path, DatasetType, Tuple[str], Path]:
    output_dir = Path(output_path)

    dataset_type = dataset_type.lower()

    return (
        output_dir,
        DatasetType(dataset_type),
        steps,
        Path(datasets_folder) if datasets_folder else DATASETS_FOLDER,
    )


def get_from_env(key: str) -> str:
    value = os.getenv(key)

    if not value:
        raise ValueError(f"env var with key '{key}' not set")

    return value


def get_file_paths(
    datasets: Tuple[str],
    children_filter_expr: str | None,
    datasets_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return find_files(
        dataset=datasets,
        metannots_filter_expr=None,
        children_filter_expr=children_filter_expr,
        datasets_dir=datasets_dir,
    )


if __name__ == "__main__":
    create_dataset()
