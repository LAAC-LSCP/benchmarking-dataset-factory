from datetime import date
from pathlib import Path
from typing import Dict, Literal, Optional

import yaml
from pydantic import BaseModel


class MetaAnnotations(BaseModel):
    segmentation: Optional[str] = None
    segmentation_type: Optional[Literal["permissive", "restrictive"]] = None
    method: Optional[
        Literal["automated", "manual", "mixed", "derivation", "citizen-scientists"]
    ] = None
    sampling_method: Optional[
        Literal[
            "none", "manual", "periodic", "random", "high-volubility", "high-energy"
        ]
    ] = None
    sampling_target: Optional[Literal["chi", "fem", "mal", "och"]] = None
    sampling_count: Optional[int] = None
    sampling_unit_duration: Optional[int] = None
    recording_selection: Optional[str] = None
    participant_selection: Optional[str] = None
    annotator_name: Optional[str] = None
    annotator_experience: Optional[Literal[1, 2, 3, 4, 5]] = None
    annotation_algorithm_name: Optional[Literal["VTC", "ALICE", "VCM", "ITS"]] = None
    annotation_algorithm_publication: Optional[str] = None
    annotation_algorithm_version: Optional[str] = None
    annotation_algorithm_repo: Optional[str] = None
    date_annotation: Optional[date] = None
    has_speaker_type: Optional[Literal["Y", "N"]] = None
    has_transcription: Optional[Literal["Y", "N"]] = None
    has_interactions: Optional[Literal["Y", "N"]] = None
    has_acoustics: Optional[Literal["Y", "N"]] = None
    has_addressee: Optional[Literal["Y", "N"]] = None
    has_vcm_type: Optional[Literal["Y", "N"]] = None
    has_words: Optional[Literal["Y", "N"]] = None
    notes: Optional[str] = None


def get_metannots(
    dataset_folder: Path,
    dataset_name: str,
    set_name: str,
    safe_load: Optional[bool] = False,
) -> Optional[MetaAnnotations]:
    metannots: Path = (
        dataset_folder / dataset_name / "annotations" / set_name / "metannots.yml"
    )

    if not metannots.exists():
        return None

    data: Dict
    with open(metannots, "r") as f:
        data = yaml.safe_load(f)

    if safe_load:
        return data

    return MetaAnnotations(**data)
