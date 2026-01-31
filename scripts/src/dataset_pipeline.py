from pathlib import Path
from typing import List, Optional

from scripts.src.steps.step import Step
from scripts.src.utils.constants import DATASETS_FOLDER
from scripts.src.utils.exceptions import StepFailedException
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetPipeline:
    _output_path: Path
    _steps: List[Step]
    _overwrite: bool

    def __init__(
        self,
        output_path: Path,
        steps: Optional[List[Step]] = None,
        overwrite: Optional[bool] = None,
    ) -> None:
        self._output_path = output_path
        self._steps = steps or []
        self._overwrite = overwrite or False

        return

    def run(self) -> None:
        logger.info("Running pipeline...")
        for step in self._steps:
            try:
                step.run(DATASETS_FOLDER, self._output_path, self._overwrite)
            except StepFailedException as e:
                logger.exception(f"Exception occured: {repr(e)} \
Stopping and exciting...")

                return
        logger.info("Finished running dataset pipeline")

        return
