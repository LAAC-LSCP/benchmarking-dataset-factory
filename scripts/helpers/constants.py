from pathlib import Path

CURRENT_FILE: Path = Path(__file__)
SCRIPT_FOLDER: Path = CURRENT_FILE.parent.parent
METADATA_FOLDER: Path = (SCRIPT_FOLDER / ".." / "metadata").resolve()
DATASETS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "datasets").resolve()
OUTPUTS_FOLDER: Path = (SCRIPT_FOLDER / ".." / "outputs").resolve()
