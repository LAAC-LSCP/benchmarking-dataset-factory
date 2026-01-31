from pathlib import Path
from typing import Set

CURRENT_FILE: Path = Path(__file__)
CURRENT_FOLDER: Path = CURRENT_FILE.parent
SCRIPTS_FOLDER: Path = CURRENT_FOLDER.parent.parent
METADATA_FOLDER: Path = (SCRIPTS_FOLDER / ".." / "metadata").resolve()
DATASETS_FOLDER: Path = (SCRIPTS_FOLDER / ".." / "datasets").resolve()
OUTPUTS_FOLDER: Path = (SCRIPTS_FOLDER / ".." / "outputs").resolve()


for folder in [METADATA_FOLDER, DATASETS_FOLDER, OUTPUTS_FOLDER]:
    assert folder.exists()


DATASETS: Set[str] = {d.name for d in DATASETS_FOLDER.iterdir() if d.is_dir()}
