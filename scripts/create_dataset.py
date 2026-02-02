import logging
import os
from pathlib import Path
from typing import List, Tuple

import click
import pandas as pd
from dotenv import load_dotenv

from scripts.src.steps.split_recordings import SplitRecordings
from scripts.src.utils.constants import DATASETS_FOLDER

from .find_files_on_filter_expression import find_files
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
    "--overwrite",
    is_flag=True,
    default=False,
    help="Whether to overwrite existing files",
)
@click.option(
    "--fetch-files",
    is_flag=True,
    default=False,
    help="Whether to fetch datalad files",
)
@click.option(
    "--split-recordings",
    is_flag=True,
    default=False,
    help="Whether to split recordings and keep only sampled parts",
)
@click.option(
    "--type",
    type=click.Choice(
        ["vtc", "addressee", "transcription", "vcm"], case_sensitive=False
    ),
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
    type=click.Choice([s.value for s in StepName], case_sensitive=False),
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
    overwrite: bool,
    fetch_files: bool,
    split_recordings: bool,
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
        logger.info("Finding files, annotations, and metadata (may take a while)...")
        file_infos, children_df, recordings_df, annotations_df = get_file_paths(
            source,
            children_filter_expr,
            dataset_type,
            datasets_dir,
        )

        env = EnvConfig(
            conda_activation_str=activation_str,
        )

        pipeline_steps: List[Step] = [
            AddBoilerplate(env),
            AddMetadata(
                env,
                children=children_df,
                recordings=recordings_df,
                annotations=annotations_df,
            ),
            AddAnnotations(env, file_infos=file_infos, fetch_files=fetch_files),
            AddRecordings(env, file_infos=file_infos, fetch_files=fetch_files),
        ]

        if split_recordings:
            pipeline_steps += [
                SplitRecordings(env),
            ]

        if len(steps) != 0:
            pipeline_steps = [s for s in pipeline_steps if s.name.value in steps]

        pipeline = DatasetPipeline(
            output_path=output_dir,
            datasets_dir=datasets_dir,
            steps=pipeline_steps,
            overwrite=overwrite,
        )

        pipeline.run()
    except Exception as e:
        logger.error(f"Error during dataset creation: {e}")
        raise


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
    dataset_type: DatasetType,
    datasets_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metannots_filter_expr: str
    if dataset_type == DatasetType.VTC:
        metannots_filter_expr = "has_speaker_type == 'Y'"
    elif dataset_type == DatasetType.ADDRESSEE:
        metannots_filter_expr = "has_addressee == 'Y'"
    elif dataset_type == DatasetType.VOCAL_MATURITY:
        metannots_filter_expr = "has_vcm_type == 'Y'"
    elif dataset_type == DatasetType.TRANSCRIPTION:
        metannots_filter_expr = "has_transcription == 'Y'"
    else:
        raise ValueError("dataset type not valid")

    return find_files(
        dataset=datasets,
        metannots_filter_expr=metannots_filter_expr,
        children_filter_expr=children_filter_expr,
        datasets_dir=datasets_dir,
    )


if __name__ == "__main__":
    create_dataset()
