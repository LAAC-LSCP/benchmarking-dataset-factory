import shutil
import subprocess
from pathlib import Path

from scripts.src.steps.file_management import datalad_save, git_unannex_and_save
from scripts.src.steps.step import EnvConfig, Step, StepName
from scripts.src.utils.logger import get_logger

logger = get_logger(__name__)


current_file = Path(__file__)
static_folder = current_file.parent.parent.parent.parent / "static"

# in case things get moved
assert static_folder.exists()


class AddBoilerplate(Step):
    def __init__(self, env: EnvConfig, additive: bool) -> None:
        super().__init__(env=env, additive=additive, name=StepName.ADD_BOILERPLATE)

    def _run(self, _: Path, dest_dataset: Path) -> None:
        if self.additive:
            logger.info("Skipping boilerplate step as `additive==True`")

            return

        logger.info(f"Preparing output directory: {dest_dataset}")

        if not dest_dataset.exists():
            dest_dataset.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory created: {dest_dataset}")

            logger.info("Initialising childproject...")
            self._initialise_childproject(dest_dataset)
            logger.info("Initialising datalad...")
            self._initialise_datalad(dest_dataset)
            logger.info("Handling .gitignore...")
            self._initialise_gitignore(dest_dataset)
            logger.info("Handling .gitattributes...")
            self._initialise_gitattributes(dest_dataset)
            logger.info("Adding scripts...")
            self._add_scripts(dest_dataset)
            logger.info("Initialising uv...")
            self._initialise_uv(dest_dataset)

            git_unannex_and_save(
                self.env, dest_dataset, "metadata/*", "Unannexed metadata and saved"
            )
            git_unannex_and_save(
                self.env, dest_dataset, "README.md", "Unannexed README.md and saved"
            )

        logger.info("Adding README.md...")
        self._add_readme(dest_dataset)

        return

    def _initialise_childproject(self, dest_dataset: Path) -> None:
        shell_command = self.env.build_command("child-project init .")

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
        shell_command = self.env.build_command("datalad create --force")

        logger.info(f"Running shell command: {shell_command} (cwd={dest_dataset})")
        try:
            subprocess.run(shell_command, shell=True, check=True, cwd=dest_dataset)
            logger.info("childproject dataset initialized successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e}")
            logger.error(f"Subprocess stdout: {e.stdout}")
            logger.error(f"Subprocess stderr: {e.stderr}")
            raise e

        datalad_save(self.env, dest_dataset, "Added ChildProject boilerplate")

    def _initialise_gitignore(self, dest_dataset: Path) -> None:
        gitignore_file = dest_dataset / ".gitignore"
        ds_store_entry = ".DS_Store"

        if not gitignore_file.exists():
            gitignore_file.write_text(f"{ds_store_entry}\n")
            logger.info(f"Created .gitignore at {gitignore_file} (ignoring .DS_Store)")
            datalad_save(self.env, dest_dataset, "added .gitignore")
            return

        with gitignore_file.open("r") as f:
            existing = set(line.strip() for line in f)

        if ds_store_entry not in existing:
            with gitignore_file.open("a") as f:
                f.write(f"{ds_store_entry}\n")
            logger.info(f"Added .DS_Store to .gitignore at {gitignore_file}")
            datalad_save(self.env, dest_dataset, "updated .gitignore")

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
        datalad_save(self.env, dest_dataset, "updated .gitattributes")

    def _add_readme(self, dest_dataset: Path) -> None:
        static_readme = static_folder / "dataset_readme.md"
        dest_readme = dest_dataset / "README.md"

        try:
            shutil.copyfile(static_readme, dest_readme)
            logger.info(f"Copied {static_readme} to {dest_readme}")
            datalad_save(self.env, dest_dataset, "added README.md")
        except Exception as e:
            logger.error(f"Failed to copy README.md: {e}")

    def _initialise_uv(self, dest_dataset: Path) -> None:
        init_cmd = self.env.build_command("uv init --no-package --no-readme")
        add_cmd = self.env.build_command("uv add childproject pandas click")

        for shell_command in [init_cmd, add_cmd]:
            logger.info(f"Running shell command: {shell_command} (cwd={dest_dataset})")
            try:
                subprocess.run(shell_command, shell=True, check=True, cwd=dest_dataset)
            except subprocess.CalledProcessError as e:
                logger.error(f"Subprocess failed: {e}")
                raise e

        datalad_save(self.env, dest_dataset, "added pyproject.toml and uv.lock")

    def _add_scripts(self, dest_dataset: Path) -> None:
        static_script = static_folder / "get_splits.py"
        scripts_dir = dest_dataset / "scripts"
        dest_script = scripts_dir / "get_splits.py"

        try:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(static_script, dest_script)
            logger.info(f"Copied {static_script} to {dest_script}")
            datalad_save(self.env, dest_dataset, "added scripts/get_splits.py")
        except Exception as e:
            logger.error(f"Failed to copy get_splits.py: {e}")
