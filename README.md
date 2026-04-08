# Benchmarking Dataset Factory 2025
This repository provides a unified pipeline for generating benchmarking datasets for supervised machine learning models for language tasks, with a focus on human "gold-standard" annotation data. The existing corpora currently used as input are those containing long form audio recordings. It was originally designed for the ExELang lab ecosystem and follows the [ChildProject](https://childproject.readthedocs.io/en/latest/format.html) dataset structure. The repository includes:

- Scripts for dataset creation, validation, and metadata generation
- Human annotation data (addressee, vocal maturity, transcription, vocalization type)
- Utilities for inspecting, filtering, and splitting data

---

## Quickstart
If you want to get started immediately, follow these steps:

### 1. Download and Install Miniconda or Micromamba
- **Miniconda:** [Download here](https://docs.conda.io/en/latest/miniconda.html)
- **Micromamba:** [Download here](https://mamba.readthedocs.io/en/latest/installation.html)
Follow the instructions on the website for your operating system. After installation, open a new terminal window.

### 2. Download the Environment File
For MacOS:
```bash
curl https://raw.githubusercontent.com/LAAC-LSCP/ChildProject/master/env_macos.yml -o env.yml
```
For Linux or Windows, use the appropriate `.yml` file from the [ChildProject repository](https://github.com/LAAC-LSCP/ChildProject/).

### 3. Create the Environment
**With Miniconda:**
```bash
conda env create -f env.yml
```
**With Micromamba:**
```bash
micromamba env create -f env.yml
```

### 4. Activate the Environment
**With Miniconda:**
```bash
conda activate childproject
```
**With Micromamba:**
```bash
micromamba activate childproject
```

You should see `(childproject)` at the start of your terminal prompt. To check, run:
```bash
conda env list  # or micromamba env list
```
An asterisk (*) should appear next to `childproject`.

### 5. Check That DataLad is Installed
```bash
datalad --version
```
If you see a version number, you're good. If not, install it with:
```bash
conda install -c conda-forge datalad
```

### 6. Clone This Repository
```bash
# prefer using DataLad over git. git will not give you the subdatasets
datalad clone git@gin.g-node.org:/LAAC-LSCP/benchmarking-data-2025.git
datalad get -n benchmarking-data-2025
cd benchmarking-data-2025
```

### 7. Install Any Missing Python Packages
If you get errors about missing packages when running scripts, install them with:
```bash
pip install [package_name]
```
while your environment is active.

### 8. Add a Dataset (Optional)
If you want to add a new dataset, follow the instructions in the "Adding Datasets" section below. Otherwise, skip to the next step.

### 9. Generate Human Annotation Metadata (Optional)
From the root of the repository, run:
```bash
python -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
```
or, if you have `uv` installed and prefer to use it:
```bash
uv run -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
```
This will create a file in `outputs/human_annotation_data/`.

Data may be missing, in which case you must run `datalad get [glob pattern]` to get this data. An example would be `datalad get datasets/png2016/annotations/eaf_2016/converted/**`.

### 10. (If Needed) Update the Manual Metadata Index
Edit `outputs/manually_annotated_metadata.json` as described in the main instructions below.

### 11. Validate the Manual Metadata Index
```bash
python -m scripts.validate_manual_metadata
```
or
```bash
uv run -m scripts.validate_manual_metadata
```
Fix any errors before proceeding.

### 12. Generate a Benchmarking Dataset
Example command:
```bash
python -m scripts.create_dataset --output-path [location of generated dataset] \
  --fetch-files \
  --type vtc \
  -d my_dataset \
  -d my_other_dataset
```
or
```bash
uv run -m scripts.create_dataset --output-path [location of generated dataset] \
  --fetch-files \
  --type vtc \
  -d my_dataset \
  -d my_other_dataset
```
Replace `[location of generated dataset]` and dataset names as needed.

### 13. (Optional) Add More Datasets Incrementally
To add a subdataset to an existing benchmarking dataset:
```bash
python -m scripts.create_dataset --output-path [location of generated dataset] \
  --fetch-files \
  --type vtc \
  -d my_added_subdataset \
  --additive
```
It is recommend to build your composite dataset one dataset at a time—changes are more manageable.

The resulting dataset will contain further instructions.

### 14. Troubleshooting
- **Command not found:** Make sure you are in the correct directory and your environment is activated.
- **Missing package:** Install with `pip install [package_name]` or `conda install [package_name]`.
- **Permission denied:** Try running the command with `sudo` (Linux/Mac) or as administrator (Windows), or check file permissions.
- **Script errors:** Read the error message carefully. Most issues are due to missing dependencies or not activating the environment.

---

## In-Depth: The 5-Step Pipeline
This repository is structured as a data pipeline. The main steps are:

1. **Add datasets**: Place datasets in `/datasets` following the ChildProject structure. To add a new dataset, use DataLad:
  ```bash
  cd datasets
  datalad clone -d .. [remote storage URL]
  datalad get --no-data [repository name]
  # For large files:
  datalad get [glob pattern] -J [num connections]
  ```
  Each human annotation set must have a `metannots.yml` file.

2. **Generate human annotation metadata**: Summarize available annotation data for a dataset:
  ```bash
  python -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
  # or
  uv run -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
  ```
  This creates a JSON file in `outputs/human_annotation_data/`.

3. **Hand-write the manual metadata index**: Edit `outputs/manually_annotated_metadata.json` to index which sets contain which annotation types. Use the output from step 2 as a guide.

4. **Validate the manual metadata index**: Ensure your manual index matches the actual data:
  ```bash
  python -m scripts.validate_manual_metadata
  # or
  uv run -m scripts.validate_manual_metadata
  ```
  Fix any errors before proceeding.

5. **Generate a benchmarking dataset**: Create a dataset for ML benchmarking:
  ```bash
  python -m scripts.create_dataset --output-path [output path] --fetch-files --type vtc -d my_dataset -d my_other_dataset
  # or
  uv run -m scripts.create_dataset --output-path [output path] --fetch-files --type vtc -d my_dataset -d my_other_dataset
  ```
  Use `--additive` to add more datasets incrementally.

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
The recommended way to manage dependencies is to use the provided environment file and `uv` for reproducibility. If you encounter missing dependencies, install them with `pip` or `conda` as described in the Quickstart.

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
```bash
uv run -m scripts.validate_metannots --dataset-name [dataset name]
```

### 2. Generate Human Annotation Data Metadata
Once you have added your datasets and fetched your annotation data, you can generate human annotation metadata using the `get_human_annotation_metadata` script. This creates json-formatted metadata over the human annotation data for your dataset, e.g.,

```bash
uv run -m scripts.get_human_annotation_metadata --dataset-name "my_dataset"
```

Running the above script generates `outputs/human_annotation_data/human_annotation_data-my_dataset.json` outlining the amount of annotations available. Here is an example for `png2016`:
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
This metadata is useful as (1) a filter, (2) a summary, and (3) a way to inspect what kind of data is available.

### 3. Hand-write an Index for your Data
Here we need a human in the loop. We need to write an index to aid in the discovery of data related to the four categories of human-annotated data. The correct identification of ChildProject sets—sets are collections of related data in ChildProject—containing such data can only be achieved through human judgment.

Inspecting the output from the previous step, it can be readily seen which data is available. Using this output as a source of truth, and potentially inspecting the human annotations themselves, an index is written at outputs/manually_annotated_metadata.json. This shows only the top of the file:

```json
{
    "datasets":
    [
        {
            "name": "bergelson",
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
                    "name": "eaf_high_volubility",
                    "addressee_cols": ["addressee"],
                    "vcm_cols": ["vcm_type"],
                    "vtc_cols": ["speaker_type"],
                    "transcription_cols": ["transcription"],
                    "other": ["words", "lex_type", "mwu_type", "speaker_id"]
                },
                {
                    "name": "eaf/reliability",
                    "addressee_cols": ["addressee"],
                    "vcm_cols": ["vcm_type"],
                    "vtc_cols": ["speaker_type"],
                    "transcription_cols": ["transcription"],
                    "other": ["lex_type", "mwu_type", "speaker_id"]
                }
            ]
        },
...
```

### 4. Validate your Manual Index
Because the index is hand-written, it needs to be validated and rewritten until it passes all checks. Validate your manual metadata with
```bash
uv run -m scripts.validate_manual_metadata
```
This script compares, for instance, your manual metadata with the human annotation data JSON files to check that column names aren't misspelled or missing.

### 5. Generate a Benchmarking Dataset
The meat of this repository is in the dataset generation script. It can be run like

```bash
uv run -m scripts.create_dataset --output-path [location of generated dataset] \
  --fetch-files // Fetch large files with DataLad if not present  \
  --type vtc  \
  -d my_dataset \
  -d my_other_dataset
```
To generate a vocalization type dataset.
There are many more options available, and its usage is complex. It can be used to generate the dataset in one fell swoop, or to generate one step at a time, or one dataset at a time, or both one step and one dataset at a time. This is very useful if you need short feedback loops for testing, exploring, or validating your generated dataset.

Below is an example of adding a subdataset to a generated benchmarking dataset using the `--additive` flag, rather than generating it from scratch
```bash
uv run -m scripts.create_dataset --output-path [location of generated dataset] \
  --fetch-files // Fetch large files with DataLad if not present  \
  --type vtc  \
  -d my_added_subdataset \
  --additive
```

## Dependency management
I decided to use `uv`. Things will probably work fine with the `ChildProject` conda environment we have been using for so long internally, maybe installing one or two missing dependencies.

But if you want to use `uv` instead, simply use `uv run`, e.g.,

```bash
uv run -m scripts.get_human_annotation_metadata --dataset-name vanuatu
```

The use of `uv` is encouraged over `conda` as it allows locking of dependencies, and therefore correct reproducibility, at least as far as Python packages are concerned.

## Linting, Formatting and More
I use `tox` to keep code clean and standard. `pipx install tox`, and run `tox` to run some automated checks on the scripts folder.

