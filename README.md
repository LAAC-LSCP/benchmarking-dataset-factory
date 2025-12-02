# Benchmarking Dataset 2025

This benchmarking dataset contains human "gold-standard" annotation data available to LAAC around the time of writing (Dec 2, 2025). Our main focus has been on getting (1) addressee, (2) vocal maturity and (3) transcription data.

As well as containing human annotation data, this repository contains scripts that allows you to find certain annotation data, satisfying certain conditions.

## Important(!): datasets.json
This file must be present and populated by you, the engineer. It must point to all the places with human annotations across the datasets

This means that should you add a new dataset, you **must** update this file. You can then run the subsequent scripts to get the associated output files, as done for the existing datasets. Many scripts explicitly read `datasets.json`

## Scripts
### find_on_filter_expression.py
Pandas has a feature called "filter expressions", which are just the kinds of expressions you pass into dataframes to filter them down, e.g., `annotations[annotations["has_vcm_type"] == "Y"]`, or equivalently, `annotations.query('has_vcm_type" == "Y"')`.

This script lets you pass in a filter expression and prints out the dataset and set (as it's called in ChildProject) that matches them.

Example:
```bash
python3 scripts/find_on_filter_expression.py --filter-expr "has_vcm_type == 'Y'"
```

Output (stdout):
```bash
INFO: Printing datasets and sets matching filter expression 'has_vcm_type == 'Y''...
Dataset: 'vanuatu'       Set: 'eaf_2023/AD'
Dataset: 'vanuatu'       Set: 'eaf_2023/AM'
Dataset: 'vanuatu'       Set: 'eaf_2023/HM'
Dataset: 'vanuatu'       Set: 'eaf_2023/MC'
Dataset: 'vanuatu'       Set: 'eaf_2023/MR'
```

### get_human_annotation_metadata.py
This script summarizes available human annotation metadata by going through the converted .csv files

It also tries to summarise what kinds of values are available in this data, by making a guess at whether the data is categorical in nature or not.

It gathers the total length of annotated segments, and the duration of the associated recordings (although these latter durations are probably not useful, as we typically end up exposing only a subset of our recordings file for human annotation)

Since models, for training, testing and validation, have to compare against annotated segments, the former statistic is probably more useful. But still, **there is one edge case where that statistics doesn't apply**, which is that you may want to train on the absence of annotated segments as well instead of cherry-picking on slices of audio that have an explicit speech label laid down by a human. That is to say, in a training batch of say 12 seconds of annotated audio, there are unannotated pauses between the labelled speech segments, which the model should learn not to try to label as any sort of speech. For this the true available data–meaning what the annotator listened to, including audio he/she didn't label–can often be calculated separately, not using this script, but using the `metannots.yml` file, based on the `sampling_count` and `sampling_unit_duration` and `recording_selection`, although this is more involved and not always possible.

TODO: add a script/option for the latter case

Example:
```bash
python3 scripts/get_human_annotation_metadata.py --dataset-name "vanuatu"
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
          "recording_duration_ms": 15718444128
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
          "recording_duration_ms": 25513058304
        },
        ...
      ]
    },
    ...
  ]
}
```