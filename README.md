# Benchmarking Dataset Factory 2025
This repository provides a unified pipeline for generating benchmarking datasets for supervised machine learning models for language tasks, with a focus on human "gold-standard" annotation data. The existing corpora currently used as input are those containing long form audio recordings. It was originally designed for the ExELang lab ecosystem.

All datasets follow the [ChildProject](https://childproject.readthedocs.io/en/latest/format.html) format. ChildProject is a Python package and pipeline tool for managing and processing long-form child-centered audio recordings and their annotations. Familiarity with its dataset structure (recordings, annotations, metadata) is assumed when adding new datasets. The repository includes:

- Scripts for dataset creation, validation, and metadata generation
- Human annotation data (addressee, vocal maturity, transcription, vocalization type) inside a number of datasets in the datasets folder
- Utilities for inspecting, filtering, and splitting data

---

## Pipeline

### Step 1 — Install Prerequisites
This repository is managed with [DataLad](https://www.datalad.org/). Large files (recordings, annotations, etc.) are not stored directly in git — they are annexed and only their lightweight pointers are tracked. You need to explicitly **get** files to download their content, and you can **drop** them to free up local disk space while keeping the pointers.

Install `uv` by following the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

Then install DataLad and git-annex:

```bash
uv tool install datalad
uv tool install git-annex
```

### Step 2 — Clone the Repository
Clone the repository from [GIN](https://gin.g-node.org/):

```bash
datalad clone git@gin.g-node.org:/LAAC-LSCP/benchmarking-data-2025.git
cd benchmarking-data-2025
datalad get -n .
```

`datalad get -n .` retrieves the subdataset metadata without downloading large files yet.

### Step 3 — Install Dependencies and System Tools
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

### Step 4 — Fetch Human Annotations
`make` is required for this step. On macOS it is included with Xcode Command Line Tools (`xcode-select --install`); on Linux it is typically pre-installed.

From the root of the repository:

```bash
make get_annotations
```

This fetches all converted annotation files (`.csv`) across all datasets. To free up disk space later:

> ** Dropping data** Once you are finished, you can drop data with `make drop_annotations` and `make drop_recordings`

> **Access rights:** Not everyone has access to all datasets. If `make get_annotations` produces errors for some datasets, that is expected — those datasets are simply not available to you. More importantly, you should remove any datasets you do not have access to from `outputs/manually_annotated_metadata.json` before generating a benchmarking dataset, otherwise the pipeline will fail when it tries to read their files.

---

> **Using existing datasets only?** If you want to generate a benchmarking dataset from the datasets already in this repository, skip ahead to [Step 8](#step-8--generate-a-benchmarking-dataset). Steps 5–7 are only needed when adding a new dataset.

---

### Step 4.1 — Add a New Dataset _(optional)_
The existing datasets live under `/datasets`. Each dataset must follow the [ChildProject](https://childproject.readthedocs.io/en/latest/format.html) directory structure — i.e. it must contain `recordings/`, `annotations/`, and `metadata/` folders in the expected layout. To add a new one, run from the root of the repository:

```bash
cd datasets
datalad clone -d .. [remote storage URL]
cd ..
make get_annotations
```

Note that the remote storage URL is an SSH URL, and that your public key must be have been uploaded to your platform e.g., GitHub or GIN in order to have access.

Each annotation set within the dataset must have a `metannots.yml` file describing it.

### Step 4.2 — Generate Human Annotation Metadata
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

### Step 4.3 — Update the Manual Metadata Index
The script from the previous step automatically discovers annotation sets and their columns — but it cannot know what those columns *mean*. For example, we have found a column called `transcription` could contain either transcriptions, or in some cases contextual information, depending on the dataset. A column called `mwu_type` is not obviously an addressee label or a VCM label just from its name.

This is why `outputs/manually_annotated_metadata.json` exists: it is a hand-written index where a human inspects the actual annotation CSV files and decides which columns map to which of the four annotation categories (addressee, vcm, vtc, transcription).

> **Why is this necessary?** Column names alone are not enough—we have found, for example, a column called `transcription` could contain transcriptions in one dataset and contextual notes in another. This mapping cannot be inferred programmatically. Knowing which columns are relevant also lets the pipeline minimize the final dataset: it only includes parts of recordings and annotation files that have a reference to the category—vtc, addressee, and so on—that you care about.

Using the output from the step 4.2 as a guide, open the annotation files for your dataset (e.g. in `datasets/my_dataset/annotations/eaf/converted/`) and add an entry:

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
                },
                {
                    "name": "eaf_2025/PB",
                    "addressee_cols": [],
                    "vcm_cols": [],
                    "vtc_cols": ["speaker_type"],
                    "transcription_cols": [],
                    "other": ["speaker_id"]
                }
                ...
            ]
        }
    ]
}
```

If in doubt, open the annotation CSV files directly and read the column values — that is the only reliable way to know what a column represents.

> **Access rights reminder:** If you do not have access to all datasets, make sure to remove the inaccessible ones from `outputs/manually_annotated_metadata.json` at this point if you haven't already.

### Step 4.4 — Validate the Manual Metadata Index _(optional, needed when adding a new dataset)_
Because the index is hand-written, it must be validated before use:

```bash
uv run -m scripts.validate_manual_metadata
```

This checks that column names are not misspelled and that referenced sets actually exist in the annotation files. Fix any errors and re-run until it passes cleanly.

### Step 5 — Generate a Benchmarking Dataset
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

### Step 6 — Add More Datasets Incrementally _(optional)_
To add a dataset to an already-generated benchmarking dataset without rebuilding from scratch, use `--additive`:

```bash
uv run -m scripts.create_dataset \
  --output-path [output path] \
  --type vtc \
  --fetch-files \
  -d my_added_dataset \
  --additive
```

**It is recommended to build composite datasets one dataset at a time — changes are more manageable.**

### Using a Different Dataset Folder
If you're logged into a cluster or cloud storage device, it's likely you already have a folder with all your subdatasets on your filesystem. You may wish to use that folder instead of having to fetch your files again and again with DataLad. It is possible to point the command to use that datasets folder instead with the `--datasets-folder` option, thus circumventing the need to fetch files or pollute your filesystem with copies.

```bash
uv run -m scripts.create_dataset \
  --output-path [output path] \
  --type vtc \
  --fetch-files \
  -d my_added_dataset \
  --datasets-folder [path to datasets folder]
```

### Advanced Info:
#### More info about `create_dataset`
You can pass the `--help` flag to the `create_dataset` script—or any other script for that matter—to get more information about generating datasets.

For debugging purposes it is possible to pass a set of steps via `-s` options to `create_dataset` to run one step of the pipeline at a time.

You can pass a filter expression into `create_dataset`, that filters on the ChildProject children.csv metadata files, for example `--children-filter-expr 'child_sex == 'F'` to sample only annotations and recordings for female children—this uses [pandas query expression syntax](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html). See [this link](https://childproject.readthedocs.io/en/latest/format.html) for more info about the schema for the .csv files.

### Reverting Changes
Reverting changes is somewhat supported via the fact that each step creates a series of commits in the generated dataset. You can therefore use git features, such as `git log` to explore changes, and `git reset --hard [commit SHA]` to reset to a previous commit. This, in combination with the above-mentioned `-d` and `-s` options, let you revert to and continue on at any previous point in the pipeline. These options are rather advanced and better avoided—understand in any case that the normal order of operations is dataset by dataset, and step by step for each dataset.

### Example Usage of `create_dataset.py`
Suppose I ran all the steps before step 5. Now I wish to generate a dataset with cougar, forrester, fausey-trio. There are two ways

Files fetched from remote, all datasets in one go:
```bash
# in your environment i.e., with `uv sync` run
uv run -m scripts.create_dataset --output-path ~/Desktop/my_vtc_dataset --fetch-files --type vtc -d cougar -d forrester -d fausey-trio
```

Files available locally in a folder, all datasets in one go:
```bash
# in your environment i.e., with `uv sync` run
uv run -m scripts.create_dataset --output-path ~/Desktop/my_vtc_dataset --datasets-folder ~/Desktop/my_datasets_folder --type vtc -d cougar -d forrester -d fausey-trio
```

Files available locally in a folder, one dataset at a time:
```bash
# in your environment i.e., with `uv sync` run
uv run -m scripts.create_dataset --output-path ~/Desktop/my_vtc_dataset --type vtc -d cougar;
uv run -m scripts.create_dataset --output-path ~/Desktop/my_vtc_dataset --type vtc -d forrester --additive;
uv run -m scripts.create_dataset --output-path ~/Desktop/my_vtc_dataset --type vtc -d fausey-trio --additive;
```

### Troubleshooting
- **Command not found:** Make sure you are in the root of the repository.
- **Missing package:** Install with `uv add [package_name]`.
- **Missing files:** Install with `datalad get [glob pattern]`.
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


