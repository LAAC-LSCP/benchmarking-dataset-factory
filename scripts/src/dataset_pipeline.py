from pathlib import Path
from typing import List, Optional

from scripts.src.steps.step import Step
from scripts.src.utils.exceptions import StepFailedException
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetPipeline:
    _output_path: Path
    _datasets_dir: Path
    _steps: List[Step]

    def __init__(
        self,
        output_path: Path,
        datasets_dir: Path,
        steps: Optional[List[Step]] = None,
    ) -> None:
        self._output_path = output_path
        self._steps = steps or []
        self._datasets_dir = datasets_dir

        return

    def run(self) -> None:
        logger.info("Running pipeline...")
        for step in self._steps:
            try:
                step.run(self._datasets_dir, self._output_path)
            except StepFailedException as e:
                logger.exception(f"Exception occured: {repr(e)} \
Stopping and exciting...")

                return
        logger.info("Finished running dataset pipeline")

        return
