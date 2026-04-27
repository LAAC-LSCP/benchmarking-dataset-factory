# Benchmarking Dataset
This dataset was generated automatically with the [benchmarking dataset factory](https://gin.g-node.org/LAAC-LSCP/benchmarking-data-2025).

---

## Setup

### Cloning this Repository
This dataset is managed with [DataLad](https://www.datalad.org/). Large files (recordings, annotations) are annexed — only lightweight pointers are stored in git. You need to explicitly **get** files to download their content, and can **drop** them to free disk space.

Install DataLad:
```bash
# via uv (recommended):
uv tool install datalad
# or on macOS via Homebrew:
brew install datalad
```

Then clone:
```bash
datalad clone git@gin.g-node.org:/LAAC-LSCP/[repository-name].git
cd [repository-name]
datalad get -n .
```

### Fetching Files
To download the actual recording and annotation content:
```bash
datalad get recordings/**
datalad get annotations/**
```

Or selectively, e.g. only converted recordings:
```bash
datalad get recordings/converted/**
```

### Installing uv and Dependencies
Install `uv` by following the [installation instructions](https://docs.astral.sh/uv/getting-started/installation/). The dataset already contains a `pyproject.toml` and `uv.lock`, so from the root of the dataset:
```bash
uv sync
```

---

## Adding a Remote and Uploading to GIN
To push this dataset to [GIN](https://gin.g-node.org/):

1. Create a new repository on GIN (via the web interface).
2. Add it as a DataLad sibling:
```bash
datalad siblings add \
  --name gin \
  --url git@gin.g-node.org:/[your-username]/[repository-name].git
```
3. Push:
```bash
datalad push --to gin
```

To push large annexed files as well:
```bash
datalad push --to gin --data anything
```

---

## Scripts
You will find scripts in the `scripts/` folder.

### Splitting the Dataset
To split your dataset into train, test, and validation sets, use `scripts/get_splits.py`. For example, for an 80/10/10 split:

```bash
uv run scripts/get_splits.py \
  --train 0.8 \
  --test 0.1 \
  --validate 0.1 \
  --output-csv outputs.csv \
  --seed 0 \
  --same-child
```

The folding algorithm is greedy and will try its best to find a good split of the data. The `--same-child` flag ensures that data for a given child doesn't straddle train/test/validation sets — this avoids overfitting and prevents the test/validation distribution from being revealed during training.
