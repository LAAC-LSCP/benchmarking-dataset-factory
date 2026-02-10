"""
This script validates manually_annotated_metadata.json against the
human_annotation_data in the outputs folder
"""

import click
from pydantic import ValidationError

from scripts.src.human_annotation_metadata.schema_manual_metadata import (
    dataset_model_factory,
)
from scripts.src.metadata import get_generated_metadata, get_manual_metadata
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


@click.command()
def validate_manual_metadata() -> None:
    """
    Validate manual metadata
    """
    generated_data = get_generated_metadata()
    manual_data = get_manual_metadata()

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
