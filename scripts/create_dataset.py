import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, List, Set, Tuple
import click
import pandas as pd
from dotenv import load_dotenv
import logging

from find_files_on_filter_expression import find_files
from helpers.constants import DATASETS_FOLDER
from helpers.dataset_type import DatasetType



load_dotenv()
ORGANIZATION_REPO = os.getenv("ORGANIZATION_REPO")
CONDA_ACTIVATE_FILE = os.getenv("CONDA_ACTIVATE_FILE")
CONDA_CHILDPROJECT_ENV = os.getenv("CONDA_CHILDPROJECT_ENV")

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
    "--source",
    "-d",
    multiple=True,
    help="datasets to source from. If not specified, will use all datasets",
)
@click.option(
    "--rewrite",
    is_flag=True,
    default=False,
    help="Whether to rewrite an existing output folder",
)
@click.option(
    "--type",
    type=click.Choice(["vtc", "addressee, transcription, vcm"], case_sensitive=False),
    required=True,
    help="Type of dataset to create",
)
@click.option(
    "--children-filter-expr",
    required=False,
    default=None,
    help="Filter expression on children metadata \
like 'child_sex == 'F'' (see Pandas + \
ChildProject docs)",
)
def create_dataset(
    output_path: str, source: Tuple[str], rewrite: bool, type: str, children_filter_expr: str | None
) -> None:
    logger.info(f"Starting dataset creation: output_path={output_path}, rewrite={rewrite}, type={type}, sources={source}")
    try:
        output_dir, rewrite, dataset_type = _validate(output_path, rewrite, type)

        logger.info("Finding matching files and metadata (may take a while)...")
        file_infos, children_df, recordings_df, annotations_df = _get_file_paths(source, children_filter_expr, dataset_type)
        logger.info("Creating dataset boilerplate...")
        _create_dataset(output_dir, rewrite)
        logger.info("Adding metadata...")
        _add_metadata(output_dir, children_df, recordings_df, annotations_df)
        logger.info("Adding annotations (this may take some time)...")
        _add_annotations(output_dir, file_infos, rewrite)
        logger.info("Adding recordings (this may take some time)...")
        _add_recordings(output_dir, file_infos, rewrite)

        logger.info(f"Dataset creation completed: {output_dir}")
    except Exception as e:
        logger.error(f"Error during dataset creation: {e}")
        raise


def _create_dataset(output_path: Path, rewrite: bool) -> None:
    logger.info(f"Preparing output directory: {output_path}")

    if output_path.exists() and rewrite:
        logger.info(f"Output directory exists, removing: {output_path}")

        _remove_dataset(output_path)

    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory created: {output_path}")

        _initialise_childproject(output_path)
        _initialise_datalad(output_path)

    return


def _remove_dataset(output_path: Path) -> None:
    if not any(
        f.is_file() and not any(x in f.parts for x in [".git", ".datalad", ".gitattributes"])
        for f in output_path.rglob("*")
    ):
        shutil.rmtree(output_path)

        return

    is_git_repo = (output_path / ".git").exists()
    is_datalad_repo = (output_path / ".datalad").exists()

    commands = [
        f"source {CONDA_ACTIVATE_FILE}",
        f"conda activate {CONDA_CHILDPROJECT_ENV}",
        "git add ." if is_git_repo else None,
        "git reset --hard HEAD" if is_git_repo else None,
        "datalad drop --recursive . --reckless kill" if is_datalad_repo else None,
        "datalad remove --recursive *" if is_datalad_repo else None,
    ]
    commands = [c for c in commands if c is not None]
    shell_command = " && ".join(commands)

    logger.info(f"Running shell command: {shell_command} (cwd={output_path})")
    try:
        subprocess.run(shell_command, shell=True, check=True, cwd=output_path)
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e}")
        logger.error(f"Subprocess stdout: {e.stdout}")
        logger.error(f"Subprocess stderr: {e.stderr}")
        raise
    shutil.rmtree(output_path)


def _initialise_childproject(output_path: Path) -> None:
    commands = [
        f"source {CONDA_ACTIVATE_FILE}",
        f"conda activate {CONDA_CHILDPROJECT_ENV}",
        f"child-project init ."
    ]
    shell_command = " && ".join(commands)

    logger.info(f"Running shell command: {shell_command} (cwd={output_path})")
    try:
        subprocess.run(shell_command, shell=True, check=True, cwd=output_path)
        logger.info("childproject dataset initialized successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e}")
        logger.error(f"Subprocess stdout: {e.stdout}")
        logger.error(f"Subprocess stderr: {e.stderr}")
        raise


def _initialise_datalad(output_path: Path) -> None:
    commands = [
        f"source {CONDA_ACTIVATE_FILE}",
        f"conda activate {CONDA_CHILDPROJECT_ENV}",
        f"datalad create --force"
    ]
    shell_command = " && ".join(commands)

    logger.info(f"Running shell command: {shell_command} (cwd={output_path})")
    try:
        subprocess.run(shell_command, shell=True, check=True, cwd=output_path)
        logger.info("childproject dataset initialized successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e}")
        logger.error(f"Subprocess stdout: {e.stdout}")
        logger.error(f"Subprocess stderr: {e.stderr}")
        raise


def _add_metadata(output_dir: Path, children: pd.DataFrame, recordings: pd.DataFrame, annotations_df: pd.DataFrame) -> None:
    logger.info("Adding children.csv...")
    children["experiment"] = "benchmarking"
    children.to_csv(output_dir / "metadata" / "children.csv", index=False)
    logger.info("Adding recordings.csv...")
    recordings["experiment"] = "benchmarking"
    recordings.to_csv(output_dir / "metadata" / "recordings.csv", index=False)
    logger.info("Adding annotations.csv...")
    annotations_df.to_csv(output_dir / "metadata" / "annotations.csv", index=False)

    return


def _add_annotations(output_dir: Path, file_paths: pd.DataFrame, rewrite: bool) -> None:
    file_pairs: Set[Tuple[Path, Path]] = set()
    dataset_file_map: Dict[str, Set[Tuple[Path, Path]]] = {d: set() for d in file_paths["dataset"].unique()}
    for _, row in file_paths.iterrows():
        src = row["annotation path"]

        dst = _get_dst_annotation(src, output_dir, row["dataset"])

        file_pairs.add((src, dst))
        dataset_file_map[row["dataset"]].add((src, dst))

    if rewrite == False:
        # skip things that are already added
        file_pairs = {(src, dst) for (src, dst) in file_pairs if not dst.exists()}
        dataset_file_map = {dataset: {(src, dst) for (src, dst) in files if not dst.exists()} for (dataset, files) in dataset_file_map.items()}

    if len(file_pairs) != 0:
        _fetch_files(dataset_file_map)
        _copy_files(file_pairs, output_dir)

    return


def _fetch_files(dataset_file_map: Dict[str, Set[Tuple[Path, Path]]]) -> None:
    for dataset, files in dataset_file_map.items():
        if len(files) == 0:
            continue

        commands = [
            f"source {CONDA_ACTIVATE_FILE}",
            f"conda activate {CONDA_CHILDPROJECT_ENV}",
            f"datalad get {' '.join(str(src) for (src, _) in files)} -J 10"
            ]
        shell_command = " && ".join(commands)
        try:
            logger.info(f"Fetching {len(files)} files in {dataset}...")
            subprocess.run(shell_command, shell=True, check=True, cwd=DATASETS_FOLDER / dataset)
            logger.info(f"Fetched {len(files)} files in {dataset}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch file with datalad: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise

    return


def _add_recordings(output_dir: Path, file_paths: pd.DataFrame, rewrite: bool) -> None:
    file_pairs: Set[Tuple[Path, Path]] = set()
    dataset_file_map: Dict[str, Set[Tuple[Path, Path]]] = {d: set() for d in file_paths["dataset"].unique()}
    for _, row in file_paths.iterrows():
        src_converted = row["recording path"]
        src_raw = row["recording path raw"]

        dst_converted = _get_dst_recording_converted_standard(src_converted, output_dir, row["dataset"])
        dst_raw = _get_dst_recording_raw(src_raw, output_dir, row["dataset"])

        file_pairs.add((src_converted, dst_converted))
        file_pairs.add((src_raw, dst_raw))
        dataset_file_map[row["dataset"]].add((src_converted, dst_converted))
        dataset_file_map[row["dataset"]].add((src_raw, dst_raw))

    if rewrite == False:
        # skip things that are already added
        file_pairs = {(src, dst) for (src, dst) in file_pairs if not dst.exists()}
        dataset_file_map = {dataset: {(src, dst) for (src, dst) in files if not dst.exists()} for (dataset, files) in dataset_file_map.items()}

    if len(file_pairs) != 0:
        _fetch_files(dataset_file_map)
        _copy_files(file_pairs, output_dir)

    return


def _get_file_paths(datasets: Tuple[str], children_filter_expr: str | None, dataset_type: DatasetType) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metannots_filter_expr: str
    if dataset_type == DatasetType.VTC:
        metannots_filter_expr = "has_speaker_type == 'Y'"
    elif dataset_type == DatasetType.ADDRESSEE:
        metannots_filter_expr = "has_addressee == 'Y'"
    elif dataset_type == DatasetType.VOCAL_MATURITY:
        metannots_filter_expr = "has_vcm_type == 'Y'"
    elif dataset_type == DatasetType.VOCAL_MATURITY:
        metannots_filter_expr = "has_transcription == 'Y'"
    else:
        raise ValueError("dataset type not valid")

    return find_files(
        dataset=datasets,
        metannots_filter_expr=metannots_filter_expr,
        children_filter_expr=children_filter_expr,
    )


def _copy_files(file_pairs: Set[Tuple[Path, Path]], dataset: Path) -> None:
    logger.info(f"Copying {len(file_pairs)} files with datalad specfile in dataset {dataset}")
    # We use a specfile because
    # (1) copying files one by one creates numerous commits (generated by DataLad)
    # (2) copying recursively isn't the best strategy, as you can't filter
    spec_lines = [
        f"{os.path.relpath(src, start=dataset)}\0{os.path.relpath(dst, start=dataset)}"
        for (src, dst) in file_pairs
    ]

    if len(spec_lines) == 0:
        return

    specfile_path: Path

    with tempfile.NamedTemporaryFile("w", delete=False) as specfile:
        specfile.write("\n".join(spec_lines))
        specfile_path = specfile.name

    commands = [
        f"source {CONDA_ACTIVATE_FILE}",
        f"conda activate {CONDA_CHILDPROJECT_ENV}",
        f"datalad copy-file --specs-from {specfile_path} -d ."
    ]
    shell_command = " && ".join(commands)
    try:
        subprocess.run(shell_command, shell=True, check=True, cwd=dataset)
        logger.info(f"Copied files using specfile in dataset {dataset}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to copy file with datalad: {e}")
        logger.error(f"Subprocess stdout: {e.stdout}")
        logger.error(f"Subprocess stderr: {e.stderr}")
        raise
    finally:
        os.remove(specfile_path)


def _validate(
    output_path: str, rewrite: bool, dataset_type: str
) -> Tuple[Path, bool, DatasetType]:
    output_dir = Path(output_path)

    dataset_type = dataset_type.lower()

    return output_dir, rewrite, DatasetType(dataset_type)


def _get_dst_annotation(source: Path, output_dir: Path, dataset: str) -> Path:
    parts = source.parts
    idx = parts.index("annotations")
    return output_dir / "annotations" / dataset / Path(*parts[idx + 1:])


def _get_dst_recording_converted_standard(source: Path, output_dir: Path, dataset: str) -> Path:
    parts = source.parts
    idx = parts.index("standard")
    return output_dir / "recordings" / "converted" / "standard" / dataset / Path(*parts[idx+1:])


def _get_dst_recording_raw(source: Path, output_dir: Path, dataset: str) -> Path:
    parts = source.parts
    idx = parts.index("raw")
    return output_dir / "recordings" / "raw" / dataset / Path(*parts[idx+1:])

if __name__ == "__main__":
    create_dataset()
