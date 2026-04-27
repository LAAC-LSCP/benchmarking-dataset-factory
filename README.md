# Benchmarking Dataset Factory 2025
This repository provides a unified pipeline for generating benchmarking datasets for supervised machine learning models for language tasks, with a focus on human "gold-standard" annotation data. The existing corpora currently used as input are those containing long form audio recordings. It was originally designed for the ExELang lab ecosystem.

All datasets follow the [ChildProject](https://childproject.readthedocs.io/en/latest/format.html) format. ChildProject is a Python package and pipeline tool for managing and processing long-form child-centered audio recordings and their annotations. Familiarity with its dataset structure (recordings, annotations, metadata) is assumed when adding new datasets. The repository includes:

- Scripts for dataset creation, validation, and metadata generation
- Human annotation data (addressee, vocal maturity, transcription, vocalization type) inside a number of datasets in the datasets folder
- Utilities for inspecting, filtering, and splitting data

---

## Pipeline

### Step 1 — Install DataLad and Clone the Repository
This repository is managed with [DataLad](https://www.datalad.org/). Large files (recordings, annotations, etc.) are not stored directly in git — they are annexed and only their lightweight pointers are tracked. You need to explicitly **get** files to download their content, and you can **drop** them to free up local disk space while keeping the pointers.

Install DataLad:

```bash
# via uv (recommended):
uv tool install datalad
# or on macOS via Homebrew:
brew install datalad
```

Then clone the repository from [GIN](https://gin.g-node.org/):

```bash
datalad clone git@gin.g-node.org:/LAAC-LSCP/benchmarking-data-2025.git
cd benchmarking-data-2025
datalad get -n .
```

`datalad get -n .` retrieves the subdataset metadata without downloading large files yet.

### Step 2 — Install uv, Dependencies, and System Tools
Install `uv` by following the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

From the root of the repository, install all Python dependencies into a local virtual environment:

```bash
uv sync
```

`uv run` handles the virtual environment automatically for all subsequent commands. If you prefer to activate it manually:

```bash
source .venv/bin/activate
```

Install `sox`, which is required for the audio splitting step:

```bash
# macOS
brew install sox

# Linux (Debian/Ubuntu)
apt install sox
```

### Step 3 — Fetch Human Annotations
`make` is required for this step. On macOS it is included with Xcode Command Line Tools (`xcode-select --install`); on Linux it is typically pre-installed.

From the root of the repository:

```bash
make get_annotations
```

This fetches all converted annotation files (`.csv`) across all datasets. To free up disk space later:

```bash
make drop_annotations
```

---

> **Using existing datasets only?** If you want to generate a benchmarking dataset from the datasets already in this repository, skip ahead to [Step 8](#step-8--generate-a-benchmarking-dataset). Steps 4–7 are only needed when adding a new dataset.

---

### Step 4 — Add a New Dataset _(optional)_
The existing datasets live under `/datasets`. Each dataset must follow the [ChildProject](https://childproject.readthedocs.io/en/latest/format.html) directory structure — i.e. it must contain `recordings/`, `annotations/`, and `metadata/` folders in the expected layout. To add a new one, run from the root of the repository:

```bash
cd datasets
datalad clone -d .. [remote storage URL]
datalad get --no-data [repository name]
# To fetch large files:
datalad get [glob pattern] -J [num connections]
cd ..
```

Each annotation set within the dataset must have a `metannots.yml` file describing it.

### Step 5 — Generate Human Annotation Metadata _(optional, needed when adding a new dataset)_
Inspect and summarize the available annotation data for your new dataset:

```bash
uv run -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
```

This creates `outputs/human_annotation_data/human_annotation_data-my_dataset.json`. Here is an example for `png2016`:

```json
{
  "name": "png2016",
  "sets": [
    {
      "name": "eaf_2016",
      "columns": [
        {
          "column": "mwu_type",
          "categorical": true,
          "annotated_duration_ms": 1337411,
          "duration_from_samples_ms": 22454000,
          "number_of_samples": 206,
          "num_of_non_empty_segments": 1519
        },
...
```

This output tells you which annotation sets exist and what columns they contain. If annotation files are missing when you run this, fetch them first:

```bash
datalad get [glob pattern]
# e.g.: datalad get datasets/png2016/annotations/eaf_2016/converted/**
```

### Step 6 — Update the Manual Metadata Index _(optional, needed when adding a new dataset)_
`outputs/manually_annotated_metadata.json` is a hand-written index that maps each dataset's annotation sets to the four annotation categories: addressee, vcm (vocalization/speech maturity), vtc (vocalization type), and transcription. Using the output from step 5 as a guide, add an entry for your dataset:

```json
{
    "datasets": [
        {
            "name": "my_dataset",
            "sets": [
                {
                    "name": "eaf/an1",
                    "addressee_cols": ["addressee"],
                    "vcm_cols": ["vcm_type"],
                    "vtc_cols": ["speaker_type"],
                    "transcription_cols": ["transcription"],
                    "other": ["words", "lex_type", "mwu_type", "speaker_id"]
                }
            ]
        }
    ]
}
```

Which sets contain which annotation types can only be determined through human judgment — inspect the metadata output from step 5 and, if needed, the annotation files themselves.

### Step 7 — Validate the Manual Metadata Index _(optional, needed when adding a new dataset)_
Because the index is hand-written, it must be validated before use:

```bash
uv run -m scripts.validate_manual_metadata
```

This checks that column names are not misspelled and that referenced sets actually exist in the annotation files. Fix any errors and re-run until it passes cleanly.

### Step 8 — Generate a Benchmarking Dataset
Create a benchmarking dataset by specifying an output path, the annotation type, and one or more datasets. Dataset names must match entries in `outputs/manually_annotated_metadata.json`.

```bash
uv run -m scripts.create_dataset \
  --output-path [output path] \
  --type vtc \
  --fetch-files \
  -d my_dataset \
  -d my_other_dataset
```

- `--output-path`: where to write the generated dataset
- `--type`: annotation type to use — one of `vtc`, `vcm`, `addressee`, `transcription`
- `--fetch-files`: automatically fetch any missing recording files via DataLad
- `-d`: dataset name to include (repeat for multiple datasets)

Run with `--help` for the full list of options. The script can generate the full dataset in one go, or incrementally one dataset or one step at a time — useful for short feedback loops during testing.

### Step 9 — Add More Datasets Incrementally _(optional)_
To add a dataset to an already-generated benchmarking dataset without rebuilding from scratch, use `--additive`:

```bash
uv run -m scripts.create_dataset \
  --output-path [output path] \
  --type vtc \
  --fetch-files \
  -d my_added_dataset \
  --additive
```

It is recommended to build composite datasets one dataset at a time — changes are more manageable.

### Troubleshooting
- **Command not found:** Make sure you are in the root of the repository.
- **Missing package:** Install with `uv add [package_name]`.
- **Permission denied:** Try running with `sudo` (Linux/Mac) or as administrator (Windows), or check file permissions.
- **Script errors:** Read the error message carefully. Most issues are due to missing dependencies or annotation files that have not been fetched yet.

---


## Scripts Overview

The main scripts in the `scripts/` folder are:

- **create_dataset.py**: Main entry point for dataset generation. Highly parameterized; see `--help` for options.
- **get_human_annotation_metadata.py**: Aggregates and summarizes annotation metadata for a dataset.
- **validate_manual_metadata.py**: Validates the manual metadata index against available data.
- **create_table_corpora_info.py**: Creates a table with information about human annotation corpora.
- **datasets_metadata.py**: Summarizes metadata over datasets (used for paper tables).
- **graph_dataset_distribution.py**: Graphs distributional information of metadata.
- **split_data.py**: Splits data into train, test, and validation sets with stratification.

For usage details and available options, run each script with the `--help` flag.

---

## Data Categories

The main annotation categories in this repository are:

1. **Addressee**: Who is being addressed (target/other child, adult, pet, etc.)
2. **Vocalization/speech maturity**: Canonical/non-canonical vocalizations, syllable types, etc.
3. **Transcription**: What is said, sometimes with translations.
4. **Vocalization type**: Key child, other child, adult male, adult female (see `speaker_type`).

---

## Development

### Dependency Management
Dependencies are managed with `uv`. If you encounter missing dependencies, install them with `uv add [package_name]`.

### Linting & Formatting
To keep the code clean and standardized, run `tox` (install with `pipx install tox`) to check code quality in the `scripts/` folder.

---

## Legacy Scripts

These scripts are for exploratory or legacy purposes. Most users can ignore them:

- **find_files_on_filter_expression.py**: Find files matching filter expressions on metadata.
- **find_on_filter_expression.py**: Find datasets/sets matching a filter expression.
- **validate_metannots.py**: Validate metannots files for schema compliance.
- **get_human_annotation_metadata.py**: Aggregate and summarize annotation metadata.
- **graph_dataset_distribution.py**: Graph distributional information of metadata.
- **split_data.py**: Split data into train, test, and validation sets with stratification.

See script docstrings or run with `--help` for details.


