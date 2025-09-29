"""
Defines standardized label enums for different segmentation categories.
These are used as fallbacks if no `total-measurements.json` is available.

Each enum class corresponds to a possible segmentation category and provides
integer values for each label.
"""

import enum


class BodyParts(enum.IntEnum):
    TRUNC = 1
    EXTREMITIES = 2


class BodyRegions(enum.IntEnum):
    SUBCUTANEOUS_TISSUE = 1
    MUSCLE = 2
    ABDOMINAL_CAVITY = 3
    THORACIC_CAVITY = 4
    BONE = 5
    GLANDS = 6
    PERICARDIUM = 7
    BREAST_IMPLANT = 8
    MEDIASTINUM = 9
    BRAIN = 10
    NERVOUS_SYSTEM = 11
    IGNORE = 255


class Vertebrae(enum.IntEnum):
    VERTEBRAE_L5 = 18
    VERTEBRAE_L4 = 19
    VERTEBRAE_L3 = 20
    VERTEBRAE_L2 = 21
    VERTEBRAE_L1 = 22
    VERTEBRAE_T12 = 23
    VERTEBRAE_T11 = 24
    VERTEBRAE_T10 = 25
    VERTEBRAE_T9 = 26
    VERTEBRAE_T8 = 27
    VERTEBRAE_T7 = 28
    VERTEBRAE_T6 = 29
    VERTEBRAE_T5 = 30
    VERTEBRAE_T4 = 31
    VERTEBRAE_T3 = 32
    VERTEBRAE_T2 = 33
    VERTEBRAE_T1 = 34
    VERTEBRAE_C7 = 35
    VERTEBRAE_C6 = 36
    VERTEBRAE_C5 = 37
    VERTEBRAE_C4 = 38
    VERTEBRAE_C3 = 39
    VERTEBRAE_C2 = 40
    VERTEBRAE_C1 = 41


class Tissues(enum.IntEnum):
    BONE = 1  # Bone tissue
    MUSCLE = 2  # Muscle tissue
    TOTAL_ADIPOSE_TISSUE = 3  # TAT: Total Adipose Tissue
    INTERMUSCULAR_ADIPOSE_TISSUE = 4  # IMAT: Fat between muscles
    SUBCUTANEOUS_ADIPOSE_TISSUE = 5  # SAT: Fat under the skin
    VISCERAL_ADIPOSE_TISSUE = 6  # VAT: Fat around organs
    PARACARDIAL_ADIPOSE_TISSUE = 7  # PAT: Fat near the heart
    EPICARDIAL_ADIPOSE_TISSUE = 8  # EAT: Fat inside the pericardium
    IGNORE = 255


class LungVesselsAirways(enum.IntEnum):
    LUNG_VESSELS = 1
    LUNG_TRACHEA_BRONCHIA = 2
