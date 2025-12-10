# Benchmarking Dataset 2025

This benchmarking dataset contains human "gold-standard" annotation data available to LAAC around the time of writing (Dec 2, 2025). Our main focus has been on getting (1) addressee, (2) vocal maturity and (3) transcription data.

As well as containing human annotation data, this repository contains scripts that allows you to find certain annotation data, satisfying certain conditions.

## Dependency management
I decided to use `uv`. Things will probably work with the `ChildProject` conda environment we have been using for so long, maybe installing one or two missing dependencies.

But if you want to use `uv` instead, simply use `uv run`, e.g.,

```bash
uv run scripts/get_human_annotation_metadata.py --dataset-name vanuatu
```

## Linting, Formatting and More
I use `tox` to keep code clean and standard. `pipx install tox`, and run `tox` to run some automated checks on the scripts folder.

## Scripts
### find_files_on_filter_expression.py
```
Usage: find_files_on_filter_expression.py [OPTIONS]

  Prints file paths matching filter expressions on metannots and
  children metadata (specified separately)

Options:
  --metannots-filter-expr TEXT  Filter expression on metannots like
                                'has_addressee == 'Y'' (see Pandas +
                                ChildProject docs)
  --children-filter-expr TEXT   Filter expression on children metadata
                                like 'child_sex == 'f'' (see Pandas +
                                ChildProject docs)
  --no-info-output              Don't print info, such as error info.
                                Only print file paths
  --help                        Show this message and exit.
```
This script lets you find files matching certain conditions. See the Pandas documentation for filter expressions. See the ChildProject documentation to see what columns can be looked for.

Note that ChildProject does not parse dates or anything like that, so all columns, like `child_dob` for example, are interpreted as strings. Luckily this turns out to be okay for comparisons of the sort below.

```bash
uv run scripts/find_files_on_filter_expression.py --metannots-filter-expr "has_addressee == 'Y'" --children-filter-expr "child_dob < '2006-06-06'"
```

Note that if values are missing in the metadata–which is very often the case except on required columns–the filter expression will typically jump over them (these values are `<NA>`) and ignored.

Output (stdout)
```bash
/Users/me/Desktop/benchmarking-data-2025/datasets/bergelson/annotations/eaf/an1/converted/123439-0396_1_10140000_10260000.csv
/Users/me/Desktop/benchmarking-data-2025/datasets/bergelson/annotations/eaf/an1/converted/123439-0396_1_11160000_11280000.csv
...
/Users/me/Desktop/benchmarking-data-2025/datasets/bergelson/annotations/eaf_high_volubility/converted/123836-7117_2_1583460_1703460.csv
/Users/me/Desktop/benchmarking-data-2025/datasets/bergelson/annotations/eaf_high_volubility/converted/123836-7117_2_2183460_2303460.csv
```

The output of this command would typically be redirected with the `>` operator in bash. Preferably use the `--no-info-output` flag in this case, if you wish to post-process this data.

### find_on_filter_expression.py
```
Usage: find_on_filter_expression.py [OPTIONS]

  Find datasets and sets matching a filter expression on the metannots
  metadata

Options:
  --filter-expr TEXT  Filter expression like 'has_addressee == 'Y'' (see
                      Pandas + ChildProject docs)
  --no-info-output    Don't print info, such as error info. Only print
                      datasets and sets
  --help              Show this message and exit.
```

Pandas has a feature called "filter expressions", which are just the kinds of expressions you pass into dataframes to filter them down, e.g., `annotations[annotations["has_vcm_type"] == "Y"]`, or equivalently, `annotations.query('has_vcm_type" == "Y"')`.

This script lets you pass in a filter expression and prints out the dataset and set (as it's called in ChildProject) that matches them.

Example:
```bash
uv run scripts/find_on_filter_expression.py --filter-expr "has_vcm_type == 'Y'" --no-info-output
```

Output (stdout):
```bash
Dataset: 'vanuatu'       Set: 'eaf_2023/AD'
Dataset: 'vanuatu'       Set: 'eaf_2023/AM'
Dataset: 'vanuatu'       Set: 'eaf_2023/HM'
Dataset: 'vanuatu'       Set: 'eaf_2023/MC'
Dataset: 'vanuatu'       Set: 'eaf_2023/MR'
```

### validate_metannots.py
```
Usage: validate_metannots.py [OPTIONS]

  Validate metannots. Prints out validation errors across datasets and
  sets

Options:
  --help  Show this message and exit.
```

This script uses the schema laid out in the ChildProject documentation for metannots and checks that there are no errors. It prints any validation errors to standard output. Under the hood uses pydantic.

Can be run simply with

Prints out validation errors. Usage:

```bash
uv run scripts/validate_metannots.py
```

Or more practically, with output redirection:

```bash
uv run scripts/validate_metannots.py > validation_errors.txt
```

### get_human_annotation_metadata.py
```
Usage: get_human_annotation_metadata.py [OPTIONS]

  Aggregates human annotation metadata for a given dataset (mostly
  duration-related) and saves it

Options:
  --dataset-name TEXT  Dataset name to process
  --help               Show this message and exit.
```

This script summarizes available human annotation metadata by going through the converted .csv files

It also tries to summarise what kinds of values are available in this data, by making a guess at whether the data is categorical in nature or not.

It gathers the total length of annotated segments, as well as the total length of the associated sampled recordings.

Since models, for training, testing and validation, have to compare against annotated segments, the former statistic is probably more useful. But the other is also useful, which is that you may want to train on the absence of annotated segments as well instead of cherry-picking on slices of audio that have an explicit speech label laid down by a human. That is to say, in a training batch of say 12 seconds of annotated audio, there are unannotated pauses between the labelled speech segments, which the model should learn not to try to label as any sort of speech. For this the true available data–meaning what the annotator listened to, including audio he/she didn't label–can often be calculated separately, not using this script, but using the `metannots.yml` file, based on the `sampling_count` and `sampling_unit_duration` and `recording_selection`, although this is more involved and not always possible.

Example:
```bash
uv run scripts/get_human_annotation_metadata.py --dataset-name "vanuatu"
```

Output (to `outputs/human_annotation_data/human_annotation_data-vanuatu.json` file):
```json
{
  "name": "vanuatu",
  "sets": [
    {
      "name": "eaf_2023/AD",
      "columns": [
        {
          "column": "speaker_type",
          "categorical": true,
          "values": [
            "CHI",
            "OCH",
            "FEM",
            "MAL"
          ],
          "annotated_duration_ms": 760555,
          "duration_from_samples_ms": 864000
        },
        ...
      ]
    },
    {
      "name": "eaf_2023/HM",
      "columns": [
        {
          "column": "speaker_type",
          "categorical": true,
          "values": [
            "OCH",
            "MAL",
            "FEM",
            "CHI"
          ],
          "annotated_duration_ms": 908559,
          "duration_from_samples_ms": 864000
        },
        ...
      ]
    },
    ...
  ]
}
```

### graph_dataset_distribution.py
```
Usage: graph_dataset_distribution.py [OPTIONS]

  Lets you graph distributional info of metadata over a dataset

  If looking at segments, will choose information only from human-
  annotated sets If looking at recordings in general, will choose all
  recording information regardless of which sets

Options:
  -d, --dataset TEXT              datasets to graph. If not specified,
                                  will use all datasets

  -x, --x-axis [child_id|child_age|child_sex|speaker_type|speaker_id]
                                  x-axis  [required]
  -y, --y-axis [segment|recording]
                                  y-axis  [required]
  --metric [duration_mean|count|duration_std|duration_total]
                                  function to run over aggregated data
                                  [required]

  --output-folder PATH            path of output folder
  --help                          Show this message and exit.
```

This is a generic graphing script that gives you a basic outline of how much data is available over some categorical index.

The following is some example output for the following command:
```bash
uv run scripts/graph_dataset_distribution.py -d vanuatu -d fausey-trio -x speaker_type -y segment --metric duration_total
```

![Example age distribution](static/images/segment-duration-over-speaker-type.png)