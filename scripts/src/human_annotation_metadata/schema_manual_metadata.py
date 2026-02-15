from contextvars import ContextVar
from pathlib import Path
from typing import Callable, Dict, List, Literal, Optional, Set, Tuple

import yaml
from pydantic import BaseModel, model_validator

from scripts.src.human_annotation_metadata.schema_generated_metadata import (
    GeneratedDataset,
    GeneratedDatasets,
    GeneratedSet,
)
from scripts.src.utils.constants import DATASETS_FOLDER


def get_metannots(dataset: str, set: str, datasets_dir: Path) -> Path:
    return (datasets_dir / dataset / "annotations" / set / "metannots.yml").resolve()


def dataset_model_factory(generated_datasets: GeneratedDatasets, datasets_folder: Optional[Path] = DATASETS_FOLDER, skip_validation: bool = False):
    context_dataset_name = ContextVar("name")

    class ManualSet(BaseModel):
        name: str
        addressee_cols: List[str]
        vcm_cols: List[str]
        vtc_cols: List[str]
        transcription_cols: List[str]
        other: List[str]
        ignore: Optional[List[str]] = []

        @model_validator(mode="after")
        def assure_cols_exact_match(self):
            """Check that the available columns are an exact match on the columns in
            the generated data."""
            if skip_validation:
                return self

            manual_cols = self._get_all_cols()

            dataset = self._get_dataset()
            generated_cols = {
                c.column for s in dataset.sets for c in s.columns if s.name == self.name
            }

            if manual_cols != generated_cols:
                raise ValueError(
                    f"generated columns and manual columns do not match in set {self.name} dataset {dataset.name}.\n"
                    f"manual_cols: {manual_cols!s}\n"
                    f"generated_cols: {generated_cols!s}\n"
                )

            return self

        @model_validator(mode="after")
        def check_metannots_exist(self):
            """Check if metannots exist. Implicitly checks the set exists"""
            if skip_validation:
                return self

            self._get_metannots(datasets_folder)

            return self

        @model_validator(mode="after")
        def check_for_missing_vcm_metannots(self):
            self._check_for_missing_data_metannots(("vcm_cols", "has_vcm_type"))
            return self

        @model_validator(mode="after")
        def check_for_false_vcm_metannots(self):
            self._check_for_false_data_metannots(("vcm_cols", "has_vcm_type"))
            return self

        @model_validator(mode="after")
        def check_for_missing_addressee_metannots(self):
            self._check_for_missing_data_metannots(("addressee_cols", "has_addressee"))
            return self

        @model_validator(mode="after")
        def check_for_false_addresseee_metannots(self):
            self._check_for_false_data_metannots(("addressee_cols", "has_addressee"))
            return self

        @model_validator(mode="after")
        def check_for_missing_vtc_metannots(self):
            self._check_for_missing_data_metannots(("vtc_cols", "has_speaker_type"))
            return self

        @model_validator(mode="after")
        def check_for_false_vtc_metannots(self):
            self._check_for_false_data_metannots(("vtc_cols", "has_speaker_type"))
            return self

        @model_validator(mode="after")
        def check_for_missing_transcription_metannots(self):
            self._check_for_missing_data_metannots(
                ("transcription_cols", "has_transcription")
            )
            return self

        @model_validator(mode="after")
        def check_for_false_transcription_metannots(self):
            self._check_for_false_data_metannots(
                ("transcription_cols", "has_transcription")
            )
            return self

        def _check_for_missing_data_metannots(
            self,
            keys: (
                Tuple[Literal["addressee_cols"], Literal["has_addressee"]]
                | Tuple[Literal["vcm_cols"], Literal["has_vcm_type"]]
                | Tuple[Literal["vtc_cols"], Literal["has_speaker_type"]]
                | Tuple[Literal["transcription_cols"], Literal["has_transcription"]]
            ),
        ) -> None:
            if skip_validation:
                return self

            metannots = self._get_metannots(datasets_folder)
            duration, cols = self._get_annotated_duration(keys[0])

            if duration > 0 and not metannots.get(keys[1], "N") in ["y", "Y"]:
                raise ValueError(f"{keys[1]} missing in metannots for set {self.name}, \
dataset {self.dataset_name}\n \
Associated columns: {cols!s}\n \
Duration: {duration!s}\n")

        def _check_for_false_data_metannots(
            self,
            keys: (
                Tuple[Literal["addressee_cols"], Literal["has_addressee"]]
                | Tuple[Literal["vcm_cols"], Literal["has_vcm_type"]]
                | Tuple[Literal["vtc_cols"], Literal["has_speaker_type"]]
                | Tuple[Literal["transcription_cols"], Literal["has_transcription"]]
            ),
        ) -> None:
            if skip_validation:
                return self

            metannots = self._get_metannots(datasets_folder)
            duration, cols = self._get_annotated_duration(keys[0])

            if duration == 0 and metannots.get(keys[1], "N") in ["y", "Y"]:
                raise ValueError(f"{keys[1]} found in metannots for set {self.name}, \
dataset {self.dataset_name}, but total annotated duration 0\n \
dataset {self.dataset_name}\n \
Associated columns: {cols!s}\n")

        def _get_metannots(self, datasets_folder: Path) -> Dict:
            file = get_metannots(self.dataset_name, self.name, datasets_folder)
            metannots: Dict
            with open(file, "r") as f:
                metannots = yaml.safe_load(f)

            return metannots

        def _get_annotated_duration(
            self,
            col_type: Literal[
                "addressee_cols", "vcm_cols", "vtc_cols", "transcription_cols"
            ],
        ) -> Tuple[int, Set[str]]:
            this_set = self._get_set()
            cols = [
                c
                for c in this_set.columns
                if c.column in self.__getattribute__(col_type)
            ]
            annotated_duration = sum([col.annotated_duration_ms for col in cols])

            return annotated_duration, {c.column for c in cols}

        @property
        def dataset_name(self) -> str:
            return context_dataset_name.get()

        def _get_all_cols(self) -> List[str]:
            result = set()
            for col_list in [
                self.addressee_cols,
                self.vcm_cols,
                self.vtc_cols,
                self.transcription_cols,
                self.other,
                self.ignore,
            ]:
                result = result.union({c for c in col_list})

            return result

        def _get_dataset(self) -> GeneratedDataset:
            dataset = next(
                (d for d in generated_datasets.datasets if d.name == self.dataset_name),
                None,
            )
            if dataset is None:
                raise ValueError(f"Dataset {self.name} not found in generated data")

            return dataset

        def _get_set(self) -> GeneratedSet:
            dataset = self._get_dataset()

            this_set = next((s for s in dataset.sets if s.name == self.name), None)

            if this_set is None:
                raise ValueError(
                    f"Set f{self.name} not found in dataset f{dataset.name} in generated metadata"
                )

            return this_set

    class ManualDataset(BaseModel):
        name: str
        sets: List[ManualSet]

        @model_validator(mode="wrap")
        @classmethod
        def validate_model(cls, v, handler):
            try:
                str(v["name"])
            except KeyError:
                raise ValueError("name required")
            token = context_dataset_name.set(v["name"])
            try:
                return handler(v)
            finally:
                context_dataset_name.reset(token)

        @model_validator(mode="after")
        def check_sets_match(self):
            if skip_validation:
                return self

            this_dataset = self._get_dataset()
            generated_sets = {s.name for s in this_dataset.sets}
            manual_sets = {s.name for s in self.sets}

            if not manual_sets == generated_sets:
                raise ValueError(
                    f"Sets don't match in dataset {this_dataset.name}:\n"
                    f"Generated datasets: {generated_sets!s}\n"
                    f"Manual sets: {manual_sets!s}\n"
                )
            return self

        def _get_dataset(self) -> GeneratedDataset:
            dataset = next(
                (d for d in generated_datasets.datasets if d.name == self.name), None
            )

            if dataset is None:
                raise ValueError(f"Dataset {self.name} not found in generated datasets")

            return dataset

    class ManualDatasets(BaseModel):
        datasets: List[ManualDataset]

    return ManualDatasets
