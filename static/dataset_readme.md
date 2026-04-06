# Benchmarking Dataset
This entire dataset was generated automatically with the [benchmarking dataset factory](https://gin.g-node.org/LAAC-LSCP/benchmarking-data-2025), also available [here](https://github.com/LAAC-LSCP/benchmarking-dataset-factory), albeit without the sub-datasets.

## Setup
Scripts will work out of the box with a package manager such as poetry or uv and a suitable virtual environment. The external dependencies are `ChildProject`, `pandas` and `click`. It also works out of the box with the ChildProject conda environment, which has these installed. For information on how to set up this environment see the [ChildProject installation page](https://childproject.readthedocs.io/en/latest/install.html#miniconda).

If a package is missing from the ChildProject conda environment, do the following
```bash
# activate the childproject environment (or whatever it is called on your system)
conda activate childproject
pip install [missing package]
```

## Scripts
You will find scripts in the scripts folder.

To split your dataset, use `get_splits.py`. For example, for a 80/10/10 split:

```bash
# assumes you've activated a virtual environments
python3 get_splits.py --train 0.8 --test 0.1 --validate 0.1 --output-csv outputs.csv --seed 0 --same-child
```

The folding algorithm is greedy and will try its best to find a good split of the data. Note that `--same-child` flag assures data for a given child doesn't straddle train/test/validation sets—this way we avoid overfitting/revealing too much of the test/validation distribution during training.