import subprocess
from pathlib import Path

from scripts.src.steps.file_management import datalad_save, git_unannex_and_save
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


class AddBoilerplate(Step):
    def __init__(self, env: EnvConfig) -> None:
        super().__init__(env=env, name=StepName.ADD_BOILERPLATE)

    def _run(self, _: Path, dest_dataset: Path, __: bool) -> None:
        logger.info(f"Preparing output directory: {dest_dataset}")

        if not dest_dataset.exists():
            dest_dataset.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory created: {dest_dataset}")

            logger.info("Initialising childproject...")
            self._initialise_childproject(dest_dataset)
            logger.info("Initialising datalad...")
            self._initialise_datalad(dest_dataset)
            datalad_save(self._env, dest_dataset, "Added ChildProject boilerplate")
            logger.info("Handling .gitignore...")
            self._initialise_gitignore(dest_dataset)
            logger.info("Handling .gitattributes...")
            self._initialise_gitattributes(dest_dataset)

            git_unannex_and_save(
                self._env, dest_dataset, "metadata/*", "Unannexed metadata and saved"
            )
            git_unannex_and_save(
                self._env, dest_dataset, "README.md", "Unannexed README.md and saved"
            )

        return

    def _initialise_childproject(self, dest_dataset: Path) -> None:
        commands = [
            self._env.conda_activation_str,
            "child-project init .",
        ]
        shell_command = " && ".join(commands)

        logger.info(f"Running shell command: {shell_command} (cwd={dest_dataset})")
        try:
            subprocess.run(shell_command, shell=True, check=True, cwd=dest_dataset)
            logger.info("childproject dataset initialized successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise e

    def _initialise_datalad(self, dest_dataset: Path) -> None:
        commands = [
            self._env.conda_activation_str,
            "datalad create --force",
        ]
        shell_command = " && ".join(commands)

        logger.info(f"Running shell command: {shell_command} (cwd={dest_dataset})")
        try:
            subprocess.run(shell_command, shell=True, check=True, cwd=dest_dataset)
            logger.info("childproject dataset initialized successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise e

    def _initialise_gitignore(self, dest_dataset: Path) -> None:
        gitignore_file = dest_dataset / ".gitignore"
        ds_store_entry = ".DS_Store"

        if not gitignore_file.exists():
            gitignore_file.write_text(f"{ds_store_entry}\n")
            logger.info(f"Created .gitignore at {gitignore_file} (ignoring .DS_Store)")
            datalad_save(self._env, dest_dataset, "added .gitignore")
            return

        with gitignore_file.open("r") as f:
            existing = set(line.strip() for line in f)

        if ds_store_entry not in existing:
            with gitignore_file.open("a") as f:
                f.write(f"{ds_store_entry}\n")
            logger.info(f"Added .DS_Store to .gitignore at {gitignore_file}")
            datalad_save(self._env, dest_dataset, "updated .gitignore")

    def _initialise_gitattributes(self, dest_dataset: Path) -> None:
        gitattributes_file = dest_dataset / ".gitattributes"
        content = (
            "* annex.backend=MD5E\n"
            "README.md annex.largefiles=nothing\n"
            "**/.git* annex.largefiles=nothing\n"
            "scripts/** annex.largefiles=nothing\n"
            "metadata/*.csv annex.largefiles=nothing\n"
            "recordings/** annex.largefiles=((mimeencoding=binary)and(largerthan=0))\n"
            "annotations/** annex.largefiles=nothing\n"
            "**/*.yml annex.largefiles=nothing\n"
        )

        gitattributes_file.write_text(content)
        logger.info(f"Wrote .gitattributes at '{gitattributes_file!s}'")
        datalad_save(self._env, dest_dataset, "updated .gitattributes")
