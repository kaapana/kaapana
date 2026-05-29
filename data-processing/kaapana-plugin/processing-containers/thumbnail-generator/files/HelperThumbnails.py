# This file is a copy of kaapana/operators/HelperThumbnails.py from the kaapana-plugin image.
# The thumbnail-generator runs in a separate Docker image and cannot import from kaapana.operators,
# so the file must be duplicated here. If NO_THUMBNAIL_MODALITIES changes in the source,
# this copy must be updated as well.
from __future__ import annotations

NO_THUMBNAIL_MODALITIES: frozenset[str] = frozenset(
    {"SR", "KO", "PR", "RTPLAN", "REG", "FID", "AU", "RWVM"}
)


def has_ref_series(ds) -> bool:
    modality = str(ds.get("Modality", "")).strip().upper()
    sop_class_uid = str(ds.get("SOPClassUID", ""))
    return modality in {"SEG", "RTSTRUCT"} or sop_class_uid in {
        "1.2.840.10008.5.1.4.1.1.66.4",  # Segmentation Storage
        "1.2.840.10008.5.1.4.1.1.481.3",  # RT Structure Set Storage
    }
