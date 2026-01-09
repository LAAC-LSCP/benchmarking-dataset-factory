from enum import StrEnum


class DatasetType(StrEnum):
    VTC = "vtc"
    ADDRESSEE = "addressee"
    TRANSCRIPTION = "transcription"
    VOCAL_MATURITY = "vcm"