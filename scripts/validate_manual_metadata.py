"""
This script validates manually_annotated_metadata.json against the
human_annotation_data in the outputs folder
"""

from typing import Tuple

import click
from pydantic import ValidationError

from scripts.src.human_annotation_metadata.schema_manual_metadata import (
    dataset_model_factory,
)
from scripts.src.metadata import get_generated_metadata, get_manual_metadata
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


@click.command()
@click.option(
    "--source",
    "-d",
    multiple=True,
    help="datasets to source from. If not specified, will use all datasets",
)
def validate_manual_metadata(source: Tuple[str]) -> None:
    """
    Validate manual metadata
    """
    generated_data = get_generated_metadata()
    manual_data = get_manual_metadata()

    if len(source):
        for s in source:
            available_datasets = [ds["name"] for ds in manual_data["datasets"]]
            if s not in available_datasets:
                logger.error(f"{s} not in {available_datasets!s}")
                return

        manual_data["datasets"] = [
            ds for ds in manual_data["datasets"] if ds["name"] in source
        ]

    try:
        dataset_model_factory(generated_data)(**manual_data)

        logger.info("All good!")
    except ValidationError as e:
        for err in e.errors():
            logger.info(f"Error in {err['loc']}: {err['msg']}")
        return
    return


if __name__ == "__main__":
    validate_manual_metadata()
